"""Retry and backoff policy for connector operations (v1.31).

Classifies errors as retryable or non-retryable, applies bounded
exponential backoff, and records retry attempts.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RetryableError(StrEnum):
    """Error types that are safe to retry."""

    NETWORK_TIMEOUT = "network_timeout"
    HTTP_429 = "http_429"
    HTTP_500 = "http_500"
    HTTP_502 = "http_502"
    HTTP_503 = "http_503"
    HTTP_504 = "http_504"
    TEMPORARY_FS_READ = "temporary_fs_read"
    CONNECTION_RESET = "connection_reset"
    DNS_FAILURE = "dns_failure"


class NonRetryableError(StrEnum):
    """Error types that must fail fast."""

    HTTP_401 = "http_401"
    HTTP_403 = "http_403"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
    BLOCKED_PRIVATE_URL = "blocked_private_url"
    PATH_TRAVERSAL = "path_traversal"
    FILE_TOO_LARGE = "file_too_large"
    MALFORMED_CONFIG = "malformed_config"
    AUTH_FAILURE = "auth_failure"


RETRYABLE_KEYWORDS: list[str] = [
    "timeout",
    "timed out",
    "connection reset",
    "connection refused",
    "connection aborted",
    "name resolution",
    "temporarily unavailable",
    "rate limit",
    "429",
    "500",
    "502",
    "503",
    "504",
    "service unavailable",
    "too many requests",
    "retry later",
    "network is unreachable",
    "reset by peer",
]

NON_RETRYABLE_KEYWORDS: list[str] = [
    "401",
    "403",
    "unauthorized",
    "forbidden",
    "not found",
    "unsupported file",
    "path traversal",
    "blocked",
    "file too large",
    "malformed config",
    "invalid config",
    "permission denied",
    "access denied",
]


@dataclass
class RetryAttempt:
    """Record of a single retry attempt."""

    attempt_number: int
    error: str
    delay_seconds: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class RetryPolicy:
    """Bounded retry policy with exponential backoff and jitter.

    Default: max 3 retries, exponential backoff (1s, 2s, 4s) + jitter.
    """

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    backoff_factor: float = 2.0
    jitter_factor: float = 0.1

    def should_retry(self, error: str | Exception, attempt_number: int) -> bool:
        """Determine if an error should be retried."""
        if attempt_number > self.max_retries:
            return False
        error_str = str(error)
        return self.classify_error(error_str) == "retryable"

    def classify_error(self, error_str: str) -> str:
        """Classify an error as retryable or non-retryable."""
        error_lower = error_str.lower()

        # Check non-retryable first (they take precedence)
        for keyword in NON_RETRYABLE_KEYWORDS:
            if keyword in error_lower:
                return "non_retryable"

        # Check retryable
        for keyword in RETRYABLE_KEYWORDS:
            if keyword in error_lower:
                return "retryable"

        # Default to non-retryable for unknown errors
        return "non_retryable"

    def get_delay(self, attempt_number: int) -> float:
        """Calculate delay for a given attempt number (1-based)."""
        delay = min(
            self.base_delay_seconds * (self.backoff_factor ** (attempt_number - 1)),
            self.max_delay_seconds,
        )
        # Add jitter: ±10%
        jitter = delay * self.jitter_factor * (2 * random.random() - 1)
        return max(0.1, min(delay + jitter, self.max_delay_seconds))

    def execute_with_retry(
        self,
        fn: Callable[..., Any],
        *args: Any,
        on_retry: Callable[[RetryAttempt], None] | None = None,
        **kwargs: Any,
    ) -> tuple[Any, list[RetryAttempt]]:
        """Execute a function with retry logic.

        Returns (result, retry_attempts) on success.
        Raises the last exception on failure.
        """
        attempts: list[RetryAttempt] = []
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 2):  # +1 for initial attempt
            try:
                result = fn(*args, **kwargs)
                if attempts and on_retry:
                    for retry_attempt in attempts:
                        on_retry(retry_attempt)
                return result, attempts
            except Exception as e:
                last_error = e
                error_str = str(e)

                if not self.should_retry(error_str, attempt):
                    raise

                delay = self.get_delay(attempt)
                retry_attempt = RetryAttempt(
                    attempt_number=attempt,
                    error=error_str,
                    delay_seconds=delay,
                )
                attempts.append(retry_attempt)

                logger.info(
                    "Retry attempt %d/%d after %.1fs: %s",
                    attempt,
                    self.max_retries,
                    delay,
                    error_str,
                )

                if attempt <= self.max_retries:
                    time.sleep(delay)

        # If we exhausted retries, raise the last error
        if last_error:
            raise last_error

        return None, attempts


# Default policy instance
_default_policy: RetryPolicy | None = None


def get_retry_policy() -> RetryPolicy:
    global _default_policy
    if _default_policy is None:
        _default_policy = RetryPolicy()
    return _default_policy


def reset_retry_policy() -> None:
    global _default_policy
    _default_policy = None
