"""OpenAI-compatible provider — for local endpoints (LM Studio, vLLM, LocalAI, etc.).

Supports:
- list_models (GET /v1/models)
- health_check (GET /v1/models)
- chat (POST /v1/chat/completions)

API key is optional for local endpoints.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from decision_system.providers.runtime import (
    BaseProvider, ChatRequest, ChatResponse,
)

DEFAULT_TIMEOUT = 30.0


class OpenAICompatibleProvider(BaseProvider):
    """Provider implementation for OpenAI-compatible local endpoints."""

    def __init__(self, config) -> None:
        super().__init__(config)
        self.base_url = (config.base_url or "").rstrip("/")
        self.timeout = config.metadata.get("timeout", DEFAULT_TIMEOUT)
        self.api_key = None
        if config.api_key_env:
            self.api_key = os.environ.get(config.api_key_env)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def list_models(self) -> list[str]:
        try:
            with self._client() as client:
                resp = client.get("/v1/models", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    def health_check(self) -> bool:
        try:
            models = self.list_models()
            return len(models) > 0
        except Exception:
            return False

    def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.time()
        try:
            messages = []
            for m in request.messages:
                messages.append({"role": m.role, "content": m.content})

            payload: dict[str, Any] = {
                "model": request.model,
                "messages": messages,
            }
            if request.temperature is not None:
                payload["temperature"] = request.temperature
            if request.max_tokens is not None:
                payload["max_tokens"] = request.max_tokens
            if request.response_format:
                payload["response_format"] = request.response_format

            with self._client() as client:
                resp = client.post("/v1/chat/completions", json=payload, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()

            latency = (time.time() - start) * 1000
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            if content is None:
                content = ""

            usage = data.get("usage")
            if usage:
                usage = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }

            return ChatResponse(
                provider_id=self.provider_id,
                provider_type=self.provider_type,
                model=request.model,
                text=content,
                usage=usage,
                latency_ms=round(latency, 1),
                raw=data,
            )
        except httpx.ConnectError as e:
            latency = (time.time() - start) * 1000
            return ChatResponse(
                provider_id=self.provider_id,
                provider_type=self.provider_type,
                model=request.model,
                text="",
                latency_ms=round(latency, 1),
                warnings=[f"Could not connect to endpoint at {self.base_url}: {e}"],
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ChatResponse(
                provider_id=self.provider_id,
                provider_type=self.provider_type,
                model=request.model,
                text="",
                latency_ms=round(latency, 1),
                warnings=[f"Provider error: {type(e).__name__}: {e}"],
            )
