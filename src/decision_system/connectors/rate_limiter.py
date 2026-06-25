"""Rate-limit handling for connector operations (v1.31).

Detects rate-limit responses (HTTP 429, GitHub rate-limit headers),
records rate-limit state, and provides Retry-After support.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """Current rate-limit state for a connector."""

    is_limited: bool = False
    retry_after_seconds: float = 0.0
    rate_limit_remaining: int | None = None
    rate_limit_reset: float | None = None  # Unix timestamp
    limited_at: float = 0.0  # Unix timestamp when rate limit was detected
    recovered_at: float | None = None


@dataclass
class RateLimitRecord:
    """A historical record of a rate-limit event."""

    connector_id: str
    retry_after_seconds: float
    rate_limit_remaining: int | None
    timestamp: float = field(default_factory=time.time)
    source_url: str = ""


class RateLimiter:
    """Tracks rate-limit state per connector.

    Not a full token-bucket — just detects, records, and surfaces
    rate-limit information so import jobs can pause/fail gracefully.
    """

    def __init__(self) -> None:
        self._states: dict[str, RateLimitState] = {}
        self._history: list[RateLimitRecord] = []
        self._max_history: int = 100

    def get_state(self, connector_id: str) -> RateLimitState:
        if connector_id not in self._states:
            self._states[connector_id] = RateLimitState()
        return self._states[connector_id]

    def record_429(
        self,
        connector_id: str,
        retry_after: float = 60.0,
        headers: dict[str, str] | None = None,
        source_url: str = "",
    ) -> RateLimitState:
        """Record an HTTP 429 rate-limit response."""
        state = self.get_state(connector_id)
        state.is_limited = True
        state.retry_after_seconds = retry_after
        state.limited_at = time.time()

        # Parse GitHub-style rate-limit headers
        if headers:
            remaining = headers.get("x-ratelimit-remaining")
            if remaining is not None:
                try:
                    state.rate_limit_remaining = int(remaining)
                except (ValueError, TypeError):
                    pass

            reset_val = headers.get("x-ratelimit-reset")
            if reset_val is not None:
                try:
                    state.rate_limit_reset = float(reset_val)
                except (ValueError, TypeError):
                    pass

            # Prefer Retry-After header
            retry_after_str = headers.get("retry-after")
            if retry_after_str is not None:
                try:
                    state.retry_after_seconds = float(retry_after_str)
                except (ValueError, TypeError):
                    pass

        # Record in history
        record = RateLimitRecord(
            connector_id=connector_id,
            retry_after_seconds=state.retry_after_seconds,
            rate_limit_remaining=state.rate_limit_remaining,
            source_url=source_url,
        )
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        logger.warning(
            "Rate-limited on %s: retry-after=%.1fs, remaining=%s",
            connector_id,
            state.retry_after_seconds,
            state.rate_limit_remaining,
        )

        return state

    def check_rate_limited(self, connector_id: str) -> bool:
        """Check if a connector is currently rate-limited.

        Returns True if the rate-limit window hasn't expired.
        """
        state = self.get_state(connector_id)
        if not state.is_limited:
            return False

        elapsed = time.time() - state.limited_at
        if elapsed >= state.retry_after_seconds:
            state.is_limited = False
            state.recovered_at = time.time()
            return False

        return True

    def record_success(self, connector_id: str, headers: dict[str, str] | None = None) -> None:
        """Record a successful API call (updates remaining count from headers)."""
        state = self.get_state(connector_id)
        if headers:
            remaining = headers.get("x-ratelimit-remaining")
            if remaining is not None:
                try:
                    state.rate_limit_remaining = int(remaining)
                except (ValueError, TypeError):
                    pass

        # Clear rate-limited flag if we got a successful response
        if state.is_limited:
            state.is_limited = False
            state.recovered_at = time.time()

    def get_history(self, limit: int = 10) -> list[RateLimitRecord]:
        return self._history[-limit:]

    def get_retry_after(self, connector_id: str) -> float:
        """Get remaining retry-after time in seconds (0 if not limited)."""
        if not self.check_rate_limited(connector_id):
            return 0.0
        state = self.get_state(connector_id)
        elapsed = time.time() - state.limited_at
        return max(0.0, state.retry_after_seconds - elapsed)

    def _reset(self) -> None:
        """Reset all state (for testing)."""
        self._states.clear()
        self._history.clear()


# Default singleton
_default_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = RateLimiter()
    return _default_limiter


def reset_rate_limiter() -> None:
    global _default_limiter
    _default_limiter = None
