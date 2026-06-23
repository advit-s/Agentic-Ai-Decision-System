"""Evidence search node for workspace-scoped evidence retrieval in workflows."""

from __future__ import annotations

from decision_system.workflow_engine.models import (
    WorkflowNode,
    ExecutionContext,
)


class EvidenceSearchNode(WorkflowNode):
    """Searches workspace evidence using keyword or vector retrieval.

    Inputs:
        workspace_id (str): Workspace to search in.
        query (str): The search query.
        limit (int, optional): Max results. Default 10.
        source_ids (list[str], optional): Filter by source IDs.
        file_types (list[str], optional): Filter by file types.

    Output:
        evidence_results (list): List of evidence search results.
        retrieval_mode (str): 'vector' or 'keyword'.
        result_count (int): Number of results returned.
    """

    type: str = "decision_system.evidence_search"
    label: str = "Evidence Search"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        workspace_id = inputs.get("workspace_id") or self.config.get("workspace_id", "")
        query = inputs.get("query") or self.config.get("query", "")
        limit = int(inputs.get("limit") or self.config.get("limit", 10))
        source_ids = inputs.get("source_ids") or self.config.get("source_ids", [])
        file_types = inputs.get("file_types") or self.config.get("file_types", [])

        if not workspace_id:
            return {
                "error": "workspace_id is required",
                "evidence_results": [],
                "retrieval_mode": "none",
                "result_count": 0,
            }

        if not query:
            return {
                "error": "query is required",
                "evidence_results": [],
                "retrieval_mode": "none",
                "result_count": 0,
            }

        # Try vector search first
        retrieval_mode = "keyword"
        results = []

        try:
            from decision_system.config import load_settings
            from decision_system.rag.retriever import retrieve_evidence
            from decision_system.data_sources.models import EvidenceSearchResult

            settings = load_settings()
            chunks = retrieve_evidence(
                query=query,
                store_dir=settings.store_dir,
                collection_name=settings.collection_name,
                top_k=limit,
            )

            if chunks:
                retrieval_mode = "vector"
                results = [
                    {
                        "evidence_id": c.evidence_id,
                        "workspace_id": workspace_id,
                        "source_id": c.document_id,
                        "source_name": c.source_filename,
                        "chunk_id": c.chunk_id,
                        "text": c.text,
                        "score": c.score or 0.0,
                        "metadata": {"source_path": c.source_path},
                    }
                    for c in chunks
                ]
        except Exception:
            pass

        if not results:
            # Fallback to keyword search
            try:
                from decision_system.data_sources.store import DataSourceStore

                store = DataSourceStore()
                kw_results = store.search_chunks_keyword(
                    workspace_id=workspace_id,
                    query=query,
                    limit=limit,
                    source_ids=source_ids if source_ids else None,
                    file_types=file_types if file_types else None,
                )
                results = [r.model_dump(mode="json") for r in kw_results]
            except Exception:
                results = []

        # Emit event for observability
        if ctx.execution_id:
            try:
                from decision_system.workflow_engine.engine.events import EventBus

                bus = EventBus()
                bus.emit(
                    event_type="evidence_search_completed",
                    execution_id=ctx.execution_id,
                    data={
                        "query": query,
                        "workspace_id": workspace_id,
                        "result_count": len(results),
                        "retrieval_mode": retrieval_mode,
                    },
                )
            except Exception:
                pass

        return {
            "evidence_results": results,
            "retrieval_mode": retrieval_mode,
            "result_count": len(results),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "title": "Workspace ID",
                    "description": "Workspace to search for evidence",
                },
                "query": {
                    "type": "string",
                    "title": "Search Query",
                    "description": "Query string for evidence search",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "title": "Max Results",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "source_ids": {"type": "array", "items": {"type": "string"}},
                "file_types": {"type": "array", "items": {"type": "string"}},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "evidence_results": {"type": "array"},
                "retrieval_mode": {"type": "string"},
                "result_count": {"type": "integer"},
                "error": {"type": "string"},
            },
        }
