---
title: Request ids and the request log
updated: 2025-12-01
---

# Request ids and the request log

Every response from `https://api.birchwell.io` carries a `Birchwell-Request-Id` header, for example
`Birchwell-Request-Id: req_6b2d0f91`. Error bodies repeat it as `error.request_id`.

That id is how we find a request in our systems. Log it on every call, and include it whenever you write to
api@birchwell.io about unexpected behaviour.

## Logging it

```python
import logging
import os
import requests

log = logging.getLogger("billing")

resp = requests.get(
    "https://api.birchwell.io/v1/invoices/inv_5d02c7",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=10,
)
log.info("birchwell %s %s", resp.status_code, resp.headers["Birchwell-Request-Id"])
```

```bash
curl -s -D - -o /dev/null https://api.birchwell.io/v1/invoices/inv_5d02c7 \
  -H "Authorization: Bearer $BIRCHWELL_KEY" | grep -i birchwell-request-id
```

## Request ids are not idempotency keys

`Birchwell-Request-Id` is created by Birchwell, one per request, and is only for tracing. It is unrelated to
deduplication. If you send an `X-Request-Id` header of your own, it is recorded in the request log for your
convenience, but it has had no effect on deduplication since 2025-04-07. Usage requests are deduplicated on the
`Idempotency-Key` header within 24 hours; see [Idempotency](idempotency.md).

A replayed usage request (same `Idempotency-Key` and body) gets a new `Birchwell-Request-Id` plus
`Idempotent-Replayed: true`, and its body names the original request id in `replayed_from`.

## The request log

The dashboard keeps 30 days of requests under **Developers**, then **Request log**: method, path, status, key name,
duration and both request ids. Bodies are kept for failed requests only. Filter by status code, by path or by key.

Common uses:

- Finding the `413 batch_too_large` responses a worker swallowed.
- Checking whether a usage batch was replayed, by filtering on `Idempotent-Replayed`.
- Confirming a credit note was attempted on a draft invoice (`409 invoice_not_finalized`).

The request log needs a dashboard role of developer or above.
