import re
from typing import Optional

from openai import AsyncOpenAI

from ..core.http_client import HttpClientManager

# 默认系统提示词 - 结构化日报格式
DEFAULT_SUMMARY_PROMPT = """你是一个代码提交日报助手。请根据提供的 Git 提交记录生成一份结构化的日报。

## 输出格式要求

### 📊 今日工作摘要
用 2-3 句话概括今日的主要工作内容、进展和成果。

### 📦 项目变更详情
按项目分组，列出关键变更：
- **项目名**: 简要描述主要变更（2-3 条）

### ⚠️ 重点关注
如有重要功能、Bug 修复、架构改进或待处理事项，在此突出说明。

---
请保持简洁，适合在企业微信中阅读。使用中文回复。直接输出 Markdown 格式内容。"""


class AIService:
    @staticmethod
    async def summarize_report(
        api_base: str,
        api_key: str,
        model: str,
        content: str,
        system_prompt: Optional[str] = None
    ) -> str:
        if not system_prompt:
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
                max_tokens=2000,  # 确保输出足够长
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

            return res_content

        except Exception as e:
            import traceback

            import httpx
            error_details = traceback.format_exc()

            # Special handling for common httpx errors to make them more readable
            error_msg = str(e)
            if isinstance(e, httpx.ConnectError):
                error_msg = f"网络连接失败，请检查 API Base URL 是否正确且可访问。详情: {error_msg}"
            elif isinstance(e, httpx.TimeoutException):
                error_msg = f"请求超时，模型响应过慢或网络不通。详情: {error_msg}"
            elif isinstance(e, httpx.HTTPStatusError):
                error_msg = f"API 返回了错误状态码: {e.response.status_code}。内容: {e.response.text}"

            return f"AI 总结出错: {error_msg}\n详情: {error_details[:300]}"
