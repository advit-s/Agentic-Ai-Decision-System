"""Sandbox wrapper for war-room tool execution."""

from __future__ import annotations


def validate_tool_call(tool_name: str) -> bool:
    """Return True if the tool call is allowed.

    The allow-list covers read-only and local-save operations.  Destructive
    or external actions are rejected.
    """
    allowed = {
        "read_profiles",
        "read_graph",
        "read_insights",
        "read_context",
        "save_artifact",
        "save_run",
    }
    if tool_name in allowed:
        return True
    blocked = ["delete", "remove", "rm", "exec", "shell", "http", "https", "send", "post", "drop"]
    lowered = tool_name.lower()
    for pattern in blocked:
        if pattern in lowered:
            return False
    return False


def sandboxed_read(store_type: str, local_state: dict) -> object:
    """Read from a local store through the sandbox.

    Returns the requested object or an empty default if unavailable.
    Currently supports ``profiles``, ``graph``, ``insights``.
    """
    if store_type == "profiles":
        profiles = local_state.get("profiles")
        if profiles is not None:
            return profiles
        try:
            from decision_system.data_catalog.store import load_profiles
            return load_profiles()
        except Exception: # noqa: BLE001
            from decision_system.data_catalog.models import DataProfileStore
            return DataProfileStore()

    if store_type == "graph":
        graph = local_state.get("knowledge_graph")
        if graph is not None:
            return graph
        try:
            from decision_system.graphing.store import load_knowledge_graph
            return load_knowledge_graph()
        except Exception: # noqa: BLE001
            from decision_system.graphing.models import KnowledgeGraph
            return KnowledgeGraph()

    if store_type == "insights":
        insights = local_state.get("insights")
        if insights is not None:
            return insights
        try:
            from decision_system.insights.store import load_insights
            return load_insights()
        except Exception: # noqa: BLE001
            from decision_system.insights.models import InsightStore
            return InsightStore()

    raise ValueError(f"Unknown store type: {store_type!r}")
