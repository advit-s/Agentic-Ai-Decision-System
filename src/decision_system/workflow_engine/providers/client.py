"""LLMClient — unified OpenAI-compatible HTTP caller.

Uses httpx to call any OpenAI-compatible ``/chat/completions`` endpoint
with streaming support. One client works with OpenAI, OpenRouter,
opencode, NVIDIA NIM, Ollama, Groq, Cerebras, and any other provider
that speaks the OpenAI chat format.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Callable

import httpx

from decision_system.workflow_engine.providers.exceptions import (
    AuthenticationError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)
from decision_system.workflow_engine.providers.store import ProviderConfig


class LLMClient:
    """HTTP client for OpenAI-compatible chat completion endpoints.

    Handles authentication, streaming SSE parsing, error mapping,
    and token accumulation. One instance per provider configuration.

    Usage::

        client = LLMClient(provider_config)
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o",
            stream=True,
            on_token=lambda t: print(t, end=""),
        )
    """

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._api_base = config.api_base.rstrip("/")
        self._api_key = os.environ.get(config.api_key_env) if config.api_key_env else None

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        stream: bool = True,
        on_token: Callable[[str], Any] | None = None,
    ) -> str:
        """Send a chat completion request and return the full response text.

        Args:
            messages: List of message dicts with ``role`` and ``content``.
            model: Model name. Falls back to provider's ``default_model``.
            stream: Whether to use SSE streaming (default ``True``).
            on_token: Async callback for each content token during streaming.

        Returns:
            The full accumulated response text.

        Raises:
            AuthenticationError: API key is missing or invalid.
            RateLimitError: Provider returned 429.
            ModelNotFoundError: Model doesn't exist on this provider.
            TimeoutError: Request timed out.
            ProviderError: Other provider errors.
        """
        if self._config.api_key_env and not self._api_key:
            raise AuthenticationError(
                f"API key not configured for provider '{self._config.name}'. "
                f"Set the {self._config.api_key_env} environment variable."
            )

        resolved_model = model or self._config.default_model
        url = f"{self._api_base}/chat/completions"

        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        body: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "stream": stream,
        }

        timeout = httpx.Timeout(30.0, connect=10.0, read=30.0)

        async with httpx.AsyncClient(timeout=timeout) as http:
            if stream:
                return await self._stream_response(http, url, headers, body, on_token)
            else:
                return await self._single_response(http, url, headers, body)

    async def _stream_response(
        self,
        http: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        on_token: Callable[[str], Coroutine[Any, Any, None] | None] | None,
    ) -> str:
        """Handle SSE streaming response, calling on_token per chunk."""
        async with http.stream("POST", url, json=body, headers=headers) as response:
            if response.status_code != 200:
                await self._raise_for_status(response)

            full_text: list[str] = []
            async for line in response.aiter_lines():
                line = line.strip()
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]  # strip "data: " prefix
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    full_text.append(content)
                    if on_token is not None:
                        result = on_token(content)
                        if asyncio.iscoroutine(result):
                            await result

            return "".join(full_text)

    async def _single_response(
        self,
        http: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> str:
        """Handle non-streaming response, return the full text."""
        body = {**body, "stream": False}
        response = await http.post(url, json=body, headers=headers)

        if response.status_code != 200:
            await self._raise_for_status(response)

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    async def _raise_for_status(self, response: httpx.Response) -> None:
        """Map HTTP status codes to typed exceptions with error body."""
        status = response.status_code
        error_body = ""
        try:
            await response.aread()
            error_data = response.json()
            error_body = error_data.get("error", {}).get("message", "") or str(error_data)
        except (json.JSONDecodeError, ValueError, httpx.ResponseNotRead):
            try:
                error_body = response.text[:500]
            except httpx.ResponseNotRead:
                error_body = f"HTTP {status}"

        if status == 401:
            raise AuthenticationError(
                f"Authentication failed for provider '{self._config.name}': {error_body}"
            )
        elif status == 429:
            raise RateLimitError(f"Rate limited by provider '{self._config.name}': {error_body}")
        elif status == 404:
            raise ModelNotFoundError(
                f"Model not found on provider '{self._config.name}': {error_body}"
            )
        elif status >= 500:
            raise ProviderError(
                f"Provider '{self._config.name}' returned {status}: {error_body}",
                status_code=status,
            )
        else:
            raise ProviderError(
                f"Provider '{self._config.name}' returned {status}: {error_body}",
                status_code=status,
            )
