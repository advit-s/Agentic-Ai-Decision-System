"""Built-in decision intelligence node types.

Each node wraps an existing decision-system capability. All use the
fake provider by default and require no API keys for execution.
"""

from __future__ import annotations

from pathlib import Path

from decision_system.workflow_engine.models import (
    WorkflowNode, ExecutionContext,
)


class RetrieveNode(WorkflowNode):
    """Retrieves evidence chunks from the local Chroma vector store."""
    type: str = "decision_system.retrieve"
    label: str = "Retrieve Evidence"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        question = inputs.get("question") or inputs.get("text") or ""
        if not question:
            return {"chunks": [], "count": 0}

        top_k = self.config.get("top_k", 5)

        try:
            from decision_system.rag.retriever import retrieve_evidence
            from decision_system.rag.vector_store import get_vector_store

            store = get_vector_store()
            collection_name = self.config.get("collection", "decision_docs")
            results = retrieve_evidence(
                question=question,
                collection_name=collection_name,
                top_k=top_k,
                vector_store=store,
            )
            chunks = []
            for chunk in results:
                chunks.append({
                    "evidence_id": chunk.evidence_id,
                    "source": chunk.source,
                    "text": chunk.text,
                    "score": chunk.score,
                })
            return {"chunks": chunks, "count": len(chunks)}
        except Exception as exc:
            return {"chunks": [], "count": 0, "error": str(exc)}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "top_k": {"type": "integer", "default": 5, "title": "Top K"},
                "collection": {
                    "type": "string", "default": "decision_docs",
                    "title": "Collection Name",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "text": {"type": "string"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "chunks": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class TechAnalystNode(WorkflowNode):
    """Runs technical analysis on retrieved evidence."""
    type: str = "decision_system.technical_analyst"
    label: str = "Technical Analyst"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.agents.technical_analyst import run_technical_analysis

        question = inputs.get("question") or ""
        chunks = inputs.get("chunks") or []
        provider = self.config.get("provider", ctx.provider)

        memo = run_technical_analysis(question=question, chunks=chunks, provider=provider)
        return {
            "memo": memo.model_dump() if hasattr(memo, "model_dump") else memo,
            "analysis": str(memo),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string", "default": "fake",
                    "enum": ["fake", "nvidia_nim", "ollama"],
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "chunks": {"type": "array"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "memo": {"type": "object"},
                "analysis": {"type": "string"},
            },
        }


class RiskAnalystNode(WorkflowNode):
    """Runs risk analysis on retrieved evidence."""
    type: str = "decision_system.risk_analyst"
    label: str = "Risk Analyst"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.agents.risk_analyst import run_risk_analysis

        question = inputs.get("question") or ""
        chunks = inputs.get("chunks") or []
        provider = self.config.get("provider", ctx.provider)

        memo = run_risk_analysis(question=question, chunks=chunks, provider=provider)
        return {
            "memo": memo.model_dump() if hasattr(memo, "model_dump") else memo,
            "analysis": str(memo),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string", "default": "fake",
                    "enum": ["fake", "nvidia_nim", "ollama"],
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "chunks": {"type": "array"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "memo": {"type": "object"},
                "analysis": {"type": "string"},
            },
        }


class ExtractClaimsNode(WorkflowNode):
    """Extracts claims from analyst memos into the claim ledger."""
    type: str = "decision_system.extract_claims"
    label: str = "Extract Claims"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.ledger.claim_ledger import ClaimLedger

        tech_memo = inputs.get("technical_memo") or inputs.get("memo", {})
        risk_memo = inputs.get("risk_memo") or inputs.get("memo", {})

        ledger = ClaimLedger()
        if isinstance(tech_memo, dict):
            ledger.add_claims_from_memo(tech_memo)
        if isinstance(risk_memo, dict):
            ledger.add_claims_from_memo(risk_memo)

        claims = ledger.get_all_claims()
        return {
            "claims": [c.model_dump() if hasattr(c, "model_dump") else c for c in claims],
            "count": len(claims),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "technical_memo": {"type": "object"},
                "risk_memo": {"type": "object"},
                "memo": {"type": "object"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "claims": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class VerifyClaimsNode(WorkflowNode):
    """Verifies extracted claims against retrieved evidence."""
    type: str = "decision_system.verify_claims"
    label: str = "Verify Claims"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.ledger.verifier import verify_claims

        claims = inputs.get("claims") or []
        raw_claims = [c if isinstance(c, dict) else {} for c in claims]
        chunks = inputs.get("chunks") or []

        verified = verify_claims(claims=raw_claims, chunks=chunks)
        return {
            "verified_claims": [
                v.model_dump() if hasattr(v, "model_dump") else v for v in verified
            ],
            "count": len(verified),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "claims": {"type": "array"},
                "chunks": {"type": "array"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "verified_claims": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class WriteReportNode(WorkflowNode):
    """Writes a decision report from verified claims."""
    type: str = "decision_system.write_report"
    label: str = "Write Report"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.reports.renderer import render_decision_report

        question = inputs.get("question") or ""
        claims = inputs.get("verified_claims") or inputs.get("claims") or []
        raw_claims = [c if isinstance(c, dict) else {} for c in claims]
        chunks = inputs.get("chunks") or []

        report_lines = render_decision_report(
            question=question,
            claims=[type("obj", (object,), c)() for c in raw_claims],  # simple compat
            chunks=chunks,
        )
        report = "\n".join(report_lines)

        return {
            "report": report,
            "format": self.config.get("format", "markdown"),
            "length": len(report),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string", "default": "markdown",
                    "enum": ["markdown", "json"],
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "claims": {"type": "array"},
                "verified_claims": {"type": "array"},
                "chunks": {"type": "array"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "report": {"type": "string"},
                "format": {"type": "string"},
                "length": {"type": "integer"},
            },
        }
