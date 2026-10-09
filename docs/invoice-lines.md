---
title: Invoice lines
updated: 2025-12-01
---

# Invoice lines

An invoice holds two kinds of line. **Usage lines** are computed from the events reported to each meter and priced
with that meter's price. **Manual lines** are ones you add yourself: a set-up fee, a one-off service, a goodwill
adjustment.

Both kinds can be changed while the invoice is `draft`. Once it finalises, every line is frozen and any change returns
`409 invoice_finalized`.

## The line object

```json
{
  "id": "il_0c3e71",
  "meter": "api_calls",
  "description": "API calls, March 2026",
  "quantity": 184220,
  "unit_amount_minor": 2,
  "amount_minor": 368440
}
```

Manual lines have `"meter": null`.

## Editing a usage line

```bash
curl -X PATCH https://api.birchwell.io/v1/invoices/inv_5d02c7/lines/il_0c3e71 \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 180000, "description": "API calls, March 2026 (outage hours excluded)"}'
```

A usage line you have patched is **pinned**: later events for that meter no longer recompute it. Use this when you have
agreed a figure with the customer. Unpatched usage lines keep updating until finalisation.

## Adding and removing manual lines

```python
import os
import requests

BASE = "https://api.birchwell.io/v1/invoices/inv_5d02c7/lines"
H = {"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"}

line = requests.post(
    BASE,
    headers=H,
    json={"description": "Onboarding workshop", "quantity": 1, "unit_amount_minor": 45000},
    timeout=10,
).json()

requests.delete(f"{BASE}/{line['id']}", headers=H, timeout=10).raise_for_status()
```

Only manual lines can be deleted. To remove a usage charge, patch its `quantity` to `0`.

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | Negative `quantity`, or deleting a usage line |
| 404 | `invoice_not_found` | Unknown invoice |
| 409 | `invoice_finalized` | The invoice is no longer `draft` |
| 403 | `insufficient_permissions` | Called with a `usage_only` key |

Amounts are integers in minor units in the invoice's currency. The invoice's `subtotal_minor` is recalculated after
each change.
