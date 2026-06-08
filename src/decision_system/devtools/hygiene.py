"""v0.6.2 Repository hygiene checker.

Checks that generated artifacts, caches, private files, agent instructions,
and project configuration are in a safe state before new milestones.
"""

from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field


class HygieneCheckResult(BaseModel):
    """Result for a single hygiene check."""

    name: str
    status: str  # "passed" | "warning" | "failed"
    detail: str


class HygieneReport(BaseModel):
    """Structured result from the hygiene checker."""

    passed: list[HygieneCheckResult] = Field(default_factory=list)
    warnings: list[HygieneCheckResult] = Field(default_factory=list)
    failed: list[HygieneCheckResult] = Field(default_factory=list)
    overall: str = "PASS"  # "PASS" | "WARN" | "FAIL"

    @property
    def all_checks(self) -> list[HygieneCheckResult]:
        return self.passed + self.warnings + self.failed


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_GITIGNORE_RULES = [
    ".env",
    ".decision_system/",
    ".decision_system/connectors/",
    "__pycache__/",
    ".pytest_cache/",
    "datasets/",
    "*.pyc",
    ".venv/",
    "evals/results/*.json",
    ".decision_system/provider_evals/",
]


def check_hygiene(root: Path | str | None = None) -> HygieneReport:
    """Run all hygiene checks against the project root.

    Parameters
    ----------
    root : Path | str | None
        Project root directory. Defaults to the ``src/decision_system`` parent's
        parent (i.e., the repo root where this package lives).

    Returns
    -------
    HygieneReport
        Structured result with passed, warning, and failed checks.
    """
    root = Path(root) if root is not None else PROJECT_ROOT
    root = root.resolve()
    passed: list[HygieneCheckResult] = []
    warnings: list[HygieneCheckResult] = []
    failed: list[HygieneCheckResult] = []

    # --- .env ---
    env_path = root / ".env"
    if env_path.exists():
        try:
            _gitignore = (root / ".gitignore").read_text(encoding="utf-8")
            if ".env" in _gitignore:
                passed.append(
                    HygieneCheckResult(
                        name="env_ignored",
                        status="passed",
                        detail=".env exists and is in .gitignore.",
                    )
                )
            else:
                failed.append(
                    HygieneCheckResult(
                        name="env_ignored",
                        status="failed",
                        detail=".env exists but is NOT in .gitignore - risk of committing secrets.",
                    )
                )
        except FileNotFoundError:
            failed.append(
                HygieneCheckResult(
                    name="env_ignored",
                    status="failed",
                    detail=".env exists but .gitignore is missing.",
                )
            )
    else:
        passed.append(
            HygieneCheckResult(
                name="env_ignored",
                status="passed",
                detail=".env does not exist locally (OK for fresh clones).",
            )
        )

    # --- .decision_system/ ---
    ds_path = root / ".decision_system"
    if ds_path.exists():
        warnings.append(
            HygieneCheckResult(
                name="decision_system_generated",
                status="warning",
                detail=(
                    ".decision_system/ exists - this is generated local state "
                    "and must remain untracked."
                ),
            )
        )
        # Check it is actually ignored
        try:
            _gitignore = (root / ".gitignore").read_text(encoding="utf-8")
            if ".decision_system/" in _gitignore:
                passed.append(
                    HygieneCheckResult(
                        name="decision_system_ignored",
                        status="passed",
                        detail=".decision_system/ is in .gitignore.",
                    )
                )
            else:
                failed.append(
                    HygieneCheckResult(
                        name="decision_system_ignored",
                        status="failed",
                        detail=".decision_system/ exists but is not in .gitignore.",
                    )
                )
        except FileNotFoundError:
            failed.append(
                HygieneCheckResult(
                    name="decision_system_ignored",
                    status="failed",
                    detail=".decision_system/ exists but .gitignore is missing.",
                )
            )
    else:
        passed.append(
            HygieneCheckResult(
                name="decision_system_generated",
                status="passed",
                detail=".decision_system/ does not exist locally.",
            )
        )

    # --- __pycache__/ ---
    pycache_dirs = list(root.glob("**/__pycache__"))
    if pycache_dirs:
        warnings.append(
            HygieneCheckResult(
                name="pycache_present",
                status="warning",
                detail=f"Found {len(pycache_dirs)} __pycache__/ directories - safe to delete; verify ignored in .gitignore.",
            )
        )
    else:
        passed.append(
            HygieneCheckResult(
                name="pycache_present",
                status="passed",
                detail="No __pycache__/ directories found.",
            )
        )

    # --- .pytest_cache/ ---
    pytest_cache = root / ".pytest_cache"
    if pytest_cache.exists():
        warnings.append(
            HygieneCheckResult(
                name="pytest_cache_present",
                status="warning",
                detail=".pytest_cache/ exists - safe to delete; verify ignored in .gitignore.",
            )
        )
    else:
        passed.append(
            HygieneCheckResult(
                name="pytest_cache_present",
                status="passed",
                detail=".pytest_cache/ does not exist locally.",
            )
        )

    # --- datasets/ (raw public dataset imports) ---
    datasets_dir = root / "datasets"
    if datasets_dir.exists():
        warnings.append(
            HygieneCheckResult(
                name="datasets_present",
                status="warning",
                detail="datasets/ exists - raw public datasets must remain local and ignored by Git.",
            )
        )
        try:
            _gitignore = (root / ".gitignore").read_text(encoding="utf-8")
            if "datasets/" in _gitignore:
                passed.append(
                    HygieneCheckResult(
                        name="datasets_ignored",
                        status="passed",
                        detail="datasets/ is in .gitignore.",
                    )
                )
            else:
                failed.append(
                    HygieneCheckResult(
                        name="datasets_ignored",
                        status="failed",
                        detail="datasets/ exists but is not in .gitignore.",
                    )
                )
        except FileNotFoundError:
            failed.append(
                HygieneCheckResult(
                    name="datasets_ignored",
                    status="failed",
                    detail="datasets/ exists but .gitignore is missing.",
                )
            )
    else:
        passed.append(
            HygieneCheckResult(
                name="datasets_present",
                status="passed",
                detail="datasets/ does not exist locally.",
            )
        )

    # --- AGENTS.md ---
    agents_path = root / "AGENTS.md"
    if agents_path.exists():
        passed.append(
            HygieneCheckResult(
                name="agents_md",
                status="passed",
                detail="AGENTS.md exists at the repository root.",
            )
        )
    else:
        failed.append(
            HygieneCheckResult(
                name="agents_md",
                status="failed",
                detail="AGENTS.md is missing at the repository root.",
            )
        )

    # --- CLAUDE.md ---
    claude_path = root / "CLAUDE.md"
    if claude_path.exists():
        passed.append(
            HygieneCheckResult(
                name="claude_md",
                status="passed",
                detail="CLAUDE.md exists at the repository root.",
            )
        )
    else:
        warnings.append(
            HygieneCheckResult(
                name="claude_md",
                status="warning",
                detail="CLAUDE.md is missing at the repository root.",
            )
        )

    # --- .gitignore ---
    gitignore_path = root / ".gitignore"
    if gitignore_path.exists():
        gitignore_text = gitignore_path.read_text(encoding="utf-8")
        missing_rules = [r for r in REQUIRED_GITIGNORE_RULES if r not in gitignore_text]
        if missing_rules:
            warnings.append(
                HygieneCheckResult(
                    name="gitignore_rules",
                    status="warning",
                    detail=f"Missing .gitignore rules: {', '.join(missing_rules)}.",
                )
            )
        else:
            passed.append(
                HygieneCheckResult(
                    name="gitignore_rules",
                    status="passed",
                    detail=".gitignore contains expected rules for generated files.",
                )
            )
    else:
        failed.append(
            HygieneCheckResult(
                name="gitignore_present",
                status="failed",
                detail=".gitignore is missing at the repository root.",
            )
        )

    # --- .env.example fake provider default ---
    env_example_path = root / ".env.example"
    if env_example_path.exists():
        env_example_text = env_example_path.read_text(encoding="utf-8")
        if "DECISION_PROVIDER=fake" in env_example_text:
            passed.append(
                HygieneCheckResult(
                    name="env_example_fake_default",
                    status="passed",
                    detail=".env.example sets DECISION_PROVIDER=fake.",
                )
            )
        else:
            failed.append(
                HygieneCheckResult(
                    name="env_example_fake_default",
                    status="failed",
                    detail=".env.example does not set DECISION_PROVIDER=fake.",
                )
            )
    else:
        warnings.append(
            HygieneCheckResult(
                name="env_example_present",
                status="warning",
                detail=".env.example is missing.",
            )
        )

    # --- pyproject.toml script entrypoint ---
    pyproject_path = root / "pyproject.toml"
    if pyproject_path.exists():
        pyproject_text = pyproject_path.read_text(encoding="utf-8")
        if "decision-system" in pyproject_text and "decision_system.cli:app" in pyproject_text:
            passed.append(
                HygieneCheckResult(
                    name="pyproject_entrypoint",
                    status="passed",
                    detail="pyproject.toml has the decision-system entry point.",
                )
            )
        else:
            warnings.append(
                HygieneCheckResult(
                    name="pyproject_entrypoint",
                    status="warning",
                    detail="pyproject.toml is missing the decision-system script entry point.",
                )
            )
    else:
        failed.append(
            HygieneCheckResult(
                name="pyproject_present",
                status="failed",
                detail="pyproject.toml is missing.",
            )
        )

    # --- Generated imported CSVs ---
    imported_csvs = list(root.glob("company_data/**/imported_*.csv"))
    if imported_csvs:
        warnings.append(
            HygieneCheckResult(
                name="imported_csvs",
                status="warning",
                detail=(
                    f"Found {len(imported_csvs)} imported_*.csv files under "
                    "company_data/ - these are generated and must remain ignored."
                ),
            )
        )
    else:
        passed.append(
            HygieneCheckResult(
                name="imported_csvs",
                status="passed",
                detail="No imported_*.csv files found under company_data/.",
            )
        )

    # Build overall status
    if failed:
        overall = "FAIL"
    elif warnings:
        overall = "WARN"
    else:
        overall = "PASS"

    return HygieneReport(
        passed=passed,
        warnings=warnings,
        failed=failed,
        overall=overall,
    )
