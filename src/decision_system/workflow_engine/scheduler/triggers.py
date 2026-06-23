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


def _parse_cron_field(field: str, min_val: int = 0, max_val: int = 59) -> set[int]:
    """Parse a single cron field into a set of matching values.

    Supported patterns:
        ``*`` — wildcard (any value within range)
        ``N`` — exact numeric match (e.g. ``9``)
        ``*/N`` — step expression (e.g. ``*/15`` matches 0, 15, 30, 45)
        ``N-M`` — range (e.g. ``1-5`` matches 1, 2, 3, 4, 5)
        ``N,M,O`` — list (e.g. ``1,3,5`` matches 1, 3, 5)
    """
    field = field.strip()

    # Wildcard
    if field == "*":
        return set(range(min_val, max_val + 1))

    # Step expression: */N
    if field.startswith("*/"):
        step_str = field[2:]
        if step_str.isdigit():
            step = int(step_str)
            if step > 0:
                return set(range(min_val, max_val + 1, step))
        raise ValueError(f"Invalid step expression: {field!r}")

    # Range: N-M
    if "-" in field and "," not in field:
        parts = field.split("-", 1)
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            low, high = int(parts[0]), int(parts[1])
            if low <= high:
                return set(range(low, high + 1))
            raise ValueError(f"Invalid range: {field!r}")
        raise ValueError(f"Invalid range expression: {field!r}")

    # Comma-separated list: N,M,O
    if "," in field:
        values: set[int] = set()
        for item in field.split(","):
            item = item.strip()
            if item.isdigit():
                values.add(int(item))
            elif "-" in item:
                range_parts = item.split("-", 1)
                if len(range_parts) == 2 and range_parts[0].isdigit() and range_parts[1].isdigit():
                    low, high = int(range_parts[0]), int(range_parts[1])
                    values.update(range(low, high + 1))
                else:
                    raise ValueError(f"Invalid range in list: {item!r}")
            else:
                raise ValueError(f"Invalid field item: {item!r}")
        return values

    # Single digit
    if field.isdigit():
        return {int(field)}

    raise ValueError(f"Unsupported cron field: {field!r}")


def _parse_cron(expression: str) -> tuple:
    """Parse a 5-field cron expression into a tuple of field value sets.

    Returns a 5-tuple ``(minute, hour, day_of_month, month, day_of_week)``.
    Each element is a set of integers matching the expression.

    Raises ``ValueError`` for invalid expressions.

    Supported patterns:
        ``*`` — wildcard (any value)
        ``N`` — exact numeric match (e.g. ``9`` matches 9am)
        ``*/N`` — step expression (e.g. ``*/30`` matches every 30 minutes)
        ``N-M`` — range (e.g. ``1-5`` matches Mon-Fri)
        ``N,M,O`` — list (e.g. ``1,3,5`` matches 1, 3, 5)
    """
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression: {expression!r}. "
            f"Expected 5 fields (minute hour dom month dow).",
        )

    # Field ranges: minute(0-59), hour(0-23), day-of-month(1-31), month(1-12), day-of-week(0-6)
    ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
    parsed: list[set[int]] = []
    for i, part in enumerate(parts):
        min_v, max_v = ranges[i]
        parsed.append(_parse_cron_field(part, min_v, max_v))

    return tuple(parsed)  # type: ignore
def _cron_matches(expression: str, dt: datetime) -> bool:
    """Check whether *dt* matches a cron expression."""
    try:
        minute, hour, dom, month, dow = _parse_cron(expression)
    except ValueError:
        return False

    if -1 not in minute and dt.minute not in minute:
        return False
    if -1 not in hour and dt.hour not in hour:
        return False
    if -1 not in dom and dt.day not in dom:
        return False
    if -1 not in month and dt.month not in month:
        return False
    if -1 not in dow and dt.weekday() not in dow:  # Monday = 0
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
