---
title: Currencies and amounts
updated: 2025-10-06
---

# Currencies and amounts

Birchwell bills in three currencies: `gbp`, `eur` and `usd`. Codes are lowercase in requests and responses.

## Minor units everywhere

Every amount in the API is an integer in the currency's minor unit, in a field ending `_minor`: `amount_minor`,
`unit_amount_minor`, `total_minor`, `amount_due_minor`. 1,999 in `gbp` is £19.99; 1,999 in `usd` is $19.99. There are
no decimals and no floating point.

```python
def to_minor(amount: str) -> int:
    pounds, _, pence = amount.partition(".")
    return int(pounds) * 100 + int((pence + "00")[:2])

assert to_minor("19.99") == 1999
```

Fractional unit prices are not supported. If a unit is worth less than one minor unit, price it as a `package`, for
example 50 pence per 1,000 calls; see [Pricing models](pricing-models.md).

## A customer has one currency

The `currency` is set when the customer is created and cannot be changed. All of that customer's invoices, payments and
credit notes use it. To move a customer to another currency, create a new customer and point new usage at it from the
start of a period.

```bash
curl -X POST https://api.birchwell.io/v1/customers \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Fenmore Analytics BV", "email": "billing@fenmore.example", "currency": "eur", "external_id": "acct_2291_eu"}'
```

## Amounts must match the invoice currency

Payments and credit notes do not carry a currency of their own; they take the invoice's. Send `amount_minor` in that
currency:

```python
import os
import requests

requests.post(
    "https://api.birchwell.io/v1/invoices/inv_5d02c7/credit_notes",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    json={"amount_minor": 1500, "reason": "Outage on 14 March, 15.00 credit"},
    timeout=10,
)
```

## Rounding

Line amounts are rounded half up to the nearest minor unit once per line, after quantity times price. Tax is computed
on the subtotal and rounded once.

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | Unknown currency code, or a decimal in an `_minor` field |
| 422 | `credit_exceeds_total` | Credit notes would exceed the invoice total |
| 422 | `payment_exceeds_balance` | A payment larger than the amount still due |
