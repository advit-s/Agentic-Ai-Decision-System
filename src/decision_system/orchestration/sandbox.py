"""Offline sandbox wrapper for v0.4 orchestration.

Executes a small, explicit allow-list of deterministic local actions.
This is NOT real security sandboxing — it is an explicit function-call
allow-list with a clear limitation documented in the models.

Allowed actions
---------------
* read_profiles        — read .decision_system/data_profiles/profiles.json
* read_ontology        — read .decision_system/ontology/ontology_map.json
* read_graph           — read .decision_system/graph/knowledge_graph.json
* read_insights        — read .decision_system/insights/insights.json
* read_csv             — read a CSV under company_data/ through the data catalog loader
* run_detectors        — run the deterministic insight detectors
* save_ontology        — write an OntologyMap
* save_insights        — write an InsightStore
* save_run             — write an orchestration run JSON

Forbidden actions (rejected with ValueError)
--------------------------------------------
* delete / rm / remove
* shell / exec / subprocess
* http / api / request
* send / email / slack / jira
* any string not listed above
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Action registry
# ---------------------------------------------------------------------------

_ALLOWED_ACTIONS: dict[str, str] = {
    # read-only
    "read_profiles": "read",
    "read_ontology": "read",
    "read_graph": "read",
    "read_insights": "read",
    "read_csv": "read",
    # execute
    "run_detectors": "execute",
    # write
    "save_ontology": "write",
    "save_insights": "write",
    "save_run": "write",
}

_FORBIDDEN_PATTERNS = [
    "delete",
    "remove",
    "rm ",
    "rm\t",
    "shell",
    "exec",
    "subprocess",
    "http://",
    "https://",
    "api.",
    "request",
    "send ",
    "email",
    "slack",
    "jira",
    "salesforce",
    "github.com",
    "curl ",
    "wget ",
    "nc ",
    "netcat",
]


def _check_forbidden(action: str) -> None:
    low = action.lower()
    for pattern in _FORBIDDEN_PATTERNS:
        if pattern in low:
            raise ValueError(
                f"Sandbox rejected action '{action}': forbidden pattern '{pattern}'"
            )


def sandbox_execute(
    action: str,
    context: dict[str, Any],
) -> Any:
    """Execute *action* against sandboxed *context*.

    Parameters
    ----------
    action:
        One of the allowed action names (see docstring).
    context:
        Pre-loaded objects available to sandboxed actions:
        ``profiles``, ``ontology_map``, ``knowledge_graph``, ``insights``,
        ``csv_root``, etc.

    Returns
    -------
    Any
        Result of the action (a model instance, a value, or None for
        side-effect actions).

    Raises
    ------
    ValueError
        If *action* is not in the allow-list or matches a forbidden
        pattern.
    """
    _check_forbidden(action)

    if action not in _ALLOWED_ACTIONS:
        raise ValueError(
            f"Sandbox rejected unknown action '{action}'. "
            f"Allowed: {sorted(_ALLOWED_ACTIONS)}"
        )

    kind = _ALLOWED_ACTIONS[action]

    # We delegate to the appropriate function imported lazily to avoid
    # circular imports at module level.
    if action == "read_profiles":
        from decision_system.data_catalog.store import load_profiles

        return load_profiles()

    if action == "read_ontology":
        from decision_system.ontology.store import load_ontology

        return load_ontology()

    if action == "read_graph":
        from decision_system.graphing.store import load_knowledge_graph

        return load_knowledge_graph()

    if action == "read_insights":
        from decision_system.insights.store import load_insights

        return load_insights()

    if action == "read_csv":
        # context must contain 'profile' and 'csv_root'
        from decision_system.data_catalog.loader import load_csv
        from decision_system.data_catalog.models import DataProfileStore

        profile = context["profile"]
        csv_root = context.get("csv_root", "company_data")
        path = _csv_path_for_profile(profile, csv_root)
        if path is None or not path.exists():
            return None
        return load_csv(path, profile.category)

    if action == "run_detectors":
        from decision_system.insights.detectors import run_detectors

        profiles = context.get("profiles")
        graph = context.get("knowledge_graph")
        csv_root = context.get("csv_root", "company_data")
        return run_detectors(profiles=profiles, graph=graph, csv_root=csv_root)

    if action == "save_ontology":
        from decision_system.ontology.store import save_ontology

        omap = context["ontology_map"]
        store_dir = context.get("ontology_store_dir")
        if store_dir is None:
            return save_ontology(omap)
        return save_ontology(omap, store_dir)

    if action == "save_insights":
        from decision_system.insights.store import save_insights

        insights = context["insights"]
        store_dir = context.get("insights_store_dir")
        if store_dir is None:
            return save_insights(insights)
        return save_insights(insights, store_dir)

    if action == "save_run":
        return context  # caller handles persistence

    # Should be unreachable
    raise ValueError(f"Sandbox action '{action}' not implemented.")


def _csv_path_for_profile(profile, csv_root: str) -> "Path | None":  # type: ignore[name-defined]  # noqa: E501
    """Derive the CSV path for a profile within *csv_root*."""
    from pathlib import Path

    try:
        p = Path(csv_root) / profile.category / profile.filename
        return p
    except Exception:  # noqa: BLE001
        return None


def validate_action(action: str) -> bool:
    """Return True if *action* would be accepted by the sandbox."""

    try:
        _check_forbidden(action)
        return action in _ALLOWED_ACTIONS
    except ValueError:
        return False
