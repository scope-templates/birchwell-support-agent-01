---
title: Meters
updated: 2026-03-03
---

# Meters

A meter is the thing you charge for: API calls, storage, seats, peak concurrency. Usage events name a meter by its
`key`, and at the end of each period Birchwell rolls the meter's events up into one quantity per customer.

How events roll up is the meter's aggregation, which is one of `sum`, `max`, `unique_count`. See
[Aggregation](aggregation.md) for when to use each.

## The meter object

```json
{
  "key": "active_users",
  "name": "Monthly active users",
  "aggregation": "unique_count",
  "unit": "user",
  "status": "active"
}
```

| Field | Notes |
|---|---|
| `key` | Lowercase letters, digits and underscores, up to 40 characters. Used in usage events. |
| `name` | Shown on invoices |
| `aggregation` | `sum`, `max` or `unique_count`; fixed once the meter is created |
| `unit` | Singular label for invoice lines, such as `call` or `GB-hour` |
| `status` | `active` or `archived` |

## Create a meter

```bash
curl -X POST https://api.birchwell.io/v1/meters \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"key": "api_calls", "name": "API calls", "aggregation": "sum", "unit": "call"}'
```

```python
import os
import requests

meter = requests.post(
    "https://api.birchwell.io/v1/meters",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    json={"key": "peak_concurrency", "name": "Peak concurrent jobs", "aggregation": "max", "unit": "job"},
    timeout=10,
).json()
```

List meters with `GET /v1/meters` and fetch one with `GET /v1/meters/{key}`.

## Limits

An account can have up to 50 active meters. Archived meters do not count toward the limit; see
[Archiving meters](archiving-meters.md).

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | Bad `key` format, or an `aggregation` other than the three above |
| 404 | `meter_not_found` | `GET` for a key that does not exist |
| 409 | `meter_key_taken` | A meter with that key already exists, active or archived |
| 422 | `unknown_meter` | A usage event names a key with no meter |

The aggregation cannot be changed after creation. If you picked the wrong one, create a new meter with a new key,
move your workers over, and archive the old one. Prices attach to meters; see [Pricing models](pricing-models.md).
