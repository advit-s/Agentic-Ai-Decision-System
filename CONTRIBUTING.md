# Contributing to the Agentic AI Decision System

> **Version:** 1.35.0-dev
> **Milestone:** Public Beta Release Candidate

Thank you for your interest in contributing! This is a **local MVP beta** project, and all contributions — code, docs, issues, and feedback — are welcome.

## How to Contribute

### Reporting Bugs
1. Check [KNOWN_LIMITATIONS.md](./docs/KNOWN_LIMITATIONS.md) first
2. Collect diagnostics: `./scripts/collect-diagnostics.sh`
3. Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml)

### Suggesting Features
1. Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml)
2. Explain the problem, use case, and proposed behavior
3. Note any local-first or security constraints

### Submitting Beta Feedback
Use the [Beta Feedback template](.github/ISSUE_TEMPLATE/beta_feedback.yml)

### Submitting Code Changes

#### Prerequisites
- Python 3.11+
- Node.js 18+
- Familiarity with the [Architecture](./docs/ARCHITECTURE.md) and [Decisions](./docs/DECISIONS.md)

#### Development Setup
```bash
git clone <your-fork>
cd Agentic-Ai-Decision-System
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
cd web/workflow-builder && npm install && cd ../..
```

#### Code Standards
- **Python**: Follow PEP 8. Use type hints. Write tests.
- **JavaScript/JSX**: Follow standard React conventions. Write tests.
- **Shell scripts**: Use `bash -n` to verify syntax before committing.
- **Documentation**: Keep docs accurate. Update known limitations if adding new constraints.

#### Testing Requirements
- All backend tests must pass: `python -m pytest -q`
- All frontend tests must pass: `cd web/workflow-builder && npm test`
- Frontend must build: `cd web/workflow-builder && npm run build`
- Repository hygiene: `decision-system check-hygiene`

#### Pull Request Process
1. Fork the repository
2. Create a feature branch from `master`
3. Make your changes
4. Write or update tests
5. Run validation (see above)
6. Submit a PR using the [PR template](.github/pull_request_template.md)
7. Ensure the PR checklist is complete

#### What Not to Do
- Do not add new product features without discussion (open an issue first)
- Do not add new connector types without a clear use case
- Do not add external write actions
- Do not add cloud-first infrastructure
- Do not add telemetry or auto-upload diagnostics
- Do not claim production-ready
- Do not expose secrets or private data in any output

## Code of Conduct

Be respectful and constructive. This project is maintained by volunteers and contributors. Disagreements are fine; personal attacks are not.

## Questions?

Open a GitHub Discussion or check the [docs](./docs/).
