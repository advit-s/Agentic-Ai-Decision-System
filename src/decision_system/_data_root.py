"""Single shared helper for the local data root directory.

All persistent state should live under this root.  Honors
``DECISION_SYSTEM_DATA_DIR`` when set, otherwise defaults to
``.decision_system/`` in the current working directory.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_data_root() -> Path:
    """Return the configured data root directory.

    Use this instead of hardcoding ``Path(".decision_system")`` so the
    product is relocatable (one env var changes everything).
    """
    raw = os.environ.get("DECISION_SYSTEM_DATA_DIR", "")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.cwd() / ".decision_system"
