import re
from typing import Optional

from openai import AsyncOpenAI

from ..core.http_client import HttpClientManager
from .gitea import get_report_type

# 默认系统提示词 - 结构化日报格式（适配企业微信Markdown）
DEFAULT_SUMMARY_PROMPT = """你是一个代码提交日报助手。
请根据提供的 Git 提交记录，生成一份简洁、结构化的日报。

## 企业微信 Markdown 语法限制

支持的语法：标题（# 后必须有空格）、加粗 **bold**、链接、行内代码、引用 > 文字、颜色字体
不支持的语法：列表（- 或 1.）、代码块、表格

## 输出格式要求

### 工作日报 (日期)

> <font color="#1976D2">新增</font> 功能描述
> <font color="#FF9800">修复</font> bug描述
> <font color="#4CAF50">优化</font> 优化描述

#### 仓库名
> <font color="#1976D2">PR #编号</font> PR标题
> <font color="#666666">Issue #编号</font> Issue标题

**活跃概览: X 个提交**

## 注意
- 提交和 PR/Issue 都需要总结，不要遗漏
- 每条变更独立一行，用 > 开头
- 不要将多条内容合并到同一行
- 相同内容（如相同 PR 编号和标题）要去重，不要重复输出
- 不要输出"其他变更描述"等模板文字
- 直接输出 Markdown 格式内容，不要有任何额外说明"""

# 默认系统提示词 - 结构化周报格式（整周视角）
DEFAULT_WEEKLY_SUMMARY_PROMPT = """你是一个代码提交周报助手。
请根据提供的 Git 提交记录，从整周视角总结本周的工作内容。

## 企业微信 Markdown 语法限制

支持的语法：标题（# 后必须有空格）、加粗 **bold**、链接、行内代码、引用 > 文字、颜色字体
不支持的语法：列表（- 或 1.）、代码块、表格

## 输出格式要求

### 工作周报 (日期范围)

> <font color="#1976D2">新增</font> 功能描述
> <font color="#FF9800">修复</font> bug描述
> <font color="#4CAF50">优化</font> 优化描述

#### 仓库名
> <font color="#1976D2">PR #编号</font> PR标题
> <font color="#666666">Issue #编号</font> Issue标题

**本周活跃概览: X 个提交**

## 注意
- 提交和PR/Issue 都需要总结，不要遗漏
- 每条变更独立一行，用 > 开头
- 不要将多条内容合并到同一行
- 相同内容（如相同 PR 编号和标题）要去重，不要重复输出
- 不要输出"其他变更描述"等模板文字
- 直接输出 Markdown 格式内容，不要有任何额外说明"""


class AIService:
    @staticmethod
    async def summarize_report(
        api_base: str,
        api_key: str,
        model: str,
        content: str,
        system_prompt: Optional[str] = None,
        report_days: int = 1
    ) -> Optional[str]:
        if not system_prompt:
            if get_report_type(report_days) == "weekly":
                system_prompt = DEFAULT_WEEKLY_SUMMARY_PROMPT
            else:
                system_prompt = DEFAULT_SUMMARY_PROMPT

        # Use the official OpenAI SDK for better compatibility
        base_url = api_base.rstrip("/")

        if not base_url.startswith(("http://", "https://")):
            return f"AI 总结出错: API Base URL 必须以 http:// 或 https:// 开头。当前值: {api_base}"

        # Security/Config Check: If running in Docker and using localhost, it will likely fail
        # This is a common pitfall for users using local LLMs like Ollama
        if "localhost" in base_url or "127.0.0.1" in base_url:
            print(f"WARNING: AI API Base URL contains 'localhost' or '127.0.0.1': {base_url}")
            print("If you are running in Docker, this will refer to the container itself, not the host.")

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            # Use our managed httpx client to reuse connections
            http_client=HttpClientManager.get_client()
        )

        print(f"DEBUG: AI Request - Base: {api_base}, Model: {model}")
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请总结以下内容：\n\n{content}"}
                ],
                max_tokens=8000,  # 确保周报等长内容不被截断
                timeout=120.0 # Reasoning models take longer
            )

            # Extract content
            res_content = response.choices[0].message.content or ""

            # Handle "Think" mode:
            # 1. Some providers put thinking in reasoning_content (ignored for the final summary)
            # 2. Some put it inside <think> tags in the main content
            if "<think>" in res_content:
                res_content = re.sub(r'<think>.*?</think>', '', res_content, flags=re.DOTALL).strip()

            if not res_content:
                return "⚠️ AI 返回了空内容，请检查模型配置或提示词。"

            if len(res_content) < 20:
                return "⚠️ AI 返回内容过短，可能是模型响应异常。"

            # 检测 AI 输出是否被截断（仅当接近 max_tokens 上限时）
            truncated = False
            if len(res_content) >= 7900:
                # 接近 max_tokens 上限，检查末尾是否完整
                last_line = res_content.rstrip().split('\n')[-1] if res_content.strip() else ""
                if last_line and not any(last_line.endswith(c) for c in '.。!！\n'):
                    truncated = True

            if truncated:
                # 返回 None 信号，让调用方回退到原始报告
                return None

            # 去重：移除重复的行（基于行内容哈希）
            lines = res_content.split('\n')
            seen = set()
            deduped_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and stripped in seen:
                    continue
                seen.add(stripped)
                deduped_lines.append(line)
            res_content = '\n'.join(deduped_lines)

            return res_content

        except Exception as e:
            import httpx

            # Special handling for common httpx errors to make them more readable
            error_msg = str(e)
            if isinstance(e, httpx.ConnectError):
                error_msg = f"网络连接失败，请检查 API Base URL 是否正确且可访问。详情: {error_msg}"
            elif isinstance(e, httpx.TimeoutException):
                error_msg = f"请求超时，模型响应过慢或网络不通。详情: {error_msg}"
            elif isinstance(e, httpx.HTTPStatusError):
                # Extract error message from response body if available
                try:
                    body = e.response.json()
                    err_detail = body.get("error", {}).get("message", "")
                    if err_detail:
                        error_msg = f"API 返回错误 ({e.response.status_code}): {err_detail}"
                    else:
                        error_msg = f"API 返回了错误状态码: {e.response.status_code}"
                except Exception:
                    error_msg = f"API 返回了错误状态码: {e.response.status_code}。内容: {e.response.text[:200]}"
            elif "model failed to load" in error_msg or "resource limitations" in error_msg:
                error_msg = "AI 模型加载失败，请检查 Ollama 服务器日志。"

            return f"AI 总结出错: {error_msg}"
