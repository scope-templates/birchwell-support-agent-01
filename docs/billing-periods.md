---
title: Billing periods
updated: 2025-09-22
---

# Billing periods

Every Birchwell billing period is one calendar month in UTC, written as `YYYY-MM`. The March 2026 period is `2026-03`.
It opens at 2026-03-01T00:00:00Z and closes at 00:00 UTC on the first of the next month, 2026-04-01T00:00:00Z.

Periods are the same for every customer and cannot be shifted to a customer's sign-up date. Customers who join
mid-month get a first invoice covering the days they were active.

## Which period an event belongs to

The event's `timestamp` decides, not the time you send it. An event stamped `2026-03-31T23:59:58Z` and reported at
00:20 on 1 April belongs to `2026-03`.

```python
from datetime import datetime, timezone

def period_of(ts: str) -> str:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    return dt.strftime("%Y-%m")

assert period_of("2026-03-31T23:59:58Z") == "2026-03"
```

Always send timestamps in UTC. A local time without an offset is read as UTC, which shifts late-evening events in
other time zones into the wrong day and sometimes the wrong month.

## The grace window

A closed period stays open for late events for 48 hours, because invoices finalise 48 hours after the period closes.
For `2026-03` that window ends at 2026-04-03T00:00:00Z. After it, events stamped in March are rejected as
`period_finalized`.

## Reading a period's totals

```bash
curl "https://api.birchwell.io/v1/usage/summary?customer_id=cus_a81f20&meter=api_calls&period=2026-03" \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import os
import requests

summary = requests.get(
    "https://api.birchwell.io/v1/usage/summary",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    params={"customer_id": "cus_a81f20", "meter": "api_calls", "period": "2026-03"},
    timeout=10,
).json()
print(summary["aggregation"], summary["quantity"])
```

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | `period` not in `YYYY-MM` form, or a future period |
| 404 | `customer_not_found` | Unknown customer |
| 404 | `meter_not_found` | Unknown meter key |

In test mode you can close the current period at once with `POST /v1/test/advance_period`; see
[Test mode](test-mode.md).
