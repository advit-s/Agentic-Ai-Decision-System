---
name: claim-ledger-designer
description: Use this when designing, implementing, or reviewing a claim ledger for the agentic company decision system. Covers schemas, statuses, evidence links, contradiction handling, and tests for claim verification.
---

# Claim Ledger Designer

Use this skill to make claims auditable instead of letting agents jump straight to conclusions.

## Core Fields

Track these fields for each material claim:

- `claim_id`
- `run_id`
- `source_agent`
- `claim_text`
- `claim_type`
- `status`: `pending`, `verified`, `unsupported`, `contradicted`
- `evidence_ids`
- `contradicting_evidence_ids`
- `confidence`
- `verification_notes`
- `created_at`
- `updated_at`

## Rules

- Store claims before final synthesis.
- Link claims to retrieval chunks or source documents, not vague prose.
- Preserve contradicted claims rather than deleting them.
- Require a verification note for any non-pending status.
- Make final reports consume the ledger rather than raw agent chat.

## Tests To Add

- Unsupported claims remain labeled unsupported.
- Contradicting evidence changes status to contradicted.
- Final report generation refuses missing ledger entries for material claims.
