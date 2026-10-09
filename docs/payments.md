---
title: Recording payments
updated: 2025-10-06
---

# Recording payments

Birchwell does not move money. Your customers pay you by card, bank transfer or however you have agreed, and you tell
Birchwell about each payment so the invoice balance stays right. When payments cover the amount due, the invoice
becomes `paid` and an `invoice.paid` webhook is sent.

## Endpoint

```
POST https://api.birchwell.io/v1/invoices/{id}/payments
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `amount_minor` | integer | yes | Positive, in the invoice's currency |
| `method` | string | yes | `card`, `bank_transfer` or `other` |
| `reference` | string | no | Your processor's charge id or the bank reference, up to 200 characters |

```bash
curl -X POST https://api.birchwell.io/v1/invoices/inv_5d02c7/payments \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"amount_minor": 367940, "method": "bank_transfer", "reference": "FENMORE-APR-0412"}'
```

```python
import os
import requests

resp = requests.post(
    "https://api.birchwell.io/v1/invoices/inv_5d02c7/payments",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    json={"amount_minor": 367940, "method": "card", "reference": "ch_8812"},
    timeout=10,
)
payment = resp.json()
print(payment["id"], payment["invoice_status"])
```

```json
{"id": "pay_7f20d1", "invoice_id": "inv_5d02c7", "amount_minor": 367940, "invoice_status": "paid"}
```

## When an invoice counts as paid

An invoice is `paid` once its payments add up to `total_minor` minus any credit notes. Partial payments are allowed and
simply lower `amount_due_minor`. The `invoice.paid` event fires once, at the moment the balance reaches zero.

## Rules and errors

Payments can only be recorded against a `finalized` invoice. A `draft` invoice is still changing, and a `paid` or
`void` one has nothing left to pay.

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | Unknown `method`, or non-positive amount |
| 404 | `invoice_not_found` | Unknown invoice |
| 409 | `invoice_not_finalized` | The invoice is still `draft` |
| 409 | `invoice_finalized` | The invoice is already `paid` or `void` |
| 422 | `payment_exceeds_balance` | The amount is more than `amount_due_minor` |

Payments cannot be deleted. If one was recorded in error, issue a [credit note](credit-notes.md) for the difference
after agreeing it with the customer, and note the reason.
