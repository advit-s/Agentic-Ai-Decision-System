"""Provider experiment result persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from decision_system.provider_experiments.models import ProviderExperimentSuiteResult


_DEFAULT_DIR = Path(".decision_system") / "evals"


def save_experiment_results(
    suite: ProviderExperimentSuiteResult,
    results_dir: Path | str = _DEFAULT_DIR,
) -> Path:
    """Persist provider experiment results and return the output path."""
    output_dir = Path(results_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"provider_results_{suite.provider_name}_{timestamp}.json"
    payload = suite.model_dump(mode="json")
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path.resolve()


def load_latest_provider_results(
    provider_name: str,
    results_dir: Path | str = _DEFAULT_DIR,
) -> ProviderExperimentSuiteResult | None:
    """Load the most recent provider experiment results for a given provider."""
    output_dir = Path(results_dir)
    pattern = f"provider_results_{provider_name}_*.json"
    candidates = sorted(output_dir.glob(pattern), reverse=True)
    if not candidates:
        return None
    data = json.loads(candidates[0].read_text(encoding="utf-8"))
    return ProviderExperimentSuiteResult.model_validate(data)
