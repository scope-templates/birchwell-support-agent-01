---
title: Customers
updated: 2026-04-07
---

# Customers

A customer is the account you bill: one of your own customers, such as a company using your SaaS product. Usage
events, invoices and payments all belong to a customer.

## Create a customer

```bash
curl -X POST https://api.birchwell.io/v1/customers \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Fenmore Analytics", "email": "billing@fenmore.example", "currency": "gbp", "external_id": "acct_2291"}'
```

```json
{
  "id": "cus_a81f20",
  "name": "Fenmore Analytics",
  "email": "billing@fenmore.example",
  "currency": "gbp",
  "external_id": "acct_2291",
  "tax_rate_percent": 20
}
```

| Field | Notes |
|---|---|
| `name` | Shown on invoices |
| `email` | Where finalised invoices are sent in live mode |
| `currency` | `gbp`, `eur` or `usd`; fixed at creation |
| `external_id` | Your own account id, up to 64 characters, unique per mode |
| `tax_rate_percent` | 0 to 30, applied at finalisation |

Creating a customer also opens a draft invoice for the current period.

## Look up by your own id

Workers usually know your account id, not Birchwell's. Fetch the customer by `external_id` once and cache the mapping:

```python
import os
import requests

resp = requests.get(
    "https://api.birchwell.io/v1/customers",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    params={"external_id": "acct_2291"},
    timeout=10,
)
customer_id = resp.json()["data"][0]["id"]  # cus_a81f20
```

`GET /v1/customers/{id}` fetches one customer by Birchwell id. The list endpoint is paginated with `limit` and
`cursor`; see [Pagination](pagination.md).

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | Missing `name`, unknown `currency`, or a duplicate `external_id` |
| 404 | `customer_not_found` | Unknown id, or a customer from the other mode |
| 403 | `insufficient_permissions` | Called with a `usage_only` key |

Usage events for a customer that does not exist are rejected per event with `customer_not_found`, so create customers
before their first billable action, typically at sign-up.

Test and live customers are separate; a `bw_test_` key cannot see `cus_a81f20` if it was created with a live key.
