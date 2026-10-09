---
title: Invoice lifecycle
updated: 2026-04-20
---

# Invoice lifecycle

Every invoice moves through the same states, always forwards:

```
draft -> finalized -> paid
                   -> void
```

The key rule: invoices finalise 48 hours after the period closes; lines are editable until then.

## Timeline for one period

Take a customer billed monthly, period `2026-03`.

| Moment | What happens |
|---|---|
| 2026-03-01T00:00:00Z | Period opens; the `draft` invoice is created |
| During March | Usage events update the usage lines; you can edit lines and add manual ones |
| 2026-04-01T00:00:00Z | Period closes; the invoice stays `draft` for the grace window |
| Until 2026-04-03T00:00:00Z | Late events for March are still accepted; lines remain editable |
| 2026-04-03T00:00:00Z | Invoice finalises; tax is applied; `invoice.finalized` is sent |
| When payments cover the total | Status becomes `paid`; `invoice.paid` is sent |

The 48-hour grace window exists for workers that report usage late, for example a nightly job that runs just after
midnight. After finalisation, events with a March timestamp are rejected with `period_finalized` and each one emits a
`usage.rejected` webhook.

## Checking where an invoice is

```bash
curl https://api.birchwell.io/v1/invoices/inv_5d02c7 \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import os
import requests

inv = requests.get(
    "https://api.birchwell.io/v1/invoices/inv_5d02c7",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=10,
).json()

if inv["status"] == "draft":
    print("still editable")
else:
    print("finalised at", inv["finalized_at"])
```

## What each state allows

| Action | `draft` | `finalized` | `paid` | `void` |
|---|---|---|---|---|
| Edit or add lines | Yes | `409 invoice_finalized` | `409 invoice_finalized` | `409 invoice_finalized` |
| Issue a credit note | `409 invoice_not_finalized` | Yes | Yes | No |
| Record a payment | No | Yes | No | No |
| Download the PDF | `409 invoice_not_finalized` | Yes | Yes | Yes |
| Void | No | Yes, if unpaid | No | No |

Once an invoice is finalised, the only way to reduce what a customer owes is a [credit note](credit-notes.md).

## Voiding

`POST /v1/invoices/{id}/void` cancels a finalised invoice that has no payments, for example one sent to the wrong
customer. A voided invoice keeps its number and PDF for your records.

In test mode, `POST /v1/test/advance_period` closes the period straight away so you can watch this sequence without
waiting a month; see [Test mode](test-mode.md).
