"""Tests for LLMClient — unified OpenAI-compatible HTTP caller."""

from __future__ import annotations

import json
import os

import pytest
from pytest_httpx import HTTPXMock

from decision_system.workflow_engine.providers.client import LLMClient
from decision_system.workflow_engine.providers.exceptions import (
    AuthenticationError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)
from decision_system.workflow_engine.providers.store import ProviderConfig

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────

def _sse_stream(*chunks: str) -> str:
    """Build SSE response body from content strings."""
    lines = [
        'data: {"id":"1","object":"chat.completion.chunk",'
        '"choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}'
    ]
    for c in chunks:
        safe = json.dumps(c)
        lines.append(
            'data: {"id":"1","object":"chat.completion.chunk",'
            f'"choices":[{{"index":0,"delta":{{"content":{safe}}},"finish_reason":null}}]}}'
        )
    lines.append(
        'data: {"id":"1","object":"chat.completion.chunk",'
        '"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}'
    )
    lines.append("data: [DONE]")
    return "\n".join(lines)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def openai_config() -> ProviderConfig:
    return ProviderConfig(
        name="test-openai",
        api_base="https://api.openai.com/v1",
        api_key_env="TEST_OPENAI_KEY",
        default_model="gpt-4o",
    )


@pytest.fixture
def local_config() -> ProviderConfig:
    return ProviderConfig(
        name="test-local",
        api_base="http://localhost:11434/v1",
        api_key_env=None,
        default_model="llama3",
    )


SIMPLE_RESPONSE = {
    "id": "chatcmpl-1",
    "object": "chat.completion",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "Hello, world!"}, "finish_reason": "stop"}
    ],
}


# ── Basic Request Tests ───────────────────────────────────────────────

class TestLLMClientBasic:
    """Core request/response handling."""

    async def test_chat_completion_basic(self, httpx_mock: HTTPXMock, openai_config: ProviderConfig):
        """Sends correct request body, returns response."""
        os.environ["TEST_OPENAI_KEY"] = "sk-test123"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                json=SIMPLE_RESPONSE,
            )
            client = LLMClient(openai_config)
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Say hello"}],
                model="gpt-4o",
                stream=False,
            )
            assert result == "Hello, world!"
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)

    async def test_chat_completion_sends_correct_request(
        self, httpx_mock: HTTPXMock, openai_config: ProviderConfig
    ):
        """Verify the exact request sent to the API."""
        os.environ["TEST_OPENAI_KEY"] = "sk-test123"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                json=SIMPLE_RESPONSE,
            )
            client = LLMClient(openai_config)
            await client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hi"},
                ],
                model="gpt-4o-mini",
                stream=False,
            )
            request = httpx_mock.get_request()
            assert request is not None
            body = json.loads(request.content)
            assert body["model"] == "gpt-4o-mini"
            assert len(body["messages"]) == 2
            assert body["messages"][0]["role"] == "system"
            assert body["messages"][1]["role"] == "user"
            assert body["stream"] is False
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)

    async def test_sends_auth_header(self, httpx_mock: HTTPXMock, openai_config: ProviderConfig):
        """Authorization header is set from env var."""
        os.environ["TEST_OPENAI_KEY"] = "sk-secret-456"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                json=SIMPLE_RESPONSE,
            )
            client = LLMClient(openai_config)
            await client.chat_completion(messages=[{"role": "user", "content": "hi"}], stream=False)
            request = httpx_mock.get_request()
            assert request is not None
            assert request.headers["Authorization"] == "Bearer sk-secret-456"
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)

    async def test_no_auth_header_for_local_providers(
        self, httpx_mock: HTTPXMock, local_config: ProviderConfig
    ):
        """Local providers send no Authorization header."""
        httpx_mock.add_response(
            url="http://localhost:11434/v1/chat/completions",
            method="POST",
            json=SIMPLE_RESPONSE,
        )
        client = LLMClient(local_config)
        await client.chat_completion(messages=[{"role": "user", "content": "hi"}], stream=False)
        request = httpx_mock.get_request()
        assert request is not None
        assert "Authorization" not in request.headers

    async def test_uses_default_model_when_not_specified(
        self, httpx_mock: HTTPXMock, openai_config: ProviderConfig
    ):
        """When model is None, uses the provider's default_model."""
        os.environ["TEST_OPENAI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                json=SIMPLE_RESPONSE,
            )
            client = LLMClient(openai_config)
            await client.chat_completion(messages=[{"role": "user", "content": "hi"}], stream=False)
            request = httpx_mock.get_request()
            assert request is not None
            body = json.loads(request.content)
            assert body["model"] == "gpt-4o"
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)

    async def test_trailing_slash_stripped(self, httpx_mock: HTTPXMock):
        """api_base with trailing / is normalized."""
        os.environ["TEST_KEY_TRAILING"] = "sk-key"
        try:
            cfg = ProviderConfig(
                name="trailing",
                api_base="https://api.example.com/v1/",
                api_key_env="TEST_KEY_TRAILING",
                default_model="m1",
            )
            httpx_mock.add_response(
                url="https://api.example.com/v1/chat/completions",
                method="POST",
                json=SIMPLE_RESPONSE,
            )
            client = LLMClient(cfg)
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "hi"}], stream=False
            )
            assert result == "Hello, world!"
        finally:
            os.environ.pop("TEST_KEY_TRAILING", None)

    async def test_content_type_header(self, httpx_mock: HTTPXMock, openai_config: ProviderConfig):
        """Content-Type is application/json."""
        os.environ["TEST_OPENAI_KEY"] = "sk-key"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                json=SIMPLE_RESPONSE,
            )
            client = LLMClient(openai_config)
            await client.chat_completion(
                messages=[{"role": "user", "content": "hi"}], stream=False
            )
            request = httpx_mock.get_request()
            assert request is not None
            assert request.headers["Content-Type"] == "application/json"
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)


# ── Streaming Tests ───────────────────────────────────────────────────

class TestLLMClientStreaming:
    """Streaming response handling."""

    async def test_streaming_calls_on_token(self, httpx_mock: HTTPXMock, openai_config: ProviderConfig):
        """on_token callback is called for each content chunk."""
        os.environ["TEST_OPENAI_KEY"] = "sk-stream"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                content=_sse_stream("Hello", " world").encode(),
                headers={"Content-Type": "text/event-stream"},
            )
            tokens: list[str] = []
            client = LLMClient(openai_config)
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                stream=True,
                on_token=lambda t: tokens.append(t),
            )
            assert tokens == ["Hello", " world"]
            assert result == "Hello world"
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)

    async def test_streaming_without_on_token(self, httpx_mock: HTTPXMock, openai_config: ProviderConfig):
        """stream=True without on_token still returns full text."""
        os.environ["TEST_OPENAI_KEY"] = "sk-stream2"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                content=_sse_stream("Only", " text").encode(),
                headers={"Content-Type": "text/event-stream"},
            )
            client = LLMClient(openai_config)
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                stream=True,
            )
            assert result == "Only text"
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)

    async def test_streaming_empty_content_chunks(
        self, httpx_mock: HTTPXMock, openai_config: ProviderConfig
    ):
        """Empty content delta is ignored."""
        os.environ["TEST_OPENAI_KEY"] = "sk-empty"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                content=_sse_stream("").encode(),
                headers={"Content-Type": "text/event-stream"},
            )
            client = LLMClient(openai_config)
            tokens: list[str] = []
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                stream=True,
                on_token=lambda t: tokens.append(t),
            )
            assert tokens == []
            assert result == ""
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)


# ── Error Tests ───────────────────────────────────────────────────────

class TestLLMClientErrors:
    """Error handling and mapping."""

    async def test_authentication_error(self, httpx_mock: HTTPXMock, openai_config: ProviderConfig):
        """401 maps to AuthenticationError."""
        os.environ["TEST_OPENAI_KEY"] = "sk-bad"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                status_code=401,
                json={"error": {"message": "Incorrect API key", "type": "authentication_error"}},
            )
            client = LLMClient(openai_config)
            with pytest.raises(AuthenticationError) as exc:
                await client.chat_completion(messages=[{"role": "user", "content": "hi"}])
            assert "Incorrect API key" in str(exc.value)
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)

    async def test_rate_limit_error(self, httpx_mock: HTTPXMock, openai_config: ProviderConfig):
        """429 maps to RateLimitError."""
        os.environ["TEST_OPENAI_KEY"] = "sk-ratelimit"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                status_code=429,
                json={"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}},
            )
            client = LLMClient(openai_config)
            with pytest.raises(RateLimitError) as exc:
                await client.chat_completion(messages=[{"role": "user", "content": "hi"}])
            assert "Rate limit exceeded" in str(exc.value)
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)

    async def test_model_not_found(self, httpx_mock: HTTPXMock, openai_config: ProviderConfig):
        """404 maps to ModelNotFoundError."""
        os.environ["TEST_OPENAI_KEY"] = "sk-model404"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                status_code=404,
                json={"error": {"message": "The model `gpt-4o` does not exist", "type": "invalid_request_error"}},
            )
            client = LLMClient(openai_config)
            with pytest.raises(ModelNotFoundError) as exc:
                await client.chat_completion(messages=[{"role": "user", "content": "hi"}])
            assert "model" in str(exc.value).lower()
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)

    async def test_server_error(self, httpx_mock: HTTPXMock, openai_config: ProviderConfig):
        """500 maps to ProviderError."""
        os.environ["TEST_OPENAI_KEY"] = "sk-500"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                status_code=500,
                json={"error": {"message": "Internal server error", "type": "server_error"}},
            )
            client = LLMClient(openai_config)
            with pytest.raises(ProviderError) as exc:
                await client.chat_completion(messages=[{"role": "user", "content": "hi"}])
            assert "Internal server error" in str(exc.value)
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)

    async def test_no_api_key_raises_error(self, openai_config: ProviderConfig):
        """Missing API key env var raises AuthenticationError."""
        os.environ.pop("TEST_OPENAI_KEY", None)
        client = LLMClient(openai_config)
        with pytest.raises(AuthenticationError) as exc:
            await client.chat_completion(messages=[{"role": "user", "content": "hi"}])
        assert "API key" in str(exc.value)

    async def test_without_on_token_still_returns_full_text(
        self, httpx_mock: HTTPXMock, openai_config: ProviderConfig
    ):
        """Non-streaming path returns full text."""
        os.environ["TEST_OPENAI_KEY"] = "sk-nostream"
        try:
            httpx_mock.add_response(
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                json=SIMPLE_RESPONSE,
            )
            client = LLMClient(openai_config)
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                stream=False,
            )
            assert result == "Hello, world!"
        finally:
            os.environ.pop("TEST_OPENAI_KEY", None)
