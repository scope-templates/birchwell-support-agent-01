---
title: Test mode
updated: 2026-03-02
---

# Test mode

Every Birchwell account has a test mode. Requests made with a `bw_test_` key read and write test objects only:
test customers, test meters, test invoices. Nothing in test mode is ever emailed to a customer or counted toward your
Birchwell bill.

Test mode uses the same host, `https://api.birchwell.io`, and the same endpoints, limits and error codes as live mode.
Code that works against a test key works against a live key once the key is swapped.

## Telling the modes apart

Every object carries `livemode` (`true` or `false`), and so does every webhook event:

```python
import os
import requests

inv = requests.get(
    "https://api.birchwell.io/v1/invoices/inv_5d02c7",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=10,
).json()
assert inv["livemode"] is False
```

Objects never cross modes. A live key asking for a test invoice gets `404 invoice_not_found`.

## Moving the clock

Billing is about time, and waiting a month to see an invoice finalise is not practical. In test mode only,
`POST /v1/test/advance_period` closes a customer's current period immediately:

```bash
curl -X POST https://api.birchwell.io/v1/test/advance_period \
  -H "Authorization: Bearer $BIRCHWELL_TEST_KEY" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cus_a81f20"}'
```

The invoice then finalises 48 hours later, as in live mode. To skip the wait, send `{"skip_grace": true}` as well and
the invoice finalises straight away, firing `invoice.finalized` to your test webhook endpoints. With a live key, the
endpoint returns `403 insufficient_permissions`.

## What to test before going live

| Scenario | How |
|---|---|
| Duplicate usage is dropped | Send the same body twice with the same `Idempotency-Key` |
| Oversized batch | Send 1,001 events and expect `413 batch_too_large` |
| Late event after finalisation | Advance with `skip_grace`, then send an event for the old period |
| Credit note on a draft | Expect `409 invoice_not_finalized` |
| Webhook signatures | Use `POST /v1/webhook_endpoints/{id}/test` |

Test data is kept until you delete it from **Developers**, then **Test data**.
