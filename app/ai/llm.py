"""
LLM gateway.

Single entry point for all text generation. Routes to:
  - Ollama (default, local) — `ollama` python client
  - Any LiteLLM-supported provider (OpenAI, Anthropic, Gemini, DeepSeek,
    OpenRouter, vLLM...) via `litellm.acompletion`.

Exposes a uniform async streaming + non-streaming interface and records token
usage. Swap providers at runtime via Settings.llm_provider / llm_model.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.core.config import settings


@dataclass(slots=True)
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class LLMGateway:
    """Provider-agnostic chat-completion gateway."""

    def __init__(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.provider = provider or settings.llm_provider
        self.model = model or settings.llm_model
        self.base_url = base_url or settings.ollama_base_url

    # ── Non-streaming ────────────────────────────────────────
    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list | None = None,
    ) -> LLMResponse:
        if self.provider == "ollama":
            return await self._ollama_chat(messages, temperature, max_tokens, tools)
        return await self._litellm_chat(messages, temperature, max_tokens, tools)

    # ── Streaming ────────────────────────────────────────────
    async def stream(
        self,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        if self.provider == "ollama":
            async for chunk in self._ollama_stream(messages, temperature, max_tokens):
                yield chunk
        else:
            async for chunk in self._litellm_stream(messages, temperature, max_tokens):
                yield chunk

    # ── Ollama backend ───────────────────────────────────────
    async def _ollama_chat(
        self,
        messages: list[dict],
        temperature: float | None,
        max_tokens: int | None,
        tools: list | None,
    ) -> LLMResponse:
        import ollama

        async with ollama.AsyncClient(host=self.base_url) as client:
            resp = await client.chat(
                model=self.model,
                messages=messages,
                stream=False,
                options={
                    "temperature": temperature if temperature is not None else settings.llm_temperature,
                    "num_predict": max_tokens or settings.llm_max_tokens,
                },
            )
        text = resp["message"]["content"] if isinstance(resp, dict) else resp.message.content
        return LLMResponse(
            text=text,
            model=self.model,
            prompt_tokens=_safe_eval(resp, "prompt_eval_count"),
            completion_tokens=_safe_eval(resp, "eval_count"),
        )

    async def _ollama_stream(
        self, messages: list[dict], temperature: float | None, max_tokens: int | None
    ) -> AsyncIterator[str]:
        import ollama

        async with ollama.AsyncClient(host=self.base_url) as client:
            async for part in await client.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options={
                    "temperature": temperature if temperature is not None else settings.llm_temperature,
                    "num_predict": max_tokens or settings.llm_max_tokens,
                },
            ):
                delta = part["message"]["content"] if isinstance(part, dict) else part.message.content
                if delta:
                    yield delta

    # ── LiteLLM backend (cloud providers) ────────────────────
    async def _litellm_chat(
        self, messages: list[dict], temperature: float | None, max_tokens: int | None, tools: list | None
    ) -> LLMResponse:
        import litellm

        litellm.modify_params = True
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.llm_temperature,
            "max_tokens": max_tokens or settings.llm_max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        resp = await litellm.acompletion(**kwargs)
        choice = resp.choices[0]
        return LLMResponse(
            text=choice.message.content or "",
            model=resp.model or self.model,
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
        )

    async def _litellm_stream(
        self, messages: list[dict], temperature: float | None, max_tokens: int | None
    ) -> AsyncIterator[str]:
        import litellm

        resp = await litellm.acompletion(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_tokens=max_tokens or settings.llm_max_tokens,
        )
        async for event in resp:
            delta = event.choices[0].delta.content
            if delta:
                yield delta


def _safe_eval(resp: Any, key: str) -> int:
    try:
        if isinstance(resp, dict):
            return int(resp.get(key, 0) or 0)
        return int(getattr(resp, key, 0) or 0)
    except Exception:
        return 0


# Module-level singleton
llm = LLMGateway()
