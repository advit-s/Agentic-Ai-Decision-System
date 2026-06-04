"""CLI entry points for the v0.1 backend-first prototype.

The CLI is the only user interface in v0.1. It indexes local documents and
asks decision questions through the fixed LangGraph workflow without requiring
API keys, a database, auth, or a frontend.
"""

from uuid import uuid4

import typer
from rich.console import Console

from decision_system.config import load_settings
from decision_system.graph.workflow import build_workflow
from decision_system.rag.chunker import chunk_documents
from decision_system.rag.loader import load_documents
from decision_system.rag.vector_store import index_chunks


app = typer.Typer(help="Create cited decision briefs from local company documents.")
console = Console()


@app.command()
def index() -> None:
    """Index local documents from the configured docs directory.

    Inputs come from environment-backed settings. The command reads `.md` and
    `.txt` files, chunks them, and writes a local Chroma collection. Its main
    side effect is refreshing the configured vector store.
    """

    settings = load_settings()
    documents = load_documents(settings.docs_dir)
    chunks = chunk_documents(documents)
    chunk_count = index_chunks(
        chunks,
        store_dir=settings.store_dir,
        collection_name=settings.collection_name,
    )
    console.print(f"Indexed {len(documents)} documents into {chunk_count} chunks.")


@app.command()
def ask(question: str, top_k: int = 6) -> None:
    """Run the decision workflow for a CLI question.

    Args:
        question: Decision question to analyze.
        top_k: Maximum evidence chunks to retrieve.

    The command prints Markdown to stdout. It uses the fake provider by default
    and does not execute external actions in v0.1.
    """

    graph = build_workflow()
    result = graph.invoke(
        {
            "run_id": str(uuid4()),
            "question": question,
            "top_k": top_k,
        }
    )
    console.print(result["final_report"].markdown)
