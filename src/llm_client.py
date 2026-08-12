from __future__ import annotations

import os
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass(slots=True)
class RateLimiter:
    """
    Simple in-memory rate limiter using a fixed-window approach.

    Enforces at most `max_calls` per `window_seconds` across all callers
    that share this instance. Thread-safe for multi-threaded use.
    """

    max_calls: int
    window_seconds: float
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _calls: list[float] = field(default_factory=list, repr=False)

    def acquire(self) -> float:
        """
        Block until a call slot is available, then record the call.

        Returns the time spent waiting (in seconds).
        """
        with self._lock:
            now = time.perf_counter()
            window_start = now - self.window_seconds

            # Drop calls outside the current window
            self._calls = [t for t in self._calls if t > window_start]

            if len(self._calls) < self.max_calls:
                # Slot available immediately
                self._calls.append(now)
                return 0.0

            # Need to wait until the oldest call exits the window
            oldest = self._calls[0]
            wait_until = oldest + self.window_seconds
            wait_seconds = wait_until - now

        # Sleep outside the lock so other threads can proceed
        if wait_seconds > 0:
            time.sleep(wait_seconds)

        # Re-acquire and record after waiting
        with self._lock:
            now = time.perf_counter()
            window_start = now - self.window_seconds
            self._calls = [t for t in self._calls if t > window_start]
            self._calls.append(now)

        return max(0.0, wait_seconds)


def get_default_model() -> str:
    model = os.getenv("MODEL_ID")
    if not model:
        raise ValueError("MODEL_ID is not set")
    return model


def get_client(
    api_key: str | None = None,
    base_url: str | None = None,
) -> OpenAI:
    resolved_api_key = api_key or os.getenv("LLM_API_KEY")
    resolved_base_url = base_url or os.getenv("LLM_BASE_URL")

    kwargs: dict[str, Any] = {}
    if resolved_api_key:
        kwargs["api_key"] = resolved_api_key
    if resolved_base_url:
        kwargs["base_url"] = resolved_base_url

    return OpenAI(**kwargs)


def _build_messages(
    instructions: str,
    user_prompt: str,
) -> list[dict[str, str]]:
    return [
        {"role": "developer", "content": instructions},
        {"role": "user", "content": user_prompt},
    ]


def _is_retryable_error(exc: Exception) -> bool:
    message = str(exc).lower()
    retry_markers = [
        "429",
        "rate limit",
        "quota",
        "resource exhausted",
        "temporarily unavailable",
        "timeout",
        "timed out",
        "connection reset",
        "internal error",
        "server error",
        "503",
        "502",
        "504",
    ]
    return any(marker in message for marker in retry_markers)


def _compute_backoff_seconds(
    attempt: int,
    initial_wait: float,
    max_wait: float,
    jitter_ratio: float,
) -> float:
    base = min(max_wait, initial_wait * (2 ** attempt))
    jitter = base * jitter_ratio * random.random()
    return base + jitter


def generate_structured_answer(
    *,
    instructions: str,
    user_prompt: str,
    output_type: type[SchemaT],
    model: str | None = None,
    client: OpenAI | None = None,
    max_retries: int = 6,
    initial_wait: float = 8.0,
    max_wait: float = 60.0,
    jitter_ratio: float = 0.25,
    verbose: bool = True,
    rate_limiter: RateLimiter | None = None,
) -> tuple[SchemaT, Any]:
    resolved_client = client or get_client()
    resolved_model = model or get_default_model()

    # Optional rate limiting (primarily for batch tasks)
    if rate_limiter is not None:
        wait_seconds = rate_limiter.acquire()
        if verbose and wait_seconds > 0:
            print(f"[RATE LIMIT] Waited {wait_seconds:.2f}s before LLM call")

    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = resolved_client.beta.chat.completions.parse(
                model=resolved_model,
                messages=_build_messages(instructions, user_prompt),
                response_format=output_type,
            )
            parsed = response.choices[0].message.parsed
            usage = response.usage
            return parsed, usage
        except Exception as exc:
            last_error = exc

            if not _is_retryable_error(exc) or attempt == max_retries - 1:
                raise

            wait_seconds = _compute_backoff_seconds(
                attempt=attempt,
                initial_wait=initial_wait,
                max_wait=max_wait,
                jitter_ratio=jitter_ratio,
            )

            if verbose:
                print(
                    f"[WARN] Structured generation failed "
                    f"(attempt {attempt + 1}/{max_retries}): {type(exc).__name__}: {exc}"
                )
                print(f"[INFO] Waiting {wait_seconds:.1f} seconds before retrying...")

            time.sleep(wait_seconds)

    if last_error is not None:
        raise last_error

    raise RuntimeError("Structured generation failed without a captured exception.")


def generate_text_answer(
    *,
    instructions: str,
    user_prompt: str,
    model: str | None = None,
    client: OpenAI | None = None,
    max_retries: int = 6,
    initial_wait: float = 8.0,
    max_wait: float = 60.0,
    jitter_ratio: float = 0.25,
    verbose: bool = True,
    rate_limiter: RateLimiter | None = None,
) -> tuple[str, Any]:
    resolved_client = client or get_client()
    resolved_model = model or get_default_model()

    # Optional rate limiting (primarily for batch tasks)
    if rate_limiter is not None:
        wait_seconds = rate_limiter.acquire()
        if verbose and wait_seconds > 0:
            print(f"[RATE LIMIT] Waited {wait_seconds:.2f}s before LLM call")

    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = resolved_client.chat.completions.create(
                model=resolved_model,
                messages=_build_messages(instructions, user_prompt),
            )
            content = response.choices[0].message.content
            text = content if isinstance(content, str) else str(content)
            usage = response.usage
            return text, usage
        except Exception as exc:
            last_error = exc

            if not _is_retryable_error(exc) or attempt == max_retries - 1:
                raise

            wait_seconds = _compute_backoff_seconds(
                attempt=attempt,
                initial_wait=initial_wait,
                max_wait=max_wait,
                jitter_ratio=jitter_ratio,
            )

            if verbose:
                print(
                    f"[WARN] Text generation failed "
                    f"(attempt {attempt + 1}/{max_retries}): {type(exc).__name__}: {exc}"
                )
                print(f"[INFO] Waiting {wait_seconds:.1f} seconds before retrying...")

            time.sleep(wait_seconds)

    if last_error is not None:
        raise last_error

    raise RuntimeError("Text generation failed without a captured exception.")