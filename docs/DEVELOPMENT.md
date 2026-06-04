# Development

## Install Dev Dependencies

```bash
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

## Run Tests

```bash
python -m pytest -q
```

## Run Evals

```bash
decision-system eval
decision-system eval --json
```

Saved eval results are generated only when requested:

```bash
decision-system eval --save-results
```

## Add a New Provider

1. Implement the `LLMProvider` protocol in `src/decision_system/llm/provider.py`.
2. Return Pydantic models, not raw prose.
3. Add the provider to `src/decision_system/llm/factory.py`.
4. Keep `fake` as the default.
5. Add mocked tests. Do not call real hosted APIs in tests.
6. Document required environment variables in `.env.example` and provider docs.

## Add a New Agent

Do not add a free-form chat loop. Add a bounded graph node with:

- structured input
- structured output
- a clear place in the linear workflow
- tests for the node behavior
- report or ledger changes only if needed

## Add a New Eval Case

Create `evals/cases/<case_id>.json` with:

- `case_id`
- `question`
- `documents`
- `expectations`

Then run:

```bash
decision-system eval
```

## Coding Rules

- Keep the graph linear unless a later design explicitly changes it.
- Keep final reports ledger-driven.
- Keep provider output structured and validated.
- Use fake provider for default tests.
- Do not commit secrets, `.env`, generated state, or private company docs.

## Documentation Rules

- Update README for user-facing commands.
- Update provider docs for new environment variables.
- Update architecture docs when workflow boundaries change.
- Update changelog for visible behavior changes.
