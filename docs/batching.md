---
title: Batching usage events
updated: 2026-02-16
---

# Batching usage events

`POST /v1/usage/events` takes up to **1,000 events per request**. Batching is the single biggest lever on throughput:
at 1,200 requests per minute per key, full batches let one key report up to 1.2 million events a minute.

The limit was raised from 250 to 1,000 on 2025-05-12. A request with more than 1,000 events is rejected whole with
`413 batch_too_large`; none of its events are recorded, so you can safely split it and send it again.

## Building batches

Collect events in memory or in your queue and flush when either limit is reached: 1,000 events, or a time limit such
as 5 seconds, whichever comes first. The time limit keeps usage fresh on quiet days.

```python
import os
import time
import uuid
import requests

MAX_EVENTS = 1000
MAX_WAIT_S = 5

class UsageBuffer:
    def __init__(self):
        self.events, self.started = [], time.monotonic()

    def add(self, event):
        self.events.append(event)
        if len(self.events) >= MAX_EVENTS or time.monotonic() - self.started > MAX_WAIT_S:
            self.flush()

    def flush(self):
        if not self.events:
            return
        requests.post(
            "https://api.birchwell.io/v1/usage/events",
            headers={
                "Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}",
                "Idempotency-Key": str(uuid.uuid4()),
            },
            json={"events": self.events[:MAX_EVENTS]},
            timeout=15,
        ).raise_for_status()
        self.events, self.started = self.events[MAX_EVENTS:], time.monotonic()
```

(For production, keep the `Idempotency-Key` with the batch so a retry reuses it; see [Idempotency](idempotency.md).)

```bash
jq -c '{events: .[0:1000]}' usage.json > batch.json
curl -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Idempotency-Key: import-2026-03-part-001" \
  -H "Content-Type: application/json" -d @batch.json
```

## Partial success

A batch is not all-or-nothing once it passes the size check. Valid events are recorded and invalid ones are listed in
`errors` by `position`, so a single event with an unknown meter does not lose the other 999.

## Other limits

| Limit | Value |
|---|---|
| Request body | 2 MB |
| Events per request | 1,000 |
| Customers per request | Any mix |
| `properties` per event | 20 keys |

Batches may mix customers and meters freely. Ordering inside a batch does not matter; aggregation depends only on each
event's `timestamp`.
