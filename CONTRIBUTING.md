# Contributing

Thanks for helping improve the Agentic AI Decision System.

## Local Setup

```bash
git clone <repo-url>
cd <repo-name>
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Before a PR

Run:

```bash
python -m pytest -q
decision-system eval
```

## Do Not Commit

- `.env`
- `.decision_system/`
- generated eval result JSON files
- real API keys
- real company documents

## Expectations

- Keep fake provider tests passing.
- Add tests for new features.
- Keep provider tests mocked.
- Keep final reports claim-ledger driven.
- Update docs and changelog for user-facing changes.
