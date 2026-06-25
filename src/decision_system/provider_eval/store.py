"""Persistence for provider evaluation results."""

from __future__ import annotations

import json
from pathlib import Path

from decision_system._data_root import get_data_root
from decision_system.provider_eval.models import ProviderEvalSuiteResult


def _default_provider_eval_results_path() -> Path:
    return get_data_root() / "provider_evals" / "provider_eval_results.json"


def save_provider_eval_results(
    suite: ProviderEvalSuiteResult,
    output_path: Path | str | None = None,
) -> Path:
    """Persist provider evaluation results to the fixed local JSON path."""

    if output_path is None:
        output_path = _default_provider_eval_results_path()
    resolved = Path(output_path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    payload = suite.model_copy(update={"saved_result_path": str(resolved)})
    resolved.write_text(
        json.dumps(payload.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return resolved


def load_provider_eval_results(
    output_path: Path | str | None = None,
) -> ProviderEvalSuiteResult | None:
    """Load saved provider evaluation results if present."""

    if output_path is None:
        output_path = _default_provider_eval_results_path()
    path = Path(output_path)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ProviderEvalSuiteResult.model_validate(payload)
