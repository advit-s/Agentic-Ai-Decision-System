"""Path validation and canonicalisation utilities for safe local file operations.

No auth or ACL system exists yet; these are simple safelist/denylist checks
that prevent obviously dangerous operations (writing to system paths,
traversing outside the project root) in a local-first prototype.

All public functions accept ``str | Path`` and return ``Path``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union


# ---------------------------------------------------------------------------
# Safe local paths
# ---------------------------------------------------------------------------

# Project directories that are safe for writes / imports
_SAFE_WRITE_PREFIXES: tuple[str, ...] = (
    ".decision_system",
    "company_docs",
    "company_data",
    "docs",
    "evals",
    "tests",
    "web",
)

# Paths that should NEVER be written to (checked relative to project_root)
# These are conceptually impossible to be a project root.
_DENIED_WRITE_PATHS: tuple[str, ...] = (
    "/etc",
    "/proc",
    "/sys",
    "/dev",
    "/bin",
    "/sbin",
    "/boot",
    "/lib",
    "/lib64",
    "/opt",
    "/root",
    "/run",
    "/srv",
)


def resolve_path(path: Union[str, Path]) -> Path:
    """Resolve *path* to an absolute, canonical :class:`Path`.

    Expands ``~``, resolves symlinks, and normalises the path.  All path
    operations in this module should go through this function.
    """
    return Path(path).expanduser().resolve()


def is_safe_write_path(path: Union[str, Path], project_root: Union[str, Path, None] = None) -> bool:
    """Return ``True`` when *path* is a safe local write destination.

    The check verifies that the resolved path is:

    * Possible to be inside a project root
    * Inside the project root or a recognised safe write prefix
    * Not a system directory (e.g. ``/etc``, ``/proc``)
    """
    resolved = resolve_path(path)
    root = resolve_path(project_root) if project_root else resolve_path(".")

    # Fast-fail: if path is an absolute system directory, reject immediately.
    for denied in _DENIED_WRITE_PATHS:
        denied_resolved = resolve_path(denied)
        if resolved == denied_resolved or denied_resolved in resolved.parents:
            return False

    # Check if path is inside the project root
    try:
        resolved.relative_to(root)
        return True
    except ValueError:
        pass

    # Outside project root — check if it's a recognised safe prefix
    for prefix in _SAFE_WRITE_PREFIXES:
        try:
            resolved.relative_to(resolve_path(prefix))
            return True
        except ValueError:
            continue

    return False


def ensure_safe_path(path: Union[str, Path], project_root: Union[str, Path, None] = None) -> Path:
    """Resolve *path* and raise ``ValueError`` if it is unsafe.

    Use this as a guard at the start of any function that writes files
    based on user-supplied paths.
    """
    resolved = resolve_path(path)
    if not is_safe_write_path(resolved, project_root=project_root):
        raise ValueError(
            f"Unsafe path: {resolved}. "
            f"Writes are restricted to the project root or "
            f"recognised safe directories."
        )
    return resolved


def ensure_safe_generated_write_path(
    path: Union[str, Path],
    project_root: Union[str, Path, None] = None,
) -> Path:
    """Resolve *path* and raise ``ValueError`` if it is outside ``.decision_system/``.

    Stricter than :func:`ensure_safe_path` — only paths under
    ``.decision_system/`` (within the project root) are accepted.  Use this
    for export / serialisation functions so that generated artefacts cannot
    accidentally overwrite tracked source files such as ``README.md`` or
    ``pyproject.toml``.
    """
    resolved = resolve_path(path)
    root = resolve_path(project_root) if project_root else resolve_path(".")

    # Fast-fail: system directories
    for denied in _DENIED_WRITE_PATHS:
        denied_resolved = resolve_path(denied)
        if resolved == denied_resolved or denied_resolved in resolved.parents:
            raise ValueError(f"Unsafe system path: {resolved}")

    # Must be under <project_root>/.decision_system/
    generated_root = resolve_path(root / ".decision_system")
    try:
        resolved.relative_to(generated_root)
    except ValueError as exc:
        raise ValueError(
            f"Unsafe path for generated writes: {resolved}. "
            f"Writes must stay under {generated_root}."
        ) from exc
    return resolved


def safe_relative_to(path: Union[str, Path], root: Union[str, Path]) -> Path:
    """Return *path* relative to *root* after resolution, or the path's name if outside *root*.

    This is equivalent to ``Path.relative_to`` but returns the filename
    instead of raising ``ValueError`` when *path* is outside *root*.
    """
    try:
        return resolve_path(path).relative_to(resolve_path(root))
    except ValueError:
        return Path(resolve_path(path).name)
