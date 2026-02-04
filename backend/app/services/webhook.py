import httpx
from typing import List
from ..core.http_client import HttpClientManager

class WebhookService:
    @staticmethod
    async def send_wecom_markdown(webhook_url: str, content: str) -> bool:
        MAX_BYTES = 4000
        chunks = WebhookService._split_content(content, MAX_BYTES)
        
        success = True
        client = HttpClientManager.get_client()
        for i, chunk in enumerate(chunks):
            payload_content = chunk
            if len(chunks) > 1:
                payload_content = f"{chunk}\n\n(续 {i+1}/{len(chunks)})"
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": payload_content
                }
            }
            try:
                response = await client.post(webhook_url, json=payload)
                if response.status_code != 200:
                    success = False
            except Exception:
                success = False
        return success

    @staticmethod
    def _split_content(content: str, max_bytes: int) -> List[str]:
        if len(content.encode('utf-8')) <= max_bytes:
            return [content]
        chunks = []
        current_chunk = []
        current_bytes = 0
        for line in content.splitlines(keepends=True):
            line_bytes = len(line.encode('utf-8'))
            if current_bytes + line_bytes > max_bytes:
                if current_chunk:
                    chunks.append("".join(current_chunk))
                current_chunk = [line]
                current_bytes = line_bytes
            else:
                current_chunk.append(line)
                current_bytes += line_bytes
        if current_chunk:
            chunks.append("".join(current_chunk))
        return chunks