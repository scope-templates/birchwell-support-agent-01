---
title: Webhook event reference
updated: 2026-08-03
---

# Webhook event reference

Every event uses this envelope:

```json
{
  "id": "evt_b41c92e0",
  "type": "invoice.finalized",
  "created_at": "2026-04-03T00:00:04Z",
  "livemode": true,
  "data": {}
}
```

The event id stays the same across retries and across endpoints; each endpoint's delivery has its own
`Birchwell-Delivery-Id`.

## `invoice.finalized`

Sent when an invoice finalises, 48 hours after its period closes. `data` is the full invoice.

```json
{
  "type": "invoice.finalized",
  "data": {
    "id": "inv_5d02c7",
    "customer_id": "cus_a81f20",
    "period": "2026-03",
    "status": "finalized",
    "currency": "gbp",
    "subtotal_minor": 368440,
    "tax_minor": 73688,
    "total_minor": 442128,
    "amount_due_minor": 442128,
    "finalized_at": "2026-04-03T00:00:00Z"
  }
}
```

## `invoice.paid`

Sent once, when recorded payments bring `amount_due_minor` to zero.

```json
{
  "type": "invoice.paid",
  "data": {"id": "inv_5d02c7", "customer_id": "cus_a81f20", "status": "paid", "paid_at": "2026-04-12T09:30:11Z"}
}
```

## `usage.rejected`

Sent for each usage event Birchwell rejects, whether it failed checks on `POST /v1/usage/events` or arrived after its
period finalised.

```json
{
  "type": "usage.rejected",
  "data": {
    "code": "period_finalized",
    "message": "Period 2026-03 for cus_a81f20 finalised at 2026-04-03T00:00:00Z.",
    "event": {"customer_id": "cus_a81f20", "meter": "api_calls", "value": 12, "timestamp": "2026-03-31T22:10:00Z"}
  }
}
```

`data.code` is one of the per-event codes such as `unknown_meter`, `subject_required` or `period_finalized`. See
[Rejected events](rejected-events.md).

## Handling them

```python
def handle(event):
    kind = event["type"]
    if kind == "invoice.finalized":
        schedule_pdf_download(event["data"]["id"])
    elif kind == "invoice.paid":
        mark_paid(event["data"]["id"])
    elif kind == "usage.rejected":
        alert_metering(event["data"])
```

To check what an endpoint would receive, send a sample:

```bash
curl -X POST https://api.birchwell.io/v1/webhook_endpoints/we_7e21c4/test \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type": "usage.rejected"}'
```

These three are the only event types. Credit notes and payments do not have events of their own.
