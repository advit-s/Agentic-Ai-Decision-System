"""Built-in decision intelligence node types.

Each node wraps an existing decision-system capability. All use the
fake provider by default and require no API keys for execution.
When a real LLM provider is configured, the nodes call it via
LLMClient for AI-powered analysis, claim extraction, and report writing.
"""

from __future__ import annotations

import json

from decision_system.workflow_engine.models import (
    ExecutionContext,
    WorkflowNode,
)
from decision_system.workflow_engine.providers.client import LLMClient


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
                chunks.append(
                    {
                        "evidence_id": chunk.evidence_id,
                        "source": chunk.source,
                        "text": chunk.text,
                        "score": chunk.score,
                    }
                )
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
                    "type": "string",
                    "default": "decision_docs",
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
        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )
        if provider_cfg is not None:
            cfg, model = provider_cfg
            question = inputs.get("question") or ""
            chunks = inputs.get("chunks") or []
            context = "\n".join(c.get("text", "") for c in chunks if isinstance(c, dict))

            client = LLMClient(cfg)
            result = await client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior technical analyst examining company data. "
                            "Analyze the provided documents and identify technical patterns, "
                            "architecture issues, and implementation concerns. "
                            "Return your analysis as structured JSON with 'findings' array."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Question: {question}\n\nContext:\n{context}",
                    },
                ],
                model=model,
                stream=False,
            )
            return {"analysis": result, "memo": {"raw": result}}

        # Fallback to fake provider
        from decision_system.agents.technical_analyst import run_technical_analysis
        from decision_system.models import EvidenceChunk

        question = inputs.get("question") or ""
        chunks = inputs.get("chunks") or []
        evidence = [
            EvidenceChunk(**c)
            if isinstance(c, dict) and "text" in c
            else EvidenceChunk(
                text=str(c),
                evidence_id="",
                document_id="",
                source_path="",
                source_filename="",
                chunk_id="",
            )
            for c in chunks
        ]

        memo = run_technical_analysis(question=question, evidence=evidence, provider=None)
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
                    "type": "string",
                    "default": "fake",
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
        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )
        if provider_cfg is not None:
            cfg, model = provider_cfg
            question = inputs.get("question") or ""
            chunks = inputs.get("chunks") or []
            context = "\n".join(c.get("text", "") for c in chunks if isinstance(c, dict))

            client = LLMClient(cfg)
            result = await client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a risk analyst evaluating business risks. "
                            "Analyze the provided context and identify potential risks, "
                            "their severity, and mitigations. "
                            "Return your analysis as structured JSON with 'risks' array."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Question: {question}\n\nContext:\n{context}",
                    },
                ],
                model=model,
                stream=False,
            )
            return {"analysis": result, "memo": {"raw": result}}

        # Fallback to fake provider
        from decision_system.agents.risk_analyst import run_risk_analysis
        from decision_system.models import EvidenceChunk

        question = inputs.get("question") or ""
        chunks = inputs.get("chunks") or []
        evidence = [
            EvidenceChunk(**c)
            if isinstance(c, dict) and "text" in c
            else EvidenceChunk(
                text=str(c),
                evidence_id="",
                document_id="",
                source_path="",
                source_filename="",
                chunk_id="",
            )
            for c in chunks
        ]

        memo = run_risk_analysis(
            question=question, evidence=evidence, technical_memo=None, provider=None
        )
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
                    "type": "string",
                    "default": "fake",
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
        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )
        if provider_cfg is not None:
            cfg, model = provider_cfg
            memo_text = str(
                inputs.get("memo", inputs.get("technical_memo", inputs.get("risk_memo", "")))
            )

            client = LLMClient(cfg)
            result = await client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract factual claims from the following text. "
                            "Each claim must be a single, verifiable statement. "
                            "Return the claims as a JSON array of strings."
                        ),
                    },
                    {"role": "user", "content": memo_text},
                ],
                model=model,
                stream=False,
            )
            try:
                claims = json.loads(result)
                if isinstance(claims, list):
                    return {"claims": claims, "count": len(claims)}
            except (json.JSONDecodeError, TypeError):
                pass
            return {"claims": [result], "count": 1}

        # Fallback to rule-based claim extraction
        from uuid import uuid4

        from decision_system.models import Claim

        tech_memo = inputs.get("technical_memo") or inputs.get("memo", {})
        risk_memo = inputs.get("risk_memo") or inputs.get("memo", {})

        claims = []
        for memo, agent_name, claim_type in [
            (tech_memo, "technical_analyst", "technical"),
            (risk_memo, "risk_analyst", "risk"),
        ]:
            if isinstance(memo, dict):
                for key in ("claims", "findings"):
                    items = memo.get(key, [])
                    if isinstance(items, list):
                        for item in items:
                            text = item.get("title", "") if isinstance(item, dict) else str(item)
                            if text:
                                claims.append(
                                    Claim(
                                        claim_id=str(uuid4()),
                                        run_id="",
                                        source_agent=agent_name,
                                        claim_text=text,
                                        claim_type=claim_type,
                                    )
                                )
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
        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )
        if provider_cfg is not None:
            cfg, model = provider_cfg
            claims = inputs.get("claims") or []
            chunks = inputs.get("chunks") or []
            claims_text = json.dumps(
                [c if isinstance(c, dict) else {"text": str(c)} for c in claims]
            )
            evidence_text = "\n".join(c.get("text", "") for c in chunks if isinstance(c, dict))

            client = LLMClient(cfg)
            result = await client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Given these claims and the supporting evidence, verify each claim. "
                            "Classify each as: supported, unsupported, or contradicted. "
                            "Return the result as a JSON array of objects with "
                            "'claim', 'status', and 'evidence' fields."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Claims:\n{claims_text}\n\nEvidence:\n{evidence_text}",
                    },
                ],
                model=model,
                stream=False,
            )
            try:
                verified = json.loads(result)
                if isinstance(verified, list):
                    return {"verified_claims": verified, "count": len(verified)}
            except (json.JSONDecodeError, TypeError):
                pass
            return {"verified_claims": [{"raw": result}], "count": 1}

        # Fallback to rule-based verifier
        from decision_system.ledger.verifier import verify_claims
        from decision_system.models import Claim, EvidenceChunk

        claims = inputs.get("claims") or []
        chunks = inputs.get("chunks") or []
        raw_claims = [
            Claim(**c)
            if isinstance(c, dict) and "claim_text" in c
            else Claim(
                claim_id="",
                run_id="",
                source_agent="",
                claim_text=str(c),
                claim_type="technical",
            )
            for c in claims
        ]
        evidence = [
            EvidenceChunk(**c)
            if isinstance(c, dict) and "text" in c
            else EvidenceChunk(
                text=str(c),
                evidence_id="",
                document_id="",
                source_path="",
                source_filename="",
                chunk_id="",
            )
            for c in chunks
        ]

        verified = verify_claims(claims=raw_claims, evidence=evidence)
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
        # Try real provider first
        provider_cfg = ctx.resolve_provider(
            self.config.get("provider"),
            self.config.get("model"),
        )
        if provider_cfg is not None:
            cfg, model = provider_cfg
            question = inputs.get("question") or ""
            claims = inputs.get("verified_claims") or inputs.get("claims") or []
            claims_text = json.dumps(claims, indent=2)

            client = LLMClient(cfg)
            result = await client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Write a structured decision report based on the following "
                            "verified claims, findings, and analysis. Include an executive "
                            "summary, key findings, and recommendations. "
                            "Use Markdown formatting."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Question: {question}\n\nClaims:\n{claims_text}",
                    },
                ],
                model=model,
                stream=False,
            )
            return {
                "report": result,
                "format": self.config.get("format", "markdown"),
                "length": len(result),
            }

        # Fallback to rule-based report renderer
        from uuid import uuid4

        from decision_system.models import Claim
        from decision_system.reports.renderer import render_decision_report

        question = inputs.get("question") or ""
        claims = inputs.get("verified_claims") or inputs.get("claims") or []
        raw_claims = [
            Claim(**c)
            if isinstance(c, dict) and "claim_text" in c
            else Claim(
                claim_id=str(uuid4()),
                run_id="",
                source_agent="",
                claim_text=str(c),
                claim_type="technical",
            )
            for c in claims
        ]

        report_obj = render_decision_report(
            question=question,
            run_id=ctx.execution_id,
            claims=raw_claims,
        )
        report = report_obj.markdown if hasattr(report_obj, "markdown") else str(report_obj)

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
                    "type": "string",
                    "default": "markdown",
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
