"""
HeartBeat Engine - OpenRouter Provider Adapter
Montreal Canadiens Advanced Analytics Assistant

Thin adapter around OpenRouter's OpenAI-compatible API to keep the rest of the
codebase provider-agnostic. Provides simple generation utilities that can be
swapped or extended later (e.g., streaming, planner JSON modes).
"""

from typing import Dict, Any, Optional, List
import os
import logging

try:
    import openai
except ImportError:
    openai = None

logger = logging.getLogger(__name__)


class OpenRouterProvider:
    """
    Minimal provider using OpenRouter via the OpenAI SDK (base_url override).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        http_referer: Optional[str] = None,
        app_title: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        if not openai:
            raise RuntimeError("openai library not available. Install openai>=1.0.0")

        #Do NOT hardcode API keys. Read from environment only.
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        self.base_url = base_url
        self.timeout = timeout

        headers = {}
        # OpenRouter recommends these headers for attribution/listing
        if http_referer or os.getenv("OPENROUTER_HTTP_REFERER"):
            headers["HTTP-Referer"] = http_referer or os.getenv("OPENROUTER_HTTP_REFERER")
        if app_title or os.getenv("OPENROUTER_APP_TITLE"):
            headers["X-Title"] = app_title or os.getenv("OPENROUTER_APP_TITLE")

        # Async client for non-blocking server flows
        self._client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers=headers if headers else None,
            timeout=self.timeout,
        )

        # Basic rate limiting and retry configuration
        try:
            from asyncio_throttle import Throttler
        except Exception:
            Throttler = None  # Optional dependency
        rps = float(os.getenv("OPENROUTER_RPS", "5"))  # requests per second
        self._throttler = Throttler(rate_limit=rps, period=1.0) if 'Throttler' in locals() and Throttler else None
        self._max_retries = int(os.getenv("OPENROUTER_MAX_RETRIES", "2"))

    async def generate(
        self,
        model: str,
        system_prompt: Optional[str],
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        extra_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a completion with the specified model and prompts.
        Returns a dict with keys: text, usage, raw.
        """
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": user_prompt})

        try:
            resp = await self._chat_with_retry(
                payload={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                }
            )
            choice = resp.choices[0].message
            text = getattr(choice, "content", "") or ""
            return {
                "text": text,
                "usage": getattr(resp, "usage", None),
                "raw": resp,
            }
        except Exception as e:
            logger.error(f"OpenRouter generate failed: {e}")
            raise

    async def _chat_with_retry(self, payload: dict):
        import asyncio, random
        attempt = 0
        last_exc = None
        while attempt <= self._max_retries:
            attempt += 1
            try:
                if self._throttler:
                    async with self._throttler:
                        return await self._client.chat.completions.create(**payload)
                return await self._client.chat.completions.create(**payload)
            except Exception as e:
                last_exc = e
                # Simple backoff on rate limit or transient errors
                msg = str(e).lower()
                if any(code in msg for code in ["429", "rate limit", "timeout", "temporarily unavailable", "5xx", "internal server error"]):
                    await asyncio.sleep(min(2 ** attempt, 8) + random.uniform(0, 0.25))
                    continue
                break
        raise last_exc


