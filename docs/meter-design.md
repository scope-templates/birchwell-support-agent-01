---
title: Designing your meters
updated: 2026-06-09
---

# Designing your meters

The meters you create decide what your customers can be charged for and how their invoices read. A few decisions made
early save a migration later, because a meter's aggregation cannot change once it exists.

## Start from the price list

Write down every line you want on an invoice, then work back to the meter behind it.

| Invoice line | Meter key | Aggregation | Event sent when |
|---|---|---|---|
| API calls | `api_calls` | `sum` | Each request, or a count every minute |
| Storage | `storage_gb_hours` | `sum` | Hourly, value = GB stored that hour |
| Concurrent jobs | `peak_concurrency` | `max` | Whenever the level changes |
| Active users | `active_users` | `unique_count` | A user does something billable |

## Pre-aggregate where you can

A `sum` meter does not need one event per request. Counting in your process and sending one event per customer per
minute, with `value` set to the count, gives the same invoice and far fewer events. It also keeps you comfortably
inside 1,000 events per request and 1,200 requests per minute.

```python
import os
import requests
from collections import Counter

calls = Counter()  # filled by your request middleware: calls[customer_id] += 1

def flush(minute_iso, batch_key):
    events = [
        {"customer_id": cid, "meter": "api_calls", "value": n, "timestamp": minute_iso}
        for cid, n in calls.items()
    ]
    calls.clear()
    if events:
        requests.post(
            "https://api.birchwell.io/v1/usage/events",
            headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}", "Idempotency-Key": batch_key},
            json={"events": events[:1000]},
            timeout=30,
        ).raise_for_status()
```

`unique_count` meters cannot be pre-aggregated in the same way, because the meter needs each `subject`.

## Name keys for the long term

Keys appear in your code and your exports for years. Prefer `storage_gb_hours` to `storage_v2`. Keys are unique per
account, including archived meters, so a retired key cannot be reused (`409 meter_key_taken`).

## Try it in test mode

```bash
curl -X POST https://api.birchwell.io/v1/meters \
  -H "Authorization: Bearer $BIRCHWELL_TEST_KEY" \
  -H "Content-Type: application/json" \
  -d '{"key": "storage_gb_hours", "name": "Storage", "aggregation": "sum", "unit": "GB-hour"}'
```

Test and live meters are separate, so you can try a design with `bw_test_` keys before creating it for real. You have
50 active meters per account; most products need fewer than ten.
