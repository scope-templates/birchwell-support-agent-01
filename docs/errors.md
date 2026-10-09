---
title: Errors
updated: 2026-08-17
---

# Errors

Failed requests return a 4xx or 5xx status with a JSON body of one shape:

```json
{
  "error": {
    "code": "invoice_not_finalized",
    "message": "Credit notes can only be issued on finalised invoices. inv_5d02c7 is draft.",
    "request_id": "req_6b2d0f91"
  }
}
```

Program against `code`. The `message` is written for a person and may change. `request_id` matches the
`Birchwell-Request-Id` response header.

## All codes

| Status | `code` | Meaning |
|---|---|---|
| 400 | `invalid_request` | Malformed JSON or an invalid field |
| 400 | `batch_empty` | `events` missing or empty |
| 401 | `missing_authorization` | No `Authorization: Bearer` header |
| 401 | `invalid_api_key` | Not a Birchwell key |
| 401 | `api_key_revoked` | Key was revoked |
| 403 | `insufficient_permissions` | Key type cannot call this endpoint |
| 404 | `customer_not_found` | Unknown customer, or one from the other mode |
| 404 | `invoice_not_found` | Unknown invoice |
| 404 | `meter_not_found` | Unknown meter key on a meter endpoint |
| 404 | `credit_note_not_found` | Unknown credit note |
| 404 | `webhook_endpoint_not_found` | Unknown webhook endpoint |
| 409 | `invoice_finalized` | Invoice is past `draft` (line edits), or already `paid` or `void` (payments) |
| 409 | `invoice_not_finalized` | Action needs a finalised invoice |
| 409 | `meter_archived` | Meter is archived |
| 409 | `meter_key_taken` | A meter with that key exists |
| 413 | `batch_too_large` | More than 1,000 events |
| 422 | `unknown_meter` | Usage event names a meter that does not exist |
| 422 | `subject_required` | `unique_count` event without `subject` |
| 422 | `period_finalized` | Event for a period whose invoice has finalised |
| 422 | `idempotency_key_mismatch` | Same `Idempotency-Key`, different body, within 24 hours |
| 422 | `credit_exceeds_total` | Credit notes would exceed the invoice total |
| 422 | `payment_exceeds_balance` | Payment larger than the amount due |
| 422 | `invalid_webhook_url` | Webhook URL is not public HTTPS |
| 429 | `rate_limited` | Over 1,200 requests per minute for this key |
| 500 | `internal_error` | Our fault; retry with backoff |
| 503 | `service_unavailable` | Maintenance or overload; honour `Retry-After` |

On `POST /v1/usage/events`, problems with single events (`unknown_meter`, `subject_required`, `period_finalized`,
`customer_not_found`, `meter_archived`, `invalid_request`) arrive inside a `202` response's `errors` array, not as the
request's status. See [Rejected events](rejected-events.md).

## Handling errors

```python
resp = s.post(f"{API}/invoices/inv_5d02c7/credit_notes",
              json={"amount_minor": 1500, "reason": "Outage on 3 March"}, timeout=10)
if resp.status_code == 409 and resp.json()["error"]["code"] == "invoice_not_finalized":
    edit_draft_line_instead()
```

```bash
curl -s https://api.birchwell.io/v1/invoices/inv_missing -H "Authorization: Bearer $BIRCHWELL_KEY"
# {"error": {"code": "invoice_not_found", ...}}
```

Retry only `429`, `500` and `503`. Every other code describes a request that will fail the same way again.
