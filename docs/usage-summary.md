---
title: Usage summary
updated: 2025-11-11
---

# Usage summary

`GET /v1/usage/summary` returns the aggregated quantity of one meter for one customer in one period. It is the number
Birchwell will put on the invoice line, computed with the meter's aggregation (`sum`, `max` or `unique_count`).

Use it to show customers their usage to date, to reconcile against your own counters, or to check that a worker's
events arrived before the period closes.

## Parameters

| Parameter | Required | Example |
|---|---|---|
| `customer_id` | yes | `cus_a81f20` |
| `meter` | yes | `api_calls` |
| `period` | no | `2026-03`; defaults to the current period |

## Example

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
    params={"customer_id": "cus_a81f20", "meter": "active_users", "period": "2026-03"},
    timeout=10,
).json()
print(summary["aggregation"], summary["quantity"])
```

```json
{
  "customer_id": "cus_a81f20",
  "meter": "api_calls",
  "period": "2026-03",
  "aggregation": "sum",
  "quantity": 1284310
}
```

## Freshness

Accepted events show up in the summary within about 30 seconds. A summary for a period whose invoice has finalised is
fixed and matches the usage line on that invoice, unless the line was edited by hand while the invoice was still a
draft; edited lines are pinned and the summary still reports the raw aggregate.

## Who can call it

Both `full` and `usage_only` keys may call this endpoint, so a metering worker can check its own output without holding
a key that can touch invoices. See [API keys](api-keys.md).

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | `period` not in `YYYY-MM` form |
| 404 | `customer_not_found` | Unknown customer, or one from the other mode |
| 404 | `meter_not_found` | Unknown meter key |
| 429 | `rate_limited` | Over 1,200 requests per minute for this key |

Each call counts as one request against the rate limit. If you display usage on a customer dashboard, cache the
summary for a minute rather than calling once per page view.
