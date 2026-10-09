---
title: Invoices
updated: 2026-06-08
---

# Invoices

Birchwell creates one invoice per customer per billing period. You do not create invoices yourself: the invoice for
`2026-03` appears as a `draft` when March opens, fills up as usage events arrive, and finalises once the period has
closed. See [Invoice lifecycle](invoice-lifecycle.md) for the timing.

## The invoice object

| Field | Type | Notes |
|---|---|---|
| `id` | string | `inv_` followed by six characters, for example `inv_5d02c7` |
| `customer_id` | string | The customer billed, such as `cus_a81f20` |
| `period` | string | Calendar month in UTC, `2026-03` |
| `status` | string | `draft`, `finalized`, `paid` or `void` |
| `currency` | string | `gbp`, `eur` or `usd`, taken from the customer |
| `lines` | array | Usage and manual lines; see [Invoice lines](invoice-lines.md) |
| `subtotal_minor` | integer | Sum of line amounts |
| `tax_minor` | integer | Set at finalisation from the customer's tax rate |
| `total_minor` | integer | `subtotal_minor` plus `tax_minor` |
| `amount_due_minor` | integer | Total less payments and credit notes |
| `finalized_at`, `paid_at` | string or null | ISO 8601 UTC |

All amounts are integers in minor units (pence or cents).

## Fetching one invoice

```bash
curl https://api.birchwell.io/v1/invoices/inv_5d02c7 \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import os
import requests

resp = requests.get(
    "https://api.birchwell.io/v1/invoices/inv_5d02c7",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=10,
)
resp.raise_for_status()
invoice = resp.json()
print(invoice["status"], invoice["total_minor"], invoice["currency"])
```

## Listing a customer's invoices

`GET /v1/invoices` takes `customer_id`, `status` and `period` filters and pages with `limit` and `cursor`
([Pagination](pagination.md)):

```python
params = {"customer_id": "cus_a81f20", "status": "finalized", "limit": 100}
page = requests.get("https://api.birchwell.io/v1/invoices", headers=headers, params=params, timeout=10).json()
for inv in page["data"]:
    print(inv["id"], inv["period"], inv["amount_due_minor"])
```

## Errors

| Status | `error.code` | When |
|---|---|---|
| 401 | `missing_authorization` | No `Authorization` header |
| 403 | `insufficient_permissions` | A `usage_only` key; invoices need a `full` key |
| 404 | `invoice_not_found` | Unknown id, or an invoice from the other mode |
| 404 | `customer_not_found` | The `customer_id` filter names an unknown customer |

Invoice reads count toward the 1,200 requests per minute per key limit like every other call.
