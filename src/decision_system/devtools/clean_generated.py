"""Safe generated-file cleanup helper.

Provides a dry-run-by-default cleanup for generated local state, caches,
and compiled Python files.  Never deletes raw ``datasets/``, ``.env``,
``company_docs/``, or ``company_data/``.

Usage from Python::

    from decision_system.devtools.clean_generated import clean_generated
    clean_generated(force=False)

Usage from shell (via the bundled scripts or directly)::

    python -m decision_system.devtools.clean_generated
    python -m decision_system.devtools.clean_generated --force
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

# Patterns that are always safe to delete (generated/cached files)
_SAFE_PATTERNS: tuple[str, ...] = (
    "__pycache__",
    ".pytest_cache",
    ".decision_system",
)

# Directories that must NEVER be deleted
_PROTECTED_DIRS: tuple[str, ...] = (
    "datasets",
    ".env",
    "company_docs",
    "company_data",
)


@dataclass
class CleanResult:
    """Outcome of a cleanup run."""

    removed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return not self.errors


def _is_within(entry: Path, protected: Sequence[str]) -> bool:
    """Return True if *entry* is inside any of the *protected* directories."""
    for name in protected:
        parts = (name,)
        if name in entry.parts:
            return True
    return False


def clean_generated(
    root: Path | str | None = None,
    *,
    force: bool = False,
) -> CleanResult:
    """Remove generated/cache files from *root*.

    Parameters
    ----------
    root:
        Project root directory.  Defaults to the repository root.
    force:
        When *False* (default) the function is dry-run only and prints
        what *would* be deleted without removing anything.

    Returns
    -------
    CleanResult
        Lists of removed/skipped paths and any errors encountered.
    """
    root = Path(root) if root is not None else _default_root()
    result = CleanResult()

    for pattern in _SAFE_PATTERNS:
        if pattern == "__pycache__":
            for pycache in root.glob("**/__pycache__"):
                candidates = list(pycache.iterdir())
                _process_entry(pycache, candidates, force, result, root)
        elif pattern == ".pytest_cache":
            pytest_dir = root / ".pytest_cache"
            if pytest_dir.exists():
                candidates = list(pytest_dir.iterdir())
                _process_entry(pytest_dir, candidates, force, result, root)
        elif pattern == ".decision_system":
            ds_dir = root / ".decision_system"
            if ds_dir.exists():
                candidates = list(ds_dir.iterdir())
                _process_entry(ds_dir, candidates, force, result, root)

    return result


def _default_root() -> Path:
    """Resolve the project root from this file's location."""
    return Path(__file__).resolve().parents[3]


def _process_entry(
    entry: Path,
    children: list[Path],
    force: bool,
    result: CleanResult,
    root: Path,
) -> None:
    """Collect *entry* for removal (or dry-run) then resolve child safety explicitly."""
    rel = entry.relative_to(root)

    if _is_within(entry, _PROTECTED_DIRS):
        result.skipped.append(str(rel))
        return

    if force:
        try:
            shutil.rmtree(entry)
            result.removed.append(str(rel))
        except OSError as exc:
            result.errors.append(f"{rel}: {exc}")
        return

    # Dry-run: list every child directly; resolve protection deterministically.
    # We iterate into a plain list (no generator left open) so callers always
    # see all removed/skipped entries before the function returns.
    for child in list(children):
        child_rel = child.relative_to(root)
        if not _is_within(child, _PROTECTED_DIRS):
            result.removed.append(f"WOULD REMOVE: {child_rel}")
        else:
            result.skipped.append(f"SKIPPED (protected): {child_rel}")


def print_clean_summary(result: CleanResult, *, force: bool) -> None:
    """Print a human-readable summary of the cleanup result."""
    label = "Removed" if force else "Would remove"
    if result.removed:
        print(f"\n{label}:")
        for item in result.removed:
            print(f"  {item}")
    if result.skipped:
        print("\nSkipped:")
        for item in result.skipped:
            print(f"  {item}")
    if result.errors:
        print("\nErrors:")
        for item in result.errors:
            print(f"  [ERROR] {item}")
    print(
        f"\nDone. {label.lower()} {len(result.removed)}, "
        f"skipped {len(result.skipped)}, errors {len(result.errors)}."
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Clean generated local state (dry-run by default)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Actually delete files instead of a dry-run preview.",
    )
    args = parser.parse_args()

    result = clean_generated(force=args.force)
    print_clean_summary(result, force=args.force)
    if not result:
        raise SystemExit(1)
