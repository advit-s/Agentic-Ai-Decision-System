"""Local JSON persistence for the extracted knowledge graph."""

from pathlib import Path

from decision_system.graphing.models import KnowledgeGraph


DEFAULT_GRAPH_PATH = Path(".decision_system") / "graph" / "knowledge_graph.json"


def save_knowledge_graph(
    graph: KnowledgeGraph,
    path: Path | str = DEFAULT_GRAPH_PATH,
) -> Path:
    """Write a knowledge graph JSON file and return its path."""

    graph_path = Path(path)
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(graph.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return graph_path


def load_knowledge_graph(path: Path | str = DEFAULT_GRAPH_PATH) -> KnowledgeGraph:
    """Load a knowledge graph JSON file, or return an empty graph if missing."""

    graph_path = Path(path)
    if not graph_path.exists():
        return KnowledgeGraph()
    return KnowledgeGraph.model_validate_json(graph_path.read_text(encoding="utf-8"))
