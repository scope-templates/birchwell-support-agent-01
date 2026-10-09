---
title: Birchwell Billing API overview
updated: 2026-08-04
---

# Birchwell Billing API overview

Birchwell Billing meters what your customers use and turns it into invoices. Your product reports usage events as
they happen; Birchwell aggregates them per meter and per billing period, prices them, and finalises an invoice for each
customer when the period is over.

Everything runs through one REST API:

```
https://api.birchwell.io/v1
```

Requests and responses are JSON. Every request is authenticated with an API key sent as a bearer token in the
`Authorization` header; see [Authentication](authentication.md).

## The objects

| Object | What it is | Page |
|---|---|---|
| Customer | One of your customers, with a fixed currency | [Customers](customers.md) |
| Meter | Something you charge for, with an aggregation of `sum`, `max` or `unique_count` | [Meters](meters.md) |
| Usage event | One measurement for one customer and one meter | [Usage events](usage-events.md) |
| Invoice | A customer's bill for one monthly period | [Invoices](invoices.md) |
| Credit note | A refund against a finalised invoice | [Credit notes](credit-notes.md) |

## The flow in one request each

```bash
curl -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Idempotency-Key: 6f1d2c0e-batch-0001" \
  -H "Content-Type: application/json" \
  -d '{"events": [{"customer_id": "cus_a81f20", "meter": "api_calls", "value": 1, "timestamp": "2026-03-04T10:15:00Z"}]}'
```

```python
import os
import requests

invoice = requests.get(
    "https://api.birchwell.io/v1/invoices/inv_5d02c7",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=10,
).json()
print(invoice["status"], invoice["total_minor"], invoice["currency"])
```

## Key limits

- 1,200 requests per minute per key.
- 1,000 events per `POST /v1/usage/events` request.
- Usage requests are deduplicated on the `Idempotency-Key` header within 24 hours.
- Invoices finalise 48 hours after the period closes.

Webhooks (`invoice.finalized`, `invoice.paid`, `usage.rejected`) tell your systems when those things happen. Start
with the [Python quickstart](quickstart-python.md) or the [Node quickstart](quickstart-node.md).
