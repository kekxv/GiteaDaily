from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from sqlalchemy import update, or_
import json
import traceback
import tzlocal
import logging
import asyncio
from ..database import SessionLocal
from ..models import ReportTask, TaskLog
from .gitea import GiteaService
from .webhook import WebhookService
from .ai import AIService

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        # Use system local timezone
        try:
            local_tz = tzlocal.get_localzone()
        except Exception:
            local_tz = None
        
        # job_defaults: ensure only 1 instance of a task runs per process
        job_defaults = {
            'coalesce': True,
            'max_instances': 1
        }
        self.scheduler = AsyncIOScheduler(timezone=local_tz, job_defaults=job_defaults)

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()

    def add_or_update_task(self, task_id: int, cron_expression: str):
        job_id = f"task_{task_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        self.scheduler.add_job(
            self.execute_task,
            CronTrigger.from_crontab(cron_expression),
            id=job_id,
            args=[task_id],
            misfire_grace_time=60  # If missed by > 60s, don't run
        )

    def remove_task(self, task_id: int):
        job_id = f"task_{task_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    async def execute_task(self, task_id: int):
        # We use a context manager to ensure session is closed and transactions are handled
        with SessionLocal() as db:
            log_id = None
            try:
                # 1. Acquire Distributed Lock (Atomic Update)
                now = datetime.now().astimezone()
                lock_threshold = now - timedelta(seconds=50)

                # Attempt to claim this task run
                stmt = (
                    update(ReportTask)
                    .where(ReportTask.id == task_id)
                    .where(ReportTask.is_active)
                    .where(or_(
                        ReportTask.last_run_at.is_(None),
                        ReportTask.last_run_at < lock_threshold
                    ))
                    .values(last_run_at=now)
                )
                result = db.execute(stmt)
                db.commit()

                if result.rowcount == 0:
                    # Locked by another worker or already run
                    return

                # 2. Fetch task with row-level lock (for the rest of the operation)
                task = db.query(ReportTask).filter(ReportTask.id == task_id).with_for_update().first()
                if not task:
                    return

                # 3. Create initial log entry
                new_log = TaskLog(
                    task_id=task.id,
                    status="running",
                    summary="任务执行中...",
                    commit_count=0
                )
                db.add(new_log)
                db.commit()
                db.refresh(new_log)
                log_id = new_log.id

                gitea_cfg = task.gitea_config
                notify_cfg = task.notify_config
                gitea_service = GiteaService(gitea_cfg.base_url, gitea_cfg.token)
                
                # Use Aware Local Time for calculations
                now = datetime.now().astimezone()
                since = (now - timedelta(days=task.report_days)).replace(hour=0, minute=0, second=0, microsecond=0)
                until = now

                markdown_report = ""
                total_commits = 0
                raw_data_obj = {}

                if task.scope_type == "user":
                    user_info = await gitea_service.get_my_info()
                    username = user_info.get("login")
                    user_id = user_info.get("id")
                    full_name = user_info.get("full_name") or username
                    activities = await gitea_service.get_user_activities(username, since, user_id=user_id)
                    
                    raw_data_obj["activities"] = activities
                    
                    # Group activities and fetch detailed commits for pushes
                    data_by_repo = {}
                    for act in activities:
                        repo_name = act["repo"]["full_name"]
                        if repo_name not in data_by_repo:
                            data_by_repo[repo_name] = {"activities": [], "detailed_commits": []}
                        data_by_repo[repo_name]["activities"].append(act)
                    
                    # For repos with pushes, get actual commit messages
                    for repo_name, repo_data in data_by_repo.items():
                        if any(a["op_type"] in ["commit_repo", "push_repo"] for a in repo_data["activities"]):
                            # Fetch commits by this user in this repo
                            all_commits = await gitea_service.get_commits_for_repo(repo_name, since, until)
                            # Filter by user (some instances might return all commits in range)
                            my_commits = [c for c in all_commits if c["author"] == full_name or c["author"] == username]
                            repo_data["detailed_commits"] = my_commits
                            total_commits += len(my_commits)
                    
                    markdown_report = gitea_service.generate_activity_report(since, data_by_repo, full_name)
                else:
                    # ... existing repos logic ...
                    # (I will wrap this part to store in raw_data_obj as well)
                    repos_to_check = []
                    if task.scope_type in ["all", "owner"]:
                        repos_to_check = await gitea_service.get_all_repos(scope=task.scope_type)
                    else:
                        repos_to_check = task.target_repos or []

                    semaphore = asyncio.Semaphore(10)

                    async def fetch_repo_data(repo):
                        async with semaphore:
                            c, i, p = await asyncio.gather(
                                gitea_service.get_commits_for_repo(repo, since, until),
                                gitea_service.get_open_issues(repo),
                                gitea_service.get_open_prs(repo)
                            )
                            return repo, c, i, p

                    results = await asyncio.gather(*(fetch_repo_data(repo) for repo in repos_to_check))

                    data_by_repo = {}
                    for repo, repo_commits, repo_issues, repo_prs in results:
                        if repo_commits or repo_issues or repo_prs:
                            data_by_repo[repo] = {
                                "commits": repo_commits,
                                "issues": repo_issues,
                                "prs": repo_prs
                            }
                            total_commits += len(repo_commits)
                    
                    raw_data_obj["repo_data"] = data_by_repo
                    markdown_report = gitea_service.generate_markdown_report(since, data_by_repo)
                
                if task.is_ai_enabled and task.ai_config:
                    ai_cfg = task.ai_config
                    system_prompt = task.ai_system_prompt or ai_cfg.system_prompt
                    ai_summary = await AIService.summarize_report(
                        api_base=ai_cfg.api_base,
                        api_key=ai_cfg.api_key,
                        model=ai_cfg.model,
                        content=markdown_report,
                        system_prompt=system_prompt
                    )
                    markdown_report = f"{ai_summary}\n\n{markdown_report}"

                success = await WebhookService.send_wecom_markdown(notify_cfg.webhook_url, markdown_report)
                
                # 2. Update log to success or partial failed
                status = "success" if success else "failed"
                summary = f"执行完成：共统计到 {total_commits} 个提交" if success else "推送 Webhook 失败"
                
                def datetime_handler(x):
                    if isinstance(x, datetime):
                        return x.isoformat()
                    raise TypeError("Unknown type")

                log = db.query(TaskLog).filter(TaskLog.id == log_id).first()
                if log:
                    log.status = status
                    log.commit_count = total_commits
                    log.summary = summary
                    log.log_details = markdown_report[:5000]
                    log.raw_data = json.dumps(raw_data_obj, default=datetime_handler, ensure_ascii=False)
                    db.commit()
                
            except Exception as e:
                logger.error(f"Error executing task {task_id}: {e}")
                error_details = traceback.format_exc()
                
                if log_id:
                    log = db.query(TaskLog).filter(TaskLog.id == log_id).first()
                    if log:
                        log.status = "failed"
                        log.summary = f"执行异常: {str(e)}"
                        log.log_details = error_details
                        db.commit()
                else:
                    log = TaskLog(
                        task_id=task_id,
                        status="failed",
                        summary=f"初始化异常: {str(e)}",
                        log_details=error_details
                    )
                    db.add(log)
                    db.commit()
            finally:
                db.close()

scheduler_service = SchedulerService()
