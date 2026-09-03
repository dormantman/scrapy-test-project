import asyncio

import httpx


class Fetcher:
    def __init__(self, client: httpx.AsyncClient, concurrency: int, retries: int, backoff: float) -> None:
        self._client = client
        self._retries = retries
        self._backoff = backoff
        self._semaphore = asyncio.Semaphore(concurrency)

    async def get(self, url: str) -> str:
        for attempt in range(self._retries + 1):
            try:
                async with self._semaphore:
                    response = await self._client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as error:
                if error.response.status_code < 500:
                    raise
                failure = error
            except httpx.TransportError as error:
                failure = error
            if attempt < self._retries:
                await asyncio.sleep(self._backoff * 2**attempt)
        raise failure
