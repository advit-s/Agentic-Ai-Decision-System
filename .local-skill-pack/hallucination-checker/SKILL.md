---
name: hallucination-checker
description: Use this when checking agent outputs, claims, reports, or RAG answers for hallucinations in the company decision system. Focuses on evidence support, contradiction detection, overclaiming, and confidence calibration.
---

# Hallucination Checker

Use this skill to find unsupported or overstated content before a report reaches the user.

## Checks

- Every material claim has evidence or is labeled unsupported.
- Evidence actually supports the claim, not just the same topic.
- No claim contradicts retrieved evidence without being labeled contradicted.
- Confidence matches evidence strength.
- Recommendations do not depend on unsupported assumptions.
- The answer does not cite nonexistent documents, chunks, or IDs.

## Classification

Use these labels:

- `verified`: Directly supported by cited evidence.
- `unsupported`: No sufficient evidence found.
- `contradicted`: Evidence conflicts with the claim.
- `overstated`: Partly supported but phrased too strongly.

## Output

Return a short finding list with claim text, label, evidence reference, and recommended correction.
