"""Async streaming client for NVIDIA's OpenAI-compatible chat completions API.

Standalone module — no FastAPI imports. Can be tested independently via
``backend/scripts/test_nvidia_client.py``.

Design choice for token-usage tracking: callers pass an optional mutable dict
``usage_out``.  After the generator is exhausted, ``usage_out`` will contain
the ``usage`` payload (prompt_tokens, completion_tokens, total_tokens) if the
API returned it.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Exceptions ──────────────────────────────────────────────────────────────

class NvidiaAPIError(Exception):
    """Raised when the NVIDIA API returns an error response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"NVIDIA API error {status_code}: {message}")


class NvidiaTimeoutError(NvidiaAPIError):
    """Raised when the NVIDIA API request times out."""

    def __init__(self, message: str = "Request to NVIDIA API timed out") -> None:
        super().__init__(status_code=0, message=message)


class NvidiaRateLimitError(NvidiaAPIError):
    """Raised when the NVIDIA API returns a 429 rate limit error."""

    def __init__(self, message: str, retry_after: str | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(status_code=429, message=message)


# ── Retry config ────────────────────────────────────────────────────────────

_MAX_RETRIES = 3
_BASE_DELAY_S = 1.0


# ── Core streaming function ────────────────────────────────────────────────

async def stream_chat_completion(
    messages: list[dict[str, str]],
    *,
    usage_out: dict[str, Any] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream incremental text from NVIDIA's chat completions endpoint.

    Yields only the ``delta.content`` text fragments as they arrive.

    Args:
        messages: OpenAI-format list of ``{"role": ..., "content": ...}`` dicts.
        usage_out: Optional mutable dict. After the generator is fully consumed,
            this dict will be populated with token-usage data (if the API
            returned it), e.g. ``{"prompt_tokens": 10, ...}``.

    Raises:
        NvidiaAPIError: On 4xx or exhausted retries for 5xx responses.
        NvidiaTimeoutError: On request timeout.
    """
    url = f"{settings.nvidia_api_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "model": settings.nvidia_model,
        "messages": messages,
        "temperature": settings.nvidia_temperature,
        "max_tokens": settings.nvidia_max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    timeout = httpx.Timeout(
        settings.nvidia_request_timeout_seconds,
        connect=10.0,
    )

    last_error: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST", url, headers=headers, json=payload,
                ) as response:
                    # ── Handle error status codes ──────────────────────
                    if response.status_code >= 400:
                        body = await response.aread()
                        body_text = body.decode(errors="replace")
                        if response.status_code < 500:
                            # 4xx — don't retry
                            if response.status_code == 429:
                                raise NvidiaRateLimitError(
                                    body_text,
                                    retry_after=response.headers.get("retry-after")
                                )
                            raise NvidiaAPIError(
                                response.status_code, body_text,
                            )
                        # 5xx — retry
                        last_error = NvidiaAPIError(
                            response.status_code, body_text,
                        )
                        delay = _BASE_DELAY_S * (2 ** attempt)
                        logger.warning(
                            "NVIDIA API 5xx (attempt %d/%d), retrying in %.1fs",
                            attempt + 1, _MAX_RETRIES, delay,
                        )
                        await asyncio.sleep(delay)
                        continue

                    # ── Parse SSE stream ───────────────────────────────
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        data = line[len("data: "):]

                        if data.strip() == "[DONE]":
                            return

                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            logger.warning(
                                "Malformed JSON chunk, skipping: %s",
                                data[:200],
                            )
                            continue

                        # Capture usage if present
                        if "usage" in chunk and chunk["usage"] is not None:
                            if usage_out is not None:
                                usage_out.update(chunk["usage"])

                        # Yield incremental content
                        choices = chunk.get("choices")
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content

                    # Stream ended without [DONE] — still success
                    return

        except NvidiaAPIError:
            raise
        except httpx.TimeoutException as exc:
            raise NvidiaTimeoutError(
                f"Request to NVIDIA API timed out after "
                f"{settings.nvidia_request_timeout_seconds}s: {exc}",
            ) from exc
        except httpx.ConnectError as exc:
            last_error = exc
            delay = _BASE_DELAY_S * (2 ** attempt)
            logger.warning(
                "Connection error (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, _MAX_RETRIES, delay, exc,
            )
            await asyncio.sleep(delay)
            continue

    # All retries exhausted
    if isinstance(last_error, NvidiaAPIError):
        raise last_error
    raise NvidiaAPIError(
        status_code=0,
        message=f"Failed after {_MAX_RETRIES} retries: {last_error}",
    )


# ── Non-streaming convenience wrapper ──────────────────────────────────────

async def get_full_completion(
    messages: list[dict[str, str]],
    *,
    usage_out: dict[str, Any] | None = None,
) -> str:
    """Consume the streaming endpoint and return the full concatenated text.

    Useful for cases where streaming is not needed, such as auto-titling
    conversations.

    Args:
        messages: OpenAI-format message list.
        usage_out: Optional dict to capture token usage.

    Returns:
        The complete assistant response as a single string.
    """
    parts: list[str] = []
    async for chunk in stream_chat_completion(messages, usage_out=usage_out):
        parts.append(chunk)
    return "".join(parts)
