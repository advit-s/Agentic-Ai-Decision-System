"""Trigger evaluators for cron, webhook, and file-watch triggers.

Each function in this module evaluates whether a trigger condition
is met at the current time. The scheduler calls these to decide
whether to fire a workflow.
"""

from __future__ import annotations

import fnmatch
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ─── Cron Evaluator ──────────────────────────────────────────────────────────


def _parse_cron(expression: str) -> tuple:
    """Parse a 5-field cron expression into a tuple of field values.

    Returns a 5-tuple ``(minute, hour, day_of_month, month, day_of_week)``.
    A value of ``-1`` means wildcard (``*``).

    Raises ``ValueError`` for invalid expressions.

    Supported patterns:
        ``*`` — wildcard (any value)
        ``N`` — exact numeric match (e.g. ``9`` matches 9am)
    """
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression: {expression!r}. "
            f"Expected 5 fields (minute hour dom month dow).",
        )
    parsed: list[int] = []
    for part in parts:
        if part == "*":
            parsed.append(-1)  # wildcard
        elif part.isdigit():
            parsed.append(int(part))
        else:
            raise ValueError(
                f"Unsupported cron field: {part!r}. "
                f"Only '*' and digits are supported.",
            )
    # (minute, hour, day_of_month, month, day_of_week)
    return tuple(parsed)  # type: ignore


def _cron_matches(expression: str, dt: datetime) -> bool:
    """Check whether *dt* matches a cron expression."""
    try:
        minute, hour, dom, month, dow = _parse_cron(expression)
    except ValueError:
        return False

    if minute != -1 and dt.minute != minute:
        return False
    if hour != -1 and dt.hour != hour:
        return False
    if dom != -1 and dt.day != dom:
        return False
    if month != -1 and dt.month != month:
        return False
    if dow != -1 and dt.weekday() != dow:  # Monday = 0
        return False
    return True


def evaluate_cron(
    expression: str,
    last_fired: Optional[datetime] = None,
) -> bool:
    """Evaluate whether a cron trigger should fire **now**.

    Returns ``True`` when the current time matches *expression* **and**
    the trigger has not already fired within the current minute window.

    Parameters
    ----------
    expression:
        A 5-field cron expression (``"0 9 * * 1-5"`` for weekdays at 9am).
    last_fired:
        The last time this trigger fired. Pass ``None`` for first evaluation.
    """
    now = datetime.now(timezone.utc)
    if not _cron_matches(expression, now):
        return False
    if last_fired is not None:
        # Don't fire again within the same 60-second window
        if (now - last_fired).total_seconds() < 60:
            return False
    return True


# ─── Webhook Evaluator ───────────────────────────────────────────────────────


def validate_webhook_path(received_path: str, stored_path: str) -> bool:
    """Validate an incoming webhook request path against a stored configuration.

    Trailing slashes are ignored during comparison.

    Returns ``True`` if the paths match.
    """
    return received_path.rstrip("/") == stored_path.rstrip("/")


# ─── File Watch Evaluator ────────────────────────────────────────────────────


def scan_directory(
    directory: str,
    pattern: str = "*",
    known_files: Optional[set[str]] = None,
) -> tuple[set[str], list[str]]:
    """Scan a directory for files matching *pattern*.

    When *known_files* is provided, returns only newly detected files
    (those not present in the previous snapshot).

    Parameters
    ----------
    directory:
        Path to the directory to scan.
    pattern:
        Glob-style file pattern (e.g. ``*.md``, ``*.csv``).
    known_files:
        Set of filenames from the previous scan. Pass ``None`` for
        an initial scan (all matching files are returned in the set,
        none reported as new).

    Returns
    -------
    tuple[set[str], list[str]]
        A ``(current_files, new_files)`` pair. ``current_files`` is the
        complete set of matching files. ``new_files`` lists files that
        appeared since the last scan.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return set(), []

    current: set[str] = set()
    for entry in dir_path.iterdir():
        if entry.is_file() and fnmatch.fnmatch(entry.name, pattern):
            current.add(entry.name)

    if known_files is None:
        return current, []

    new_files = [f for f in current if f not in known_files]
    return current, new_files
