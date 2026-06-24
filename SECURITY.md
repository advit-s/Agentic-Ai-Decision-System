# Security Policy

## Reporting a Security Issue

If you discover a security vulnerability in this project, please report it privately.

**Do not disclose security issues publicly in GitHub issues, discussions, or pull requests.**

To report a security issue, email the project maintainers or open a GitHub Security Advisory.

## What Is in Scope

- Authentication and authorization bypass
- Data exposure or leakage (workspace isolation failures)
- Remote code execution
- Injection vulnerabilities (command injection, path traversal)
- Secret/token exposure in logs, UI, or diagnostics

## What Is Out of Scope

- **This is a local MVP beta candidate.** It is not production-ready.
- Demo mode (default) has no authentication — this is by design
- Governed mode provides basic RBAC but is not enterprise-grade
- There is no encryption at rest — data is stored as plain JSON/SQLite
- There is no transport encryption — local deployments use HTTP

## How We Handle Reports

1. We will acknowledge receipt within 48 hours
2. We will assess severity and impact
3. We will work on a fix and coordinate disclosure
4. We will credit reporters (with permission) in release notes

## Security Features

| Feature | Status |
|---------|--------|
| Secret scanning | ✅ Local file scan |
| Provider secret redaction | ✅ In UI and logs |
| Workspace isolation | ✅ SQLite + JSON per workspace |
| RBAC (governed mode) | ✅ Owner, admin, analyst, reviewer, viewer |
| Audit logging | ✅ All key actions logged |
| Safe diagnostics script | ✅ No secrets collected |

## Safe Use Recommendations

- Use demo mode for evaluation — no secrets needed
- Use sample/demo data instead of real production data
- If testing with real data, understand the local storage model
- Run `./scripts/collect-diagnostics.sh` before reporting — it is safe
- Never paste API keys, tokens, or `.env` contents into public issues
