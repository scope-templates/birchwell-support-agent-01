---
title: Reporting usage from background workers
updated: 2026-05-18
---

# Reporting usage from background workers

Most products report usage from a queue consumer or a scheduled job rather than from the request path. That keeps
billing out of your latency budget and survives Birchwell being briefly unreachable. This page puts the pieces
together.

## Shape of a reliable worker

1. Your app writes a usage record to its own queue or table as the work happens.
2. A worker reads up to 1,000 records, gives the group an `Idempotency-Key` derived from the records (for example the
   first and last queue offsets) and stores it with them.
3. The worker calls `POST /v1/usage/events` with a `usage_only` key.
4. On `202`, it marks the records sent. On a timeout, `429` or `5xx`, it retries with the **same** key.
5. Rejected events from the `errors` array go to a dead-letter table for someone to look at.

```python
import os
import requests

session = requests.Session()
session.headers["Authorization"] = f"Bearer {os.environ['BIRCHWELL_USAGE_KEY']}"

def report(records):
    key = f"usage:{records[0].offset}-{records[-1].offset}"
    resp = session.post(
        "https://api.birchwell.io/v1/usage/events",
        headers={"Idempotency-Key": key},
        json={"events": [r.as_event() for r in records]},
        timeout=15,
    )
    if resp.status_code == 202:
        body = resp.json()
        for err in body["errors"]:
            dead_letter(records[err["position"]], err["code"])
        mark_sent(records)
    elif resp.status_code == 429:
        raise Retry(after=int(resp.headers["Retry-After"]))
    else:
        resp.raise_for_status()
```

Deriving the key from offsets means a worker that crashes and restarts sends the same key for the same records, and
Birchwell dedupes them within 24 hours.

## Testing from a shell

```bash
curl -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_USAGE_KEY" \
  -H "Idempotency-Key: usage:918200-918273" \
  -H "Content-Type: application/json" \
  -d '{"events": [{"customer_id": "cus_a81f20", "meter": "storage_gb_hours", "value": 3.5, "timestamp": "2026-03-04T11:00:00Z"}]}'
```

## Many workers, one key

Workers sharing a key share its 1,200 requests per minute. With full batches that is rarely the constraint; if it is,
give each worker pool its own `usage_only` key. Workers should never coordinate idempotency keys with each other, since
each owns distinct records.

## Late and stuck records

Events for a closed period are still accepted until that period's invoice finalises, 48 hours after the close. Records
stuck longer than that will come back as `period_finalized` and fire `usage.rejected`. Alert on dead-letter growth
during the first two days of each month; that is the window in which a stuck worker still costs nothing to fix.
