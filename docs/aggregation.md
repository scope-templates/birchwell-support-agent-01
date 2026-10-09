---
title: Meter aggregation
updated: 2026-03-03
---

# Meter aggregation

A meter's `aggregation` decides how a period's usage events become the single quantity on the invoice line. There are
three: `sum`, `max`, `unique_count`. The `max` and `unique_count` aggregations were added on 2025-03-17; before that
every meter summed its events.

| Aggregation | Quantity for the period | Uses `value`? | Uses `subject`? |
|---|---|---|---|
| `sum` | Total of all `value`s | Yes | No |
| `max` | Largest single `value` | Yes | No |
| `unique_count` | Number of distinct `subject`s | No | Yes, required |

## `sum`

For things that add up: API calls, messages sent, GB-hours stored. Three events with values 120, 80 and 300 on the
`api_calls` meter give a quantity of 500.

## `max`

For capacity you reserve: peak concurrent jobs, the highest number of seats in use. Events with values 4, 9 and 6 on
`peak_concurrency` give 9. Send a reading whenever the level changes, or every few minutes; only the peak matters.

## `unique_count`

For "how many different": monthly active users, devices, projects touched. Each event needs a `subject`; `value` is
ignored. Events for `user_93`, `user_14` and `user_93` on `active_users` give 2. More on
[Unique-count meters](unique-count.md).

## Sending one event of each kind

```bash
curl -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Idempotency-Key: 3b8f0e1a-agg-demo" \
  -H "Content-Type: application/json" \
  -d '{"events": [
        {"customer_id": "cus_a81f20", "meter": "api_calls", "value": 120, "timestamp": "2026-03-10T08:00:00Z"},
        {"customer_id": "cus_a81f20", "meter": "peak_concurrency", "value": 9, "timestamp": "2026-03-10T08:00:00Z"},
        {"customer_id": "cus_a81f20", "meter": "active_users", "subject": "user_93", "timestamp": "2026-03-10T08:00:00Z"}
      ]}'
```

```python
import os
import requests

for meter in ("api_calls", "peak_concurrency", "active_users"):
    s = requests.get(
        "https://api.birchwell.io/v1/usage/summary",
        headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
        params={"customer_id": "cus_a81f20", "meter": meter, "period": "2026-03"},
        timeout=10,
    ).json()
    print(meter, s["aggregation"], s["quantity"])
```

## Errors

An event without `subject` on a `unique_count` meter is rejected with `subject_required`. Creating a meter with any
other aggregation returns `400 invalid_request`. Aggregation is fixed at creation; see [Meters](meters.md).
