---
title: Testing webhooks
updated: 2025-12-15
---

# Testing webhooks

You can exercise a receiver without waiting for a real month to close. Birchwell offers two tools: a sample sender
for any endpoint, and a test-mode clock that drives real invoices through finalisation.

## Send a sample event

`POST /v1/webhook_endpoints/{id}/test` delivers one event of the type you choose, with placeholder data, signed with the
endpoint's real secret:

```bash
curl -X POST https://api.birchwell.io/v1/webhook_endpoints/we_7e21c4/test \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type": "invoice.paid"}'
```

```python
import os
import requests

resp = requests.post(
    "https://api.birchwell.io/v1/webhook_endpoints/we_7e21c4/test",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    json={"type": "invoice.finalized"},
    timeout=10,
)
print(resp.json()["delivery_id"])
```

Samples follow the normal retry schedule. Return `500` from your receiver once on purpose and you will see the second
attempt five minutes later with `Birchwell-Delivery-Attempt: 2`.

## Drive a real invoice in test mode

With a `bw_test_` key:

1. Report a few events to a test customer with `POST /v1/usage/events`.
2. Call `POST /v1/test/advance_period` with `{"skip_grace": true}` to close the period and finalise at once.
3. Your test endpoint receives `invoice.finalized` for the new invoice.
4. Record a payment with `POST /v1/invoices/{id}/payments` to get `invoice.paid`.

```bash
curl -X POST https://api.birchwell.io/v1/test/advance_period \
  -H "Authorization: Bearer $BIRCHWELL_TEST_KEY" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cus_a81f20", "skip_grace": true}'
```

Without `skip_grace`, finalisation follows 48 hours after the period closes, as in live mode. With a live key the call
returns `403 insufficient_permissions`.

## Receiving on a laptop

Endpoints must be public HTTPS, so register the address of a tunnelling tool that forwards to your local port. Delete
the endpoint afterwards; it counts toward the limit of 10.

## Before going live

- Signature checked over the raw body, with the `sha256=` prefix.
- A 2xx answer inside 15 seconds.
- Repeated `Birchwell-Delivery-Id` values skipped.
- A separate live endpoint, created with a `bw_live_` key, with its own secret.
