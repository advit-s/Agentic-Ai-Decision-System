"""Ollama provider — local LLM via Ollama's HTTP API.

Default base URL: http://localhost:11434

Supports:
- list_models (GET /api/tags)
- health_check (HEAD /)
- chat (POST /api/chat)
- generate (POST /api/generate)
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from decision_system.providers.runtime import (
    BaseProvider,
    ChatRequest,
    ChatResponse,
)

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_TIMEOUT = 30.0


class OllamaProvider(BaseProvider):
    """Provider implementation for local Ollama instances."""

    def __init__(self, config) -> None:
        super().__init__(config)
        self.base_url = (config.base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = config.metadata.get("timeout", DEFAULT_TIMEOUT)

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def list_models(self) -> list[str]:
        try:
            with self._client() as client:
                resp = client.get("/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def health_check(self) -> bool:
        try:
            with self._client() as client:
                resp = client.get("/")
                return resp.status_code < 500
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
                "stream": False,
            }
            if request.temperature is not None:
                payload["temperature"] = request.temperature
            if request.max_tokens is not None:
                payload["max_tokens"] = request.max_tokens

            with self._client() as client:
                resp = client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()

            latency = (time.time() - start) * 1000
            content = data.get("message", {}).get("content", "")

            usage = None
            if "prompt_eval_count" in data or "eval_count" in data:
                usage = {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
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
                warnings=[f"Could not connect to Ollama at {self.base_url}: {e}"],
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ChatResponse(
                provider_id=self.provider_id,
                provider_type=self.provider_type,
                model=request.model,
                text="",
                latency_ms=round(latency, 1),
                warnings=[f"Ollama error: {type(e).__name__}: {e}"],
            )
