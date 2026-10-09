---
title: HTTP clients, timeouts and retries
updated: 2026-02-23
---

# HTTP clients, timeouts and retries

Most Birchwell integrations in Python use `requests` directly. These are the settings that keep a client well behaved
under load and safe to retry.

## Timeouts

| Call | Typical | Client timeout |
|---|---|---|
| `POST /v1/usage/events` (1,000 events) | under 1 s | 15 s |
| Reads such as `GET /v1/invoices/{id}` | under 200 ms | 10 s |
| `GET /v1/invoices/{id}/pdf` | under 2 s | 30 s |

Always set a timeout. `requests` waits forever by default.

## What to retry

| Response | Retry? |
|---|---|
| `429 rate_limited` | Yes, after the `Retry-After` seconds |
| `500 internal_error`, `503 service_unavailable` | Yes, with backoff from 1 s, at most 4 tries |
| Timeout or connection error | Yes, with the same `Idempotency-Key` |
| Any other 4xx | No; fix the request |

The limit is 1,200 requests per minute per key. When a 429 arrives, honour `Retry-After` exactly; retrying sooner just
earns another 429.

## Retrying usage safely

`POST /v1/usage/events` dedupes on the `Idempotency-Key` header within 24 hours. Generate the key once per batch and
resend the **same** key on every retry of that batch. A new key on a retry turns a lost response into double-counted
usage.

```python
import os
import time
import uuid
import requests

session = requests.Session()
session.headers["Authorization"] = f"Bearer {os.environ['BIRCHWELL_KEY']}"

def send_batch(events):
    key = str(uuid.uuid4())
    for attempt in range(4):
        try:
            resp = session.post(
                "https://api.birchwell.io/v1/usage/events",
                headers={"Idempotency-Key": key},
                json={"events": events},
                timeout=15,
            )
        except requests.ConnectionError:
            time.sleep(2 ** attempt)
            continue
        if resp.status_code == 429:
            time.sleep(int(resp.headers["Retry-After"]))
            continue
        if resp.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        return resp
    raise RuntimeError("usage batch not accepted after 4 attempts")
```

A replayed request returns the original response with `Idempotent-Replayed: true`. Reusing a key with a different body
returns `422 idempotency_key_mismatch`.

## From a shell

```bash
curl --retry 3 --max-time 15 -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Idempotency-Key: nightly-2026-03-31-batch-07" \
  -H "Content-Type: application/json" \
  -d @batch-07.json
```

More on keys in [Idempotency](idempotency.md).
