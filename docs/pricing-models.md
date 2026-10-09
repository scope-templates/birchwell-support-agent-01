---
title: Pricing models
updated: 2026-01-20
---

# Pricing models

A price turns a meter's quantity into money. Each price belongs to one meter and one currency and uses one of three
models: `per_unit`, `tiered` or `package`. All amounts are integers in minor units.

## `per_unit`

Every unit costs the same.

```json
{"meter": "storage_gb_hours", "currency": "gbp", "model": "per_unit", "unit_amount_minor": 3}
```

A quantity of 12,000 GB-hours at 3 pence is 36,000, shown as £360.00.

## `tiered`

Units are charged at the rate of the tier they fall in. `up_to: null` marks the last, open-ended tier.

```bash
curl -X POST https://api.birchwell.io/v1/prices \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "meter": "api_calls",
    "currency": "gbp",
    "model": "tiered",
    "tiers": [
      {"up_to": 10000, "unit_amount_minor": 2},
      {"up_to": null, "unit_amount_minor": 1}
    ]
  }'
```

For 25,000 calls: the first 10,000 at 2 pence (20,000) plus 15,000 at 1 penny (15,000), so 35,000 minor units.

## `package`

Units are sold in blocks, and a part block is charged as a full one.

```python
import os
import requests

requests.post(
    "https://api.birchwell.io/v1/prices",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    json={"meter": "api_calls", "currency": "eur", "model": "package",
          "package_size": 1000, "package_amount_minor": 500},
    timeout=10,
).raise_for_status()
```

2,300 calls are three packages: 1,500 minor units, or €15.00.

## Rules

- One active price per meter per currency. Creating another replaces it from the next period; the current draft
  invoices keep the old price.
- Prices apply to `sum`, `max` and `unique_count` meters alike. A `max` meter priced `per_unit` charges for the peak.
- A meter with no price in the customer's currency produces a zero-amount line, so usage is still visible on the
  invoice.

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | Unknown `model`, tiers out of order, or a non-integer amount |
| 404 | `meter_not_found` | `meter` names no meter |
| 409 | `meter_archived` | The meter is archived |

Line amounts on draft invoices can still be adjusted by hand before finalisation; see [Invoice lines](invoice-lines.md).
