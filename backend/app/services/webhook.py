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

        # Split into blocks separated by double newlines (markdown sections)
        blocks = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_bytes = 0

        for block in blocks:
            block_with_sep = block + '\n\n'
            block_bytes = len(block_with_sep.encode('utf-8'))

            if block_bytes > max_bytes:
                # Block itself is too large, split by lines
                if current_chunk:
                    chunks.append("".join(current_chunk).rstrip('\n'))
                    current_chunk = []
                    current_bytes = 0
                # Split large block by lines
                for line in block.splitlines(keepends=True):
                    line_bytes = len(line.encode('utf-8'))
                    if line_bytes > max_bytes:
                        # Force split a very long line
                        if current_chunk:
                            chunks.append("".join(current_chunk).rstrip('\n'))
                            current_chunk = []
                            current_bytes = 0
                        current_chunk.append(line[:max_bytes] + '...')
                        chunks.append("".join(current_chunk).rstrip('\n'))
                        current_chunk = []
                        current_bytes = 0
                    elif current_bytes + line_bytes > max_bytes:
                        chunks.append("".join(current_chunk).rstrip('\n'))
                        current_chunk = [line]
                        current_bytes = line_bytes
                    else:
                        current_chunk.append(line)
                        current_bytes += line_bytes
            elif current_bytes + block_bytes > max_bytes:
                chunks.append("".join(current_chunk).rstrip('\n'))
                current_chunk = [block_with_sep]
                current_bytes = block_bytes
            else:
                current_chunk.append(block_with_sep)
                current_bytes += block_bytes

        if current_chunk:
            chunks.append("".join(current_chunk).rstrip('\n'))

        return chunks
