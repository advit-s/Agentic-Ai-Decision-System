# Issue Triage — v1.34.0-dev

> **Version:** 1.34.0-dev
> **Milestone:** Local Beta Feedback Loop + Issue Templates
> **Date:** 2026-06-24

## Labels

### Type Labels
| Label | Description |
|-------|-------------|
| `bug` | Something is broken or not working as expected |
| `enhancement` | Feature request or improvement |
| `docs` | Documentation issue or improvement |
| `beta-feedback` | General beta testing feedback |

### Area Labels
| Label | Description |
|-------|-------------|
| `frontend` | React SPA or UI issue |
| `backend` | FastAPI server or CLI issue |
| `connector` | Connector import or sync issue |
| `workflow` | Workflow builder or execution issue |
| `data-sources` | Document upload, parsing, or indexing issue |
| `verification` | Claim verification or evidence quality issue |
| `reports` | Report generation or export issue |
| `security` | Security or RBAC concern |

### Status Labels
| Label | Description |
|-------|-------------|
| `good-first-issue` | Good for new contributors |
| `needs-repro` | Cannot reproduce — needs more details |
| `blocked-env` | Environment-specific (Docker, OS, Tesseract) |

### Priority Labels
| Label | Description |
|-------|-------------|
| `critical` | Data loss, security leak, app cannot start |
| `high` | Demo path blocked |
| `medium` | Feature works but is broken or confusing |
| `low` | Polish, docs, minor issue |

## Severity Definitions

| Severity | Criteria | Response |
|----------|----------|----------|
| **Critical** | Data loss, security vulnerability, app crash on start, workspace corruption | Immediate triage, halt other work |
| **High** | Demo path blocked, major feature unusable, critical error in standard workflow | Triage within 1 day |
| **Medium** | Feature works but produces wrong results, confusing UI, missing error handling | Triage within 1 week |
| **Low** | Typo in docs, minor UI polish, nice-to-have enhancement | Triage within 1 month or backlog |

## Triage Process

### Step 1: Initial Review
1. Read the issue carefully
2. Check if it's a duplicate
3. Check if it matches a known limitation
4. Add appropriate labels
5. Assign severity

### Step 2: Reproduction
1. Try to reproduce with the provided steps
2. If environment-specific, add `blocked-env` label
3. If cannot reproduce, add `needs-repro` and ask for more details

### Step 3: Resolution
1. Fix critical/high issues immediately
2. Schedule medium issues for the current milestone
3. Move low issues to backlog

### Step 4: Close
1. Verify the fix works
2. Add a closing comment with resolution details
3. Close the issue

## Escalation

If an issue involves:
- **Data loss**: Raise to critical immediately
- **Security vulnerability**: Raise to critical, do not disclose in public issue until fixed
- **Legal/Compliance**: Raise to project maintainers

---

*This process applies to the local beta phase. It will evolve as the project matures.*
