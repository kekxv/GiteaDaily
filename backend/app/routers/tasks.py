from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import ReportTask, User, GiteaConfig, NotifyConfig, AIConfig
from ..schemas import ReportTaskCreate, ReportTaskResponse
from ..services.scheduler import scheduler_service
from .auth import get_current_user

router = APIRouter()

@router.post("/", response_model=ReportTaskResponse)
def create_task(task: ReportTaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_task = ReportTask(**task.dict(), user_id=current_user.id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    if new_task.is_active:
        try:
            scheduler_service.add_or_update_task(new_task.id, new_task.cron_expression)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid cron expression: {e}")
            
    return new_task

@router.get("/", response_model=List[ReportTaskResponse])
def get_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ReportTask).filter(ReportTask.user_id == current_user.id).all()

@router.put("/{task_id}", response_model=ReportTaskResponse)
def update_task(task_id: int, task_data: ReportTaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(ReportTask).filter(ReportTask.id == task_id, ReportTask.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for key, value in task_data.dict().items():
        setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    
    if task.is_active:
        try:
            scheduler_service.add_or_update_task(task.id, task.cron_expression)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid cron expression: {e}")
    else:
        scheduler_service.remove_task(task.id)
        
    return task

@router.post("/test-run")
async def test_run_task(task_data: ReportTaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Get the actual configs from DB to get the tokens/urls
    gitea_cfg = await run_in_threadpool(
        lambda: db.query(GiteaConfig).filter(GiteaConfig.id == task_data.gitea_config_id, GiteaConfig.user_id == current_user.id).first()
    )
    notify_cfg = await run_in_threadpool(
        lambda: db.query(NotifyConfig).filter(NotifyConfig.id == task_data.notify_config_id, NotifyConfig.user_id == current_user.id).first()
    )
    
    if not gitea_cfg or not notify_cfg:
        raise HTTPException(status_code=404, detail="Gitea or Notify config not found")

    from ..services.gitea import GiteaService
    from ..services.webhook import WebhookService
    from datetime import datetime, timedelta

    gitea_service = GiteaService(gitea_cfg.base_url, gitea_cfg.token)
    
    # Use Aware Local Time
    now = datetime.now().astimezone()
    since = (now - timedelta(days=task_data.report_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    until = now

    markdown_report = ""
    data_by_repo = {}
    if task_data.scope_type == "user":
        user_info = await gitea_service.get_my_info()
        username = user_info.get("login")
        user_id = user_info.get("id")
        full_name = user_info.get("full_name") or username
        activities = await gitea_service.get_user_activities(username, since, user_id=user_id)
        
        # Group activities by repo for generate_activity_report
        for act in activities:
            repo_name = act["repo"]["full_name"]
            if repo_name not in data_by_repo:
                data_by_repo[repo_name] = {"activities": [], "detailed_commits": []}
            data_by_repo[repo_name]["activities"].append(act)
            
        markdown_report = gitea_service.generate_activity_report(since, data_by_repo, full_name)
    else:
        repos_to_check = []
        if task_data.scope_type in ["all", "owner"]:
            repos_to_check = await gitea_service.get_all_repos(scope=task_data.scope_type)
        else:
            repos_to_check = task_data.target_repos or []

        import asyncio
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

        markdown_report = gitea_service.generate_markdown_report(since, data_by_repo)
    
    # AI Summary in test run
    if task_data.is_ai_enabled and task_data.ai_config_id:
        ai_cfg = await run_in_threadpool(
            lambda: db.query(AIConfig).filter(AIConfig.id == task_data.ai_config_id, AIConfig.user_id == current_user.id).first()
        )
        if ai_cfg:
            from ..services.ai import AIService
            # Priority: Incoming task_data prompt > AI Config prompt
            system_prompt = task_data.ai_system_prompt or ai_cfg.system_prompt
            
            ai_summary = await AIService.summarize_report(
                api_base=ai_cfg.api_base,
                api_key=ai_cfg.api_key,
                model=ai_cfg.model,
                content=markdown_report,
                system_prompt=system_prompt
            )
            markdown_report = f"{ai_summary}\n\n{markdown_report}"

    success = await WebhookService.send_wecom_markdown(notify_cfg.webhook_url, f"【配置测试】\n{markdown_report}")
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to send notification to Webhook")
        
    return {"message": "Test report sent successfully", "commit_count": sum(len(d.get("commits", [])) for d in data_by_repo.values())}

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(ReportTask).filter(ReportTask.id == task_id, ReportTask.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    scheduler_service.remove_task(task.id)
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}

@router.post("/{task_id}/run")
async def run_task_immediately(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(ReportTask).filter(ReportTask.id == task_id, ReportTask.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # We can use the scheduler to run it once immediately
    import uuid
    from ..services.scheduler import scheduler_service
    
    # Generate a unique job id for this manual run
    job_id = f"manual_{task_id}_{uuid.uuid4().hex[:8]}"
    scheduler_service.scheduler.add_job(
        scheduler_service.execute_task,
        args=[task_id],
        id=job_id
    )
    return {"message": "Task execution triggered"}
