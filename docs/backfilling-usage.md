---
title: Backfilling usage
updated: 2025-12-08
---

# Backfilling usage

When you move an existing product onto Birchwell, or a worker was down for a few hours, you will need to send a large
amount of past usage at once. The same endpoint handles it: `POST /v1/usage/events`, up to 1,000 events per request.

## What can be backfilled

Only periods whose invoices have not finalised. In practice that means the current period, and the previous period
during the 48 hours after it closes. Usage from older periods is rejected with `period_finalized`. To bill historic
usage, add a manual line to the current draft invoice instead.

## A backfill loop

```python
import os
import time
import uuid
import requests

URL = "https://api.birchwell.io/v1/usage/events"
HEADERS = {"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"}

def backfill(events, run_id):
    for n, start in enumerate(range(0, len(events), 1000)):
        group = events[start:start + 1000]
        key = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}/{n}"))
        while True:
            resp = requests.post(URL, headers={**HEADERS, "Idempotency-Key": key},
                                 json={"events": group}, timeout=60)
            if resp.status_code == 429:
                time.sleep(int(resp.headers["Retry-After"]))
                continue
            resp.raise_for_status()
            break
```

The `Idempotency-Key` is derived from the run id and the group number, so if the script crashes and you start it again
with the same `run_id`, groups already sent within the last 24 hours are replayed instead of counted twice.

## Throughput

At 1,000 events per request and 1,200 requests per minute per key, the ceiling is well over a million events a minute.
Most backfills are limited by how fast you can read your own logs. One process sending one request at a time is usually
enough; if you run several, keep them on separate keys or watch `X-RateLimit-Remaining`.

## Check the result

```bash
curl "https://api.birchwell.io/v1/usage/summary?customer_id=cus_a81f20&meter=api_calls&period=2026-03" \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

Compare `quantity` with the total from your source. If they differ, look at the `errors` arrays you logged, or at the
`usage.rejected` webhooks for the run.

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `batch_empty` | `events` is an empty array |
| 413 | `batch_too_large` | More than 1,000 events |
| 422 | `idempotency_key_mismatch` | A key reused with a different body within 24 hours |

Try a backfill with a `bw_test_` key first; see [Test mode](test-mode.md).
