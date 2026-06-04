# Agentic Decision System

Backend-first v0.1 prototype for producing cited decision briefs from local company documents.

## Commands

```bash
decision-system index
decision-system ask "Should we proceed with Project X?"
```

The default provider is `fake`, so tests and local smoke runs do not require API keys.

## Setup

```bash
python -m pip install -e ".[dev]"
```

## Example

```bash
mkdir -p company_docs
echo "Billing migration requires rollback planning." > company_docs/billing.md
decision-system index
decision-system ask "Should we migrate billing?"
```

## Demo Smoke Test

Use the included fake demo documents in `company_docs/`:

```bash
decision-system index
decision-system ask "Should we migrate billing?"
python -m pytest -q
```

Expected output shape:

```text
Indexed <document_count> documents into <chunk_count> chunks.

# Decision Report
## Recommendation
...
## Evidence Citations
- doc-...:chunk-...
## Risks
...
## Contradictions
- ... Cited evidence explicitly contradicts this claim.
## Unsupported Assumptions
...
## Confidence Level
low
## Human Review Required
- Resolve contradicted claims before taking action.

13 passed
```

The demo should show citation-ready evidence IDs, at least one verified ledger claim internally, and at least one contradicted claim or human review item from the `CONTRADICTS:` marker.

## v0.1 Limits

- Uses fake provider by default.
- Supports `.md` and `.txt`.
- Does not include a frontend or database.
- Does not execute external actions.
