---
title: Team roles
updated: 2025-09-22
---

# Team roles

People sign in to the Birchwell dashboard with their own accounts. Their role decides what they can do there. Roles do
not apply to API calls; those are governed by the key and its type.

| Role | Invoices and customers | Credit notes | Meters and prices | API keys and webhooks | Billing settings |
|---|---|---|---|---|---|
| Owner | Edit | Issue | Edit | Manage | Edit |
| Admin | Edit | Issue | Edit | Manage | View |
| Finance | Edit | Issue | View | None | View |
| Developer | View | None | Edit | Manage webhooks only | None |
| Viewer | View | None | View | None | None |

There is exactly one owner. Ownership is transferred from **Settings**, then **Team**.

## Why developers cannot create keys

API keys act on real money. A `full` live key can issue credit notes worth up to an invoice's total, so key creation
sits with owners and admins. Developers can still create and test webhook endpoints and read the request log under
**Developers**, which covers most integration work.

## Auditing who did what

Actions in the dashboard and through the API are both recorded in the audit log. API actions show the key name;
dashboard actions show the person.

```bash
curl "https://api.birchwell.io/v1/audit_log?limit=50" \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import os
import requests

entries = requests.get(
    "https://api.birchwell.io/v1/audit_log",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    params={"limit": 50, "object_type": "credit_note"},
    timeout=10,
).json()["data"]
for e in entries:
    print(e["created_at"], e["actor"], e["object_id"])
```

The audit log needs a `full` key; a `usage_only` key gets `403 insufficient_permissions`. It is paginated with `limit`
and `cursor` like every list (see [Pagination](pagination.md)) and keeps 13 months of entries.

## Removing a person

Removal signs them out everywhere at once. If they had seen an API key, rotate it as described in
[Rotating API keys](key-rotation.md); keys are not tied to people and are not revoked automatically.
