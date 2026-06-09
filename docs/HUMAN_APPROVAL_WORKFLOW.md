# Human Approval Workflow

## Overview

The Agentic Decision System includes a local human approval workflow to
record and track requests for human review before certain operations proceed.
This is a **record-keeping mechanism**, not an enforcement gate.

## Current Implementation

### Approval Requests

- Created via `decision-system approval request --reason "explanation"`
- Stored as JSON files under `.decision_system/security/approvals/`
- Tracked in the audit log

### Approval Lifecycle

1. **Request**: A user or system creates an approval request with a reason.
2. **Review**: A human reviews the request details.
3. **Decision**: The approval status is updated (approved, rejected, or cancelled).

### Approval Fields

| Field | Description |
|-------|-------------|
| `approval_id` | Unique identifier for the request |
| `reason` | Why the approval is needed |
| `status` | Current status (pending, approved, rejected, cancelled) |
| `requested_by` | Identity of the requester (defaults to "local-user") |
| `created_at` | When the request was created |
| `resolved_at` | When the request was resolved |
| `metadata` | Optional additional context |

### CLI Commands

```bash
# Create an approval request
decision-system approval request --reason "Deploy to staging"

# List all approval requests
decision-system approval list

# List with JSON output
decision-system approval list --json

# Inspect a specific approval
decision-system approval inspect APPROVAL_ID
```

## What This Does NOT Do

- **Does not block operations.** Creating an approval request does not prevent
  any command from executing. It records intent for human review.
- **Does not enforce RBAC.** There is no access control on who can create,
  approve, or reject requests.
- **Does not integrate with external systems.** There is no Jira, Slack, or
  email integration for approval notifications.
- **Does not persist across environments.** Approval records are local JSON files.

## When Approvals Should Be Required (Future)

In a production system, the following operations should require approval:

1. Deploying to production environments
2. Exporting company data outside the system
3. Running real connector imports (GitHub, Jira, etc.)
4. Modifying policy or governance rules
5. Processing high-risk or sensitive data categories
6. Any action flagged by the judge/verifier as requiring human review

## Integration with War Room

The war-room judge/verifier may flag artifacts as "REQUIRES HUMAN REVIEW" when:

- An artifact cites a high-severity insight
- Confidence is low
- Claims are unsupported or contradicted
- Risk factors exceed thresholds

These flags should trigger approval requests in a production system.

## API Endpoints (Planned)

Future API endpoints for approval workflow:

- `POST /approvals` - Create an approval request
- `GET /approvals` - List approval requests
- `GET /approvals/{id}` - Inspect a specific request
- `PATCH /approvals/{id}` - Update approval status

## Design Principles

1. **Approval is a record, not a gate** in the current prototype.
2. **All approval actions are audited** in the local audit log.
3. **Approval records are inspectable** via CLI and (planned) API.
4. **No real auth** means approval identity is trust-on-first-use.
5. **Future enforcement** should block flagged operations until approved.
