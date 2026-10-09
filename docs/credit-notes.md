---
title: Credit notes
updated: 2026-02-16
---

# Credit notes

A credit note reduces what a customer owes on an invoice that is already finalised. Use it for refunds, service-level
credits or billing mistakes found after the 48-hour grace window.

```
POST https://api.birchwell.io/v1/invoices/{id}/credit_notes
```

Call `POST /v1/invoices/{id}/credit_notes` with `amount_minor` and `reason`. Credit notes are only allowed on
finalised invoices, meaning status `finalized` or `paid`. While an invoice is still `draft`, fix the lines directly instead (see [Invoice lines](invoice-lines.md)).

## Request

| Field | Type | Required | Notes |
|---|---|---|---|
| `amount_minor` | integer | yes | Positive, in the invoice's currency |
| `reason` | string | yes | Up to 500 characters; printed on the credit note PDF |

```bash
curl -X POST https://api.birchwell.io/v1/invoices/inv_5d02c7/credit_notes \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"amount_minor": 1500, "reason": "Service credit for the 14 March outage"}'
```

```python
import os
import requests

resp = requests.post(
    "https://api.birchwell.io/v1/invoices/inv_5d02c7/credit_notes",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    json={"amount_minor": 1500, "reason": "Service credit for the 14 March outage"},
    timeout=10,
)
resp.raise_for_status()
note = resp.json()
```

## Response

```json
{
  "id": "cn_19b4e0",
  "invoice_id": "inv_5d02c7",
  "amount_minor": 1500,
  "currency": "gbp",
  "reason": "Service credit for the 14 March outage",
  "created_at": "2026-04-06T10:12:44Z"
}
```

The invoice's `amount_due_minor` drops by the credited amount straight away.

## Limits and errors

The credit notes on one invoice may add up to its `total_minor`, never more.

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | `amount_minor` missing, zero or negative; `reason` missing |
| 404 | `invoice_not_found` | Unknown invoice |
| 409 | `invoice_not_finalized` | The invoice is still `draft` |
| 422 | `credit_exceeds_total` | This note would take total credits above `total_minor` |

## Listing

`GET /v1/invoices/{id}/credit_notes` lists the notes on an invoice; `GET /v1/credit_notes/{id}` fetches one, or returns
`404 credit_note_not_found`. Credit notes do not send a webhook; record them on your side when the call succeeds.
