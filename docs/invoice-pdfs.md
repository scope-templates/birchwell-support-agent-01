---
title: Invoice PDFs
updated: 2026-05-11
---

# Invoice PDFs

Every finalised invoice has a PDF you can send to your customer or attach to an email from your own system. The PDF is
generated at finalisation and never changes afterwards, so it matches the figures in `invoice.finalized`.

```
GET https://api.birchwell.io/v1/invoices/{id}/pdf
```

The response is `application/pdf`. A `draft` invoice has no PDF yet and returns `409 invoice_not_finalized`, because
its lines can still change.

## Downloading

```bash
curl -o inv_5d02c7.pdf https://api.birchwell.io/v1/invoices/inv_5d02c7/pdf \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import os
import requests

resp = requests.get(
    "https://api.birchwell.io/v1/invoices/inv_5d02c7/pdf",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=30,
)
resp.raise_for_status()
with open("inv_5d02c7.pdf", "wb") as fh:
    fh.write(resp.content)
```

## When to fetch it

The usual moment is when your webhook endpoint receives `invoice.finalized`. Queue the download rather than doing it
inside the webhook handler, which must answer within 15 seconds.

## What is printed

- Your company name, address and logo from the dashboard settings.
- The customer's `name` and billing email.
- The period, each line's description, quantity, unit amount and amount.
- Subtotal, tax at the customer's `tax_rate_percent`, and total, in the invoice currency.

Since 2026-05-11 the PDF uses the customer's currency to choose the number format, so `eur` invoices print
`1.234,56 €` and `gbp` invoices print `£1,234.56`.

## Credit notes and voided invoices

Each credit note has its own PDF at `GET /v1/credit_notes/{id}/pdf`, listing the original invoice and the `reason`.
A voided invoice keeps its PDF, stamped "Void".

## Errors

| Status | `error.code` | When |
|---|---|---|
| 404 | `invoice_not_found` | Unknown invoice |
| 404 | `credit_note_not_found` | Unknown credit note |
| 409 | `invoice_not_finalized` | The invoice is still `draft` |
| 403 | `insufficient_permissions` | A `usage_only` key |

PDF downloads count toward the 1,200 requests per minute limit. If you archive every invoice at month end, fetch them
one after another rather than all at once.
