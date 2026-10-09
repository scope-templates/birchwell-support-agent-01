---
title: Rate limits
updated: 2026-04-13
---

# Rate limits

The limit is **1,200 requests per minute per key**. It belongs to the key, not to the account or the calling
IP, and covers every endpoint together.

A usage request counts once however many events it carries. With batches of up to 1,000 events, a single key can
report far more usage than any one product needs; the limit mostly matters for code that sends one event per request
or that polls invoices in a loop.

## Headers

Every response carries:

| Header | Example |
|---|---|
| `X-RateLimit-Limit` | `1200` |
| `X-RateLimit-Remaining` | `1187` |
| `X-RateLimit-Reset` | `1775117520` (Unix seconds) |

## Over the limit

```
HTTP/1.1 429 Too Many Requests
Retry-After: 4
X-RateLimit-Limit: 1200
X-RateLimit-Remaining: 0

{"error": {"code": "rate_limited", "message": "1,200 requests per minute exceeded for this key.", "request_id": "req_6b2d0f91"}}
```

Wait the number of seconds in `Retry-After` and send the request again. For usage requests, send it with the same
`Idempotency-Key`; a 429 means nothing was recorded, but reusing the key costs nothing and protects you if an earlier
attempt did get through.

```python
import time
import requests

def call(session, method, url, **kw):
    for _ in range(6):
        resp = session.request(method, url, timeout=15, **kw)
        if resp.status_code != 429:
            return resp
        time.sleep(int(resp.headers.get("Retry-After", "1")))
    return resp
```

```bash
curl -s -D - -o /dev/null https://api.birchwell.io/v1/invoices?limit=1 \
  -H "Authorization: Bearer $BIRCHWELL_KEY" | grep -i -E "ratelimit|retry-after"
```

## Staying under it

- Batch usage events, up to 1,000 per request.
- Subscribe to `invoice.finalized` and `invoice.paid` webhooks instead of polling invoice status.
- Give separate services separate keys. Each key gets its own 1,200 per minute.
- Use `limit=100` when listing, so exports take fewer pages.

## Other limits

| Limit | Value | Error |
|---|---|---|
| Events per usage request | 1,000 | `413 batch_too_large` |
| Request body | 2 MB | `400 invalid_request` |
| Active meters | 50 | `400 invalid_request` |
| Webhook endpoints | 10 | `400 invalid_request` |
| List page size | 100 | `400 invalid_request` |

Live and test keys have the same limits.
