import httpx

class HttpClientManager:
    _client: httpx.AsyncClient = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None or cls._client.is_closed:
            # Increase timeout to 120s for AI reasoning models
            cls._client = httpx.AsyncClient(timeout=120.0, follow_redirects=True)
        return cls._client

    @classmethod
    async def close_client(cls):
        if cls._client and not cls._client.is_closed:
            await cls._client.aclose()
