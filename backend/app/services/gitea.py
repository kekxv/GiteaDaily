import json
from datetime import datetime
from typing import Any, Dict, List

from ..core.http_client import HttpClientManager


def get_report_type(report_days: int) -> str:
    return "weekly" if report_days >= 7 else "daily"


class GiteaService:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"token {token}"}

    async def get_my_info(self) -> Dict[str, Any]:
        client = HttpClientManager.get_client()
        response = await client.get(f"{self.base_url}/api/v1/user", headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return {}

    async def test_connection(self) -> bool:
        info = await self.get_my_info()
        return bool(info)

    async def get_all_repos(self, scope: str = "all") -> List[str]:
        repos = []
        page = 1
        client = HttpClientManager.get_client()
        gitea_type = "all" if scope == "all" else "individual"
        while True:
            response = await client.get(
                f"{self.base_url}/api/v1/user/repos",
                headers=self.headers,
                params={"page": page, "limit": 50, "type": gitea_type}
            )
            if response.status_code != 200:
                break
            data = response.json()
            if not data:
                break
            for repo in data:
                repos.append(repo["full_name"])
            page += 1
        return repos

    async def get_user_activities(self, username: str, since: datetime, user_id: int = None) -> List[Dict[str, Any]]:
        activities = []
        page = 1
        client = HttpClientManager.get_client()
        while True:
            response = await client.get(
                f"{self.base_url}/api/v1/users/{username}/activities/feeds",
                headers=self.headers,
                params={"page": page, "limit": 50}
            )
            if response.status_code != 200:
                break
            data = response.json()
            if not data:
                break

            finished = False
            for act in data:
                # If user_id is provided, verify it matches act_user_id
                if user_id and act.get("act_user_id") != user_id:
                    continue

                # Parse Gitea time and convert to same aware timezone for comparison
                created = datetime.fromisoformat(act["created"].replace("Z", "+00:00")).astimezone(since.tzinfo)
                if created < since:
                    finished = True
                    break
                activities.append(act)

            if finished or len(data) < 50:
                break
            page += 1
        return activities

    async def get_commits_for_repo(self, repo_full_name: str, since: datetime, until: datetime) -> List[Dict[str, Any]]:
        commits = []
        client = HttpClientManager.get_client()
        response = await client.get(
            f"{self.base_url}/api/v1/repos/{repo_full_name}/commits",
            headers=self.headers,
            params={"since": since.isoformat(), "stat": "false"}
        )
        if response.status_code == 200:
            data = response.json()
            for commit_item in data:
                commit_date = datetime.fromisoformat(commit_item["commit"]["author"]["date"].replace("Z", "+00:00"))
                if since <= commit_date <= until:
                    author_info = commit_item.get("author")
                    author_name = (author_info.get("full_name") if author_info else None) or \
                                 commit_item["commit"]["author"]["name"]
                    commits.append({
                        "repo": repo_full_name,
                        "author": author_name,
                        "message": commit_item["commit"]["message"].split("\n")[0],
                        "sha": commit_item["sha"][:7],
                        "url": commit_item["html_url"],
                        "date": commit_date
                    })
        return commits

    async def get_open_issues(self, repo_full_name: str) -> List[Dict[str, Any]]:
        issues = []
        client = HttpClientManager.get_client()
        response = await client.get(
            f"{self.base_url}/api/v1/repos/{repo_full_name}/issues",
            headers=self.headers,
            params={"state": "open", "type": "issues"}
        )
        if response.status_code == 200:
            data = response.json()
            for item in data:
                issues.append({
                    "id": item["number"],
                    "title": item["title"],
                    "url": item["html_url"],
                    "user": item["user"]["full_name"] or item["user"]["login"]
                })
        return issues

    async def get_open_prs(self, repo_full_name: str) -> List[Dict[str, Any]]:
        prs = []
        client = HttpClientManager.get_client()
        response = await client.get(
            f"{self.base_url}/api/v1/repos/{repo_full_name}/pulls",
            headers=self.headers,
            params={"state": "open"}
        )
        if response.status_code == 200:
            data = response.json()
            for item in data:
                prs.append({
                    "id": item["number"],
                    "title": item["title"],
                    "url": item["html_url"],
                    "user": item["user"]["full_name"] or item["user"]["login"]
                })
        return prs

    @staticmethod
    def _classify_message(msg: str) -> tuple:
        """根据 commit message 前缀分类，返回 (分类标签, 清理后的消息)"""
        msg_lower = msg.lower().strip()
        if msg_lower.startswith(('feat', '新增', 'add')):
            return '新增', msg.split(':', 1)[-1].strip() if ':' in msg else msg
        elif msg_lower.startswith(('fix', '修复', 'bug')):
            return '修复', msg.split(':', 1)[-1].strip() if ':' in msg else msg
        elif msg_lower.startswith(('update', '优化', 'refactor', 'chore', 'style', 'docs', 'perf')):
            return '优化', msg.split(':', 1)[-1].strip() if ':' in msg else msg
        elif msg_lower.startswith('merge'):
            return '合并', msg
        return '变更', msg

    @staticmethod
    def generate_markdown_report(since: datetime, until: datetime, report_days: int, data_by_repo: Dict[str, Dict[str, Any]]) -> str:
        COLOR_NEW = "#1976D2"
        COLOR_FIX = "#FF9800"
        COLOR_OPT = "#4CAF50"
        COLOR_MERGE = "#9E9E9E"
        COLOR_OTHER = "#666666"
        COLOR_PR = "#1976D2"
        COLOR_ISSUE = "#666666"

        type_colors = {"新增": COLOR_NEW, "修复": COLOR_FIX, "优化": COLOR_OPT, "合并": COLOR_MERGE, "变更": COLOR_OTHER}

        report_type = get_report_type(report_days)
        if report_type == "weekly":
            date_str = f"{since.strftime('%Y-%m-%d')} ~ {until.strftime('%Y-%m-%d')}"
            report = f"### 🚀 代码提交与任务周报 ({date_str})\n\n"
        else:
            date_str = since.strftime("%Y-%m-%d")
            report = f"### 🚀 代码提交与任务日报 ({date_str})\n\n"

        has_content = False
        total_commits = 0
        for repo, data in data_by_repo.items():
            commits = data.get("commits", [])
            issues = data.get("issues", [])
            prs = data.get("prs", [])

            if not (commits or issues or prs):
                continue

            has_content = True
            total_commits += len(commits)
            report += f"#### 📦 {repo}\n"

            if commits:
                # 按类型分组
                grouped = {}
                for c in commits:
                    label, clean_msg = GiteaService._classify_message(c["message"])
                    grouped.setdefault(label, []).append((clean_msg, c["author"]))
                for label in ["新增", "修复", "优化", "合并", "变更"]:
                    items = grouped.get(label, [])
                    if not items:
                        continue
                    color = type_colors[label]
                    for msg, author in items:
                        report += f"> <font color=\"{color}\">{label}</font> {msg} (@{author})\n"

            if prs:
                for p in prs:
                    report += f"> <font color=\"{COLOR_PR}\">PR #{p['id']}</font> {p['title']} (@{p['user']})\n"

            if issues:
                for i in issues:
                    report += f"> <font color=\"{COLOR_ISSUE}\">Issue #{i['id']}</font> {i['title']} (@{i['user']})\n"

            report += "\n"

        if not has_content:
            report += "此时间段内无活跃记录。"
        else:
            if report_type == "weekly":
                report += f"---\n**本周活跃概览: {total_commits} 个提交**"
            else:
                report += f"---\n**活跃概览: {total_commits} 个提交**"

        return report

    @staticmethod
    def generate_activity_report(since: datetime, until: datetime, report_days: int, data_by_repo: Dict[str, Dict[str, Any]], user_full_name: str) -> str:
        report_type = get_report_type(report_days)
        if report_type == "weekly":
            date_str = f"{since.strftime('%Y-%m-%d')} ~ {until.strftime('%Y-%m-%d')}"
            report = f"### 📝 {user_full_name} 的个人活动轨迹周报 ({date_str})\n\n"
        else:
            date_str = since.strftime("%Y-%m-%d")
            report = f"### 📝 {user_full_name} 的个人活动轨迹日报 ({date_str})\n\n"

        if not data_by_repo:
            report += "此时间段内无活动轨迹。"
            return report

        for repo, data in data_by_repo.items():
            report += f"#### 📦 {repo}\n"

            acts = data.get("activities", [])

            commit_messages = []
            seen_shas = set()

            for act in acts:
                op_type = act["op_type"]
                content_str = act.get("content", "")

                if (op_type == "commit_repo" or op_type == "push_repo") and content_str:
                    try:
                        content_json = json.loads(content_str)
                        for c in content_json.get("Commits", []):
                            sha = c.get("Sha1")
                            if sha not in seen_shas:
                                msg = c.get("Message", "").strip()
                                if msg:
                                    commit_messages.append(msg)
                                    seen_shas.add(sha)
                    except Exception:
                        pass

            if commit_messages:
                report += "**[代码提交]**\n"
                for msg in commit_messages:
                    report += f"- {msg}\n"

            other_acts = [a for a in acts if a["op_type"] not in ["commit_repo", "push_repo"]]
            if other_acts:
                for act in other_acts:
                    op_type = act["op_type"]
                    content = act.get("content", "")
                    index = act.get("index", "?")
                    if op_type == "create_issue":
                        report += f"- 创建了 Issue #{index} {content}\n"
                    elif op_type == "close_issue":
                        report += f"- 关闭了 Issue #{index}\n"
                    elif op_type == "create_pull_request":
                        report += f"- 创建了 PR #{index} {content}\n"
                    elif op_type == "merge_pull_request":
                        report += f"- 合并了 PR #{index}\n"
                    elif op_type == "comment_issue" or op_type == "comment_pull_request":
                        report += f"- 发表了评论于 #{index}\n"
            report += "\n"

        return report
