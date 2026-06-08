"""Security, governance, and audit package for v1.2.

Provides deterministic local secret scanning, PII redaction previews,
audit logging, policy checks, and approval request records.  All
operations are offline and do not contact external services.

No real auth, cloud scanning, secret vault, or production RBAC yet.
"""

from __future__ import annotations
