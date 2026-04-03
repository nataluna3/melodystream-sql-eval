"""
Thin Fireworks client using the official OpenAI Python SDK (OpenAI-compatible).

See: https://fireworks.ai/docs/tools-sdks/openai-compatibility
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI

from melodystream_eval.config import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    FIREWORKS_BASE_URL,
)


@dataclass
class ChatCompletionResult:
    """Structured LLM output plus latency for benchmarking."""

    text: str
    model: str
    latency_seconds: float
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]


def _require_api_key() -> str:
    key = os.environ.get("FIREWORKS_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "FIREWORKS_API_KEY is not set. Add it to .env (see .env.example) "
            "or export it in your shell before running evaluations."
        )
    return key


def create_client() -> OpenAI:
    """OpenAI-compatible client pointed at Fireworks inference."""
    return OpenAI(api_key=_require_api_key(), base_url=FIREWORKS_BASE_URL)


def chat_completion(
    client: OpenAI,
    model: str,
    system: str,
    user: str,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> ChatCompletionResult:
    """
    Single-turn chat completion; returns assistant message content.

    temperature=0 reduces sampling variance for repeatable eval passes.
    """
    messages: List[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    latency = time.perf_counter() - t0

    choice = response.choices[0]
    text = (choice.message.content or "").strip()
    usage = getattr(response, "usage", None)
    pt = getattr(usage, "prompt_tokens", None) if usage else None
    ct = getattr(usage, "completion_tokens", None) if usage else None
    tt = getattr(usage, "total_tokens", None) if usage else None

    return ChatCompletionResult(
        text=text,
        model=model,
        latency_seconds=latency,
        prompt_tokens=pt,
        completion_tokens=ct,
        total_tokens=tt,
    )
