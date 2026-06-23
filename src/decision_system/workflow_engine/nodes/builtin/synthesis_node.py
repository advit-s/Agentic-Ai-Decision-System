"""Evidence Synthesis workflow node — AI-assisted synthesis from retrieved evidence."""

from __future__ import annotations

from decision_system.workflow_engine.models import (
    WorkflowNode,
    ExecutionContext,
)


class EvidenceSynthesisNode(WorkflowNode):
    """Synthesizes workspace evidence using AI, with optional auto-verification.

    Uses a configured provider (fake, Ollama, OpenAI-compatible) to generate
    summaries, extract claims, detect risks/opportunities, or create report
    outlines. Generated claims are saved as pending until verified.

    Inputs:
        workspace_id (str): Workspace to synthesize evidence for.
        question (str): Question or objective for the synthesis.
        evidence_results (list, optional): Pre-retrieved evidence list.
        provider_id (str, optional): Provider to use.
        model (str, optional): Model to use.
        synthesis_mode (str): One of summary, risks, opportunities, claims, report_outline.
        auto_verify (bool): Whether to verify generated claims immediately.

    Output:
        synthesis_id (str): Unique synthesis operation ID.
        summary_text (str): Synthesized summary or analysis.
        claim_ids (list): IDs of generated draft claims.
        verification_summary (dict, optional): Auto-verification results.
        warnings (list): Any warnings from the synthesis.
        result_count (int): Number of generated claims.
    """

    type: str = "decision_system.evidence_synthesis"
    label: str = "Evidence Synthesis"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        workspace_id = inputs.get("workspace_id") or self.config.get("workspace_id", "")
        question = inputs.get("question") or self.config.get("question", "")
        evidence_results = inputs.get("evidence_results") or self.config.get("evidence_results", [])
        provider_id = inputs.get("provider_id") or self.config.get("provider_id", "")
        model = inputs.get("model") or self.config.get("model", "")
        synthesis_mode = inputs.get("synthesis_mode") or self.config.get("synthesis_mode", "summary")
        auto_verify = inputs.get("auto_verify") or self.config.get("auto_verify", False)

        if not workspace_id:
            return {"error": "workspace_id is required", "claim_ids": [], "result_count": 0}
        if not question:
            return {"error": "question is required", "claim_ids": [], "result_count": 0}

        # Find provider config by name or ID
        provider_config = None
        if provider_id:
            try:
                from decision_system.providers.store import get_provider, get_provider_by_name
                provider_config = get_provider(provider_id) or get_provider_by_name(provider_id)
            except Exception:
                pass

        # Run synthesis
        try:
            from decision_system.synthesis.service import run_synthesis
            result = run_synthesis(
                workspace_id=workspace_id,
                question=question,
                evidence_results=evidence_results if evidence_results else None,
                provider_id=provider_id if provider_id else None,
                model=model if model else None,
                synthesis_mode=synthesis_mode,  # type: ignore
                provider_config=provider_config,
            )
        except Exception as e:
            return {
                "error": f"Synthesis failed: {type(e).__name__}: {e}",
                "claim_ids": [],
                "result_count": 0,
                "warnings": [str(e)],
            }

        # Save draft claims
        claim_ids = []
        if result.draft_claims:
            try:
                for dc in result.draft_claims:
                    from decision_system.ledger.models import Claim
                    from decision_system.ledger.store import ClaimLedgerStore
                    store = ClaimLedgerStore()
                    claim = Claim(
                        claim_text=dc.claim_text,
                        claim_type=dc.claim_type,
                        confidence=dc.confidence,
                        status="pending",
                        workspace_id=workspace_id,
                        source="evidence_synthesis",
                        metadata={
                            "synthesis_id": result.synthesis_id,
                            "evidence_ids": dc.evidence_ids,
                            "evidence_snippets": dc.evidence_snippets,
                        },
                    )
                    saved = store.save_claim(claim)
                    if saved and hasattr(saved, "claim_id"):
                        claim_ids.append(saved.claim_id)
            except Exception:
                pass

        # Auto-verify if requested
        verification_summary = None
        if auto_verify and claim_ids:
            try:
                from decision_system.verification.verifier import VerifierService
                verifier = VerifierService()
                v_results = []
                for cid in claim_ids:
                    v = verifier.verify_claim(cid, workspace_id)
                    if v:
                        v_results.append(v.model_dump(mode="json") if hasattr(v, "model_dump") else v)
                verification_summary = {
                    "total": len(v_results),
                    "verified": sum(1 for v in v_results if isinstance(v, dict) and v.get("status") != "error"),
                    "results": v_results,
                }
            except Exception:
                verification_summary = {"error": "Auto-verification failed"}

        output = {
            "synthesis_id": result.synthesis_id,
            "summary_text": result.summary_text,
            "claim_ids": claim_ids,
            "warnings": result.warnings + result.parse_warnings,
            "result_count": len(claim_ids),
        }
        if verification_summary:
            output["verification_summary"] = verification_summary

        return output

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "title": "Workspace ID",
                },
                "question": {
                    "type": "string",
                    "title": "Question / Objective",
                    "description": "The question or objective for evidence synthesis",
                },
                "synthesis_mode": {
                    "type": "string",
                    "title": "Synthesis Mode",
                    "default": "summary",
                    "enum": ["summary", "risks", "opportunities", "claims", "report_outline"],
                },
                "provider_id": {
                    "type": "string",
                    "title": "Provider",
                    "description": "AI provider to use for synthesis",
                },
                "model": {
                    "type": "string",
                    "title": "Model",
                    "description": "Model to use for synthesis",
                },
                "auto_verify": {
                    "type": "boolean",
                    "title": "Auto-Verify Claims",
                    "default": False,
                    "description": "Automatically verify generated claims",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "question": {"type": "string"},
                "evidence_results": {"type": "array"},
                "provider_id": {"type": "string"},
                "model": {"type": "string"},
                "synthesis_mode": {"type": "string"},
                "auto_verify": {"type": "boolean"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "synthesis_id": {"type": "string"},
                "summary_text": {"type": "string"},
                "claim_ids": {"type": "array", "items": {"type": "string"}},
                "verification_summary": {"type": "object"},
                "warnings": {"type": "array", "items": {"type": "string"}},
                "result_count": {"type": "integer"},
                "error": {"type": "string"},
            },
        }
