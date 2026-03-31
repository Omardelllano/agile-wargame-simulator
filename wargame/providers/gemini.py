import asyncio
import os
import time

from wargame.exceptions import ProviderError
from wargame.models.agent_response import AgentResponse
from wargame.providers.base import BaseLLMProvider

# Gemini free tier: 15 RPM for gemini-2.0-flash; we cap at 12 RPM for safety
_GEMINI_RPM = 12
_MIN_INTERVAL = 60.0 / _GEMINI_RPM  # 5 seconds between requests


class _RateLimiter:
    """Simple token-bucket rate limiter for async code."""

    def __init__(self, min_interval: float):
        self._min_interval = min_interval
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()


_rate_limiter = _RateLimiter(_MIN_INTERVAL)


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini-free"

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model

    async def complete(self, system_prompt: str, user_prompt: str) -> AgentResponse:
        import litellm

        await _rate_limiter.acquire()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = await litellm.acompletion(
                model=f"gemini/{self.model}",
                messages=messages,
                api_key=os.environ.get("GEMINI_API_KEY"),
            )
            raw = response.choices[0].message.content
            return self._parse_response(raw)
        except Exception as exc:
            raise ProviderError(f"GeminiProvider error: {exc}") from exc

    def is_available(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY"))
