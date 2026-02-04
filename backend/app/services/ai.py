import re
from typing import Optional
from openai import AsyncOpenAI
from ..core.http_client import HttpClientManager

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
            system_prompt = (
                "你是一个资深软件工程师，请根据提供的代码提交记录、PR和Issue，"
                "总结出一份简洁、专业的日报。重点突出重要的变更和待办事项。"
                "请直接返回总结后的 Markdown 内容，不要包含多余的解释。"
            )

        # Use the official OpenAI SDK for better compatibility
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base.rstrip("/"),
            # Use our managed httpx client to reuse connections
            http_client=HttpClientManager.get_client()
        )

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请总结以下内容：\n\n{content}"}
                ],
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
                return "AI 返回了空内容，请检查模型配置或提示词。"
                
            return res_content

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"AI 总结出错: {str(e)}\n详情: {error_details[:200]}"
