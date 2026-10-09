---
title: Archiving meters
updated: 2025-09-22
---

# Archiving meters

Meters cannot be deleted, because finalised invoices refer to them. When you stop charging for something, or replace a
meter because its aggregation was wrong, archive it.

```bash
curl -X POST https://api.birchwell.io/v1/meters/api_calls_legacy/archive \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import os
import requests

resp = requests.post(
    "https://api.birchwell.io/v1/meters/api_calls_legacy/archive",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=10,
)
print(resp.json()["status"])  # archived
```

## What archiving does

| | Before | After |
|---|---|---|
| New usage events | Accepted | Rejected per event with `meter_archived` |
| Draft invoices for the current period | Line recomputed | Line kept with usage up to the archive time |
| Finalised invoices | Unchanged | Unchanged |
| Counts toward the 50 active meters | Yes | No |
| Key reusable | No | No |

Archiving cannot be undone. The key stays reserved so old invoices and exports remain unambiguous; creating a new meter
with the same key returns `409 meter_key_taken`.

## Replacing a meter

The usual reason to archive is a change of aggregation, for example moving seats from `sum` to `max`.

1. Create the new meter, such as `seats_peak` with `max`.
2. Add its price in each currency you bill.
3. Deploy workers that send to both meters for a short overlap, then only to the new one.
4. Archive the old meter at the start of a period, so no invoice carries half a month of each.

Events that still reach the archived meter come back in the `errors` array with their `position` and are sent as
`usage.rejected` webhooks, so a worker you forgot to update is easy to spot.

## Errors

| Status | `error.code` | When |
|---|---|---|
| 404 | `meter_not_found` | No meter with that key |
| 409 | `meter_archived` | The meter is already archived, or a price is created for it |
| 403 | `insufficient_permissions` | Called with a `usage_only` key |

`GET /v1/meters` lists active meters by default; add `?status=archived` to list the archived ones.
