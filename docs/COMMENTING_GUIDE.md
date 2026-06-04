# Commenting Guide

Use comments to make the v0.1 system safe to continue, not noisy.

## Module Docstrings

Every important source file should start with a module docstring that explains why the module exists in the architecture. Keep it practical: name the boundary, the main side effects, and any v0.1 simplifications.

## Public Function and Class Docstrings

Public functions and classes should explain:

- what the function or class does
- important inputs
- outputs
- side effects
- v0.1 limitations
- why it exists in the architecture

## Inline Comments

Inline comments should explain why something exists, not repeat obvious code behavior.

Good places for comments:

- safety constraints
- fake hash embeddings
- Chroma adapter compatibility methods
- workflow linear/no-loop constraints
- contradiction marker logic
- report generation from the claim ledger only
- provider stubs

Avoid line-by-line comments for simple assignments or direct data mapping.

## Future Work Notes

Use `TODO(v0.2):` only for planned future work. Do not use open-ended `TODO` comments without a version or reason.
