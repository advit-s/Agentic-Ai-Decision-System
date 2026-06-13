"""Exception hierarchy for LLM provider errors."""

from __future__ import annotations


class ProviderError(Exception):
    """Base exception for all LLM provider errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(ProviderError):
    """API key is invalid or missing."""

    def __init__(self, message: str = "Authentication failed. Check your API key.") -> None:
        super().__init__(message, status_code=401)


class RateLimitError(ProviderError):
    """Rate limited by the provider."""

    def __init__(self, message: str = "Rate limit exceeded. Please retry later.") -> None:
        super().__init__(message, status_code=429)


class ModelNotFoundError(ProviderError):
    """The requested model does not exist on this provider."""

    def __init__(self, message: str = "Model not found on provider.") -> None:
        super().__init__(message, status_code=404)


class TimeoutError(ProviderError):
    """The provider request timed out."""

    def __init__(self, message: str = "Provider request timed out after 30 seconds.") -> None:
        super().__init__(message, status_code=504)
