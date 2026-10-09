---
title: Webhooks
updated: 2026-07-27
---

# Webhooks

Birchwell sends webhooks so your systems hear about billing changes without polling. There are three event types:

| Event | Sent when |
|---|---|
| `invoice.finalized` | An invoice finalises, 48 hours after its period closes |
| `invoice.paid` | Recorded payments cover the amount due |
| `usage.rejected` | A usage event is rejected, whether at intake or for `period_finalized` |

Each delivery is an HTTPS `POST` with a JSON body and these headers:

| Header | Example |
|---|---|
| `Birchwell-Signature` | `sha256=4b1e...9c` |
| `Birchwell-Event-Type` | `invoice.finalized` |
| `Birchwell-Delivery-Id` | `dlv_9a03f5` |
| `Birchwell-Delivery-Attempt` | `1` |

Always verify `Birchwell-Signature` before trusting the body; see [Webhook signatures](webhook-signatures.md).

## Registering an endpoint

```bash
curl -X POST https://api.birchwell.io/v1/webhook_endpoints \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://billing.example.com/birchwell/webhooks", "events": ["invoice.finalized", "invoice.paid", "usage.rejected"]}'
```

The response includes the signing secret, which starts `bwsec_`. Store it at once. More in
[Webhook endpoints](webhook-endpoints.md).

## A receiver in Python

```python
import hashlib
import hmac
import os
from flask import Flask, abort, request

app = Flask(__name__)
SECRET = os.environ["BIRCHWELL_WEBHOOK_SECRET"].encode()

@app.post("/birchwell/webhooks")
def birchwell_webhook():
    digest = hmac.new(SECRET, request.get_data(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(f"sha256={digest}", request.headers.get("Birchwell-Signature", "")):
        abort(401)
    queue.put(request.get_json())
    return "", 204
```

## Delivery and retries

Answer with any 2xx within 15 seconds. Anything else counts as a failure, and the delivery is retried 8 times over 24
hours, at 5 minutes, 30 minutes, 1, 2, 4, 8, 16 and 24 hours after the original attempt. The full table and replay
rules are on [Webhook retries](webhook-retries.md).

Deliveries are at least once and may arrive out of order. Keep the `Birchwell-Delivery-Id` values you have handled for
a few days and skip repeats.

## Limits

Up to 10 endpoints per account. Endpoints must use HTTPS; anything else is refused with `422 invalid_webhook_url`.
Test-mode and live-mode endpoints are separate; events carry `livemode` so you can tell them apart.
