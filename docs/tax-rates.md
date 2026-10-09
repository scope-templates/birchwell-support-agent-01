---
title: Tax rates
updated: 2026-01-12
---

# Tax rates

Birchwell applies one tax rate per customer, set as `tax_rate_percent` on the customer. It accepts values from 0 to 30
with up to two decimal places, so 20 for UK VAT, 21 for Dutch BTW, or 0 for a reverse-charge business customer.

Tax is calculated once, when the invoice finalises. While an invoice is `draft`, `tax_minor` is `0` and
`total_minor` equals `subtotal_minor`. At finalisation Birchwell computes:

```
tax_minor   = round(subtotal_minor * tax_rate_percent / 100)
total_minor = subtotal_minor + tax_minor
```

Rounding is half up, to the nearest minor unit.

## Setting the rate

```bash
curl -X PATCH https://api.birchwell.io/v1/customers/cus_a81f20 \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tax_rate_percent": 20}'
```

```python
import os
import requests

resp = requests.patch(
    "https://api.birchwell.io/v1/customers/cus_a81f20",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    json={"tax_rate_percent": 20},
    timeout=10,
)
resp.raise_for_status()
```

The rate in force at the moment of finalisation is the one used. Change it before the period's grace window ends
(48 hours after close) and the new rate applies to that period's invoice; change it later and only future invoices are
affected.

## Example

A `draft` invoice for `2026-03` with `subtotal_minor` of 368440 pence and a customer rate of 20 finalises with:

```json
{"subtotal_minor": 368440, "tax_minor": 73688, "total_minor": 442128, "currency": "gbp"}
```

## Credit notes and tax

A credit note's `amount_minor` is the gross amount, tax included. If you credit 1,500 pence on a 20% invoice, the PDF
shows the 250 pence of tax inside that figure; you do not add tax on top.

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | Rate below 0, above 30, or with more than two decimals |
| 404 | `customer_not_found` | Unknown customer id |
| 403 | `insufficient_permissions` | Called with a `usage_only` key |

Birchwell does not work out which rate applies to a customer. Decide that with your accountant and set it per customer.
