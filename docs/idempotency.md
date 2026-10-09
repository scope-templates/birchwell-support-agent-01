---
title: Idempotency
updated: 2026-07-28
---

# Idempotency

Networks fail after the server has done the work. If your worker sends a batch of usage, the connection drops, and the
worker sends it again, you must not bill the customer twice. Birchwell prevents that with the `Idempotency-Key` header.

**`POST /v1/usage/events` dedupes on the `Idempotency-Key` header within 24 hours.** The first request with a given key
is processed. Any repeat with the same key and the same body during the next 24 hours is not processed again; it gets
the original response back, with the header `Idempotent-Replayed: true`.

Deduplication has worked this way since 2025-04-07. Before that date the API deduplicated on `X-Request-Id`. That header
now has no effect on deduplication: two requests with the same `X-Request-Id` and different `Idempotency-Key` values
(or none) are both counted.

## Choosing keys

- Generate the key once per logical batch, before the first attempt, and reuse it for every retry of that batch.
- Use a UUID, or a stable id from your own system such as `worker-7:offset-918273`. Keys are up to 255 characters.
- Never reuse a key for different usage. A repeat with a different body within 24 hours fails with
  `422 idempotency_key_mismatch` and nothing in it is recorded.

```python
import os
import time
import uuid
import requests

def send_batch(events, attempts=5):
    key = str(uuid.uuid4())
    for _ in range(attempts):
        try:
            resp = requests.post(
                "https://api.birchwell.io/v1/usage/events",
                headers={
                    "Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}",
                    "Idempotency-Key": key,
                },
                json={"events": events},
                timeout=15,
            )
        except requests.ConnectionError:
            continue
        if resp.status_code == 429:
            time.sleep(int(resp.headers.get("Retry-After", "1")))
            continue
        if resp.status_code < 500:
            return resp
    raise RuntimeError("usage batch not delivered")
```

```bash
curl -i -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Idempotency-Key: worker-7:offset-918273" \
  -H "Content-Type: application/json" \
  -d @batch.json
# a repeat within 24 hours answers with: Idempotent-Replayed: true
```

## Why was my second event dropped as a duplicate?

Almost always because two different batches were sent with the same `Idempotency-Key` and the same body inside 24
hours, for example a worker that derives the key from the minute rather than from the batch. The second request was
answered from the first one's response and its events were never recorded. Derive the key from something unique to the
batch.

## After 24 hours

Keys are forgotten after 24 hours. A retry sent later than that is processed as new usage, so do not keep retrying the
same batch for days; route long failures to a dead-letter queue and reconcile them with
[usage summaries](usage-summary.md).
