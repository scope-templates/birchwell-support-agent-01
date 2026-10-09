---
title: Usage events
updated: 2026-07-28
---

# Usage events

A usage event says that a customer used a metered thing: one API call, 3.5 GB-hours of storage, one active user. You
send events to `POST /v1/usage/events`, and Birchwell aggregates them onto the customer's draft invoice for the period
the event's `timestamp` falls in.

## Request

```
POST https://api.birchwell.io/v1/usage/events
Authorization: Bearer bw_live_...
Idempotency-Key: <unique per request>
Content-Type: application/json
```

The body is always an `events` array of 1 to 1,000 events, even for a single event.

| Field | Type | Required | Notes |
|---|---|---|---|
| `customer_id` | string | yes | e.g. `cus_a81f20` |
| `meter` | string | yes | A meter key such as `api_calls` |
| `value` | number | yes, except `unique_count` meters | 0 or more |
| `timestamp` | string | yes | ISO 8601 UTC; at most 5 minutes in the future |
| `subject` | string | for `unique_count` meters | What is being counted, such as a user id |
| `properties` | object | no | Up to 20 keys, kept for your own reporting |

```bash
curl -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Idempotency-Key: 0b8f6a4e-7d1c-4c55-9a1e-2f3b8d61c0aa" \
  -H "Content-Type: application/json" \
  -d '{"events": [
        {"customer_id": "cus_a81f20", "meter": "api_calls", "value": 42, "timestamp": "2026-03-04T10:15:00Z"},
        {"customer_id": "cus_a81f20", "meter": "active_users", "subject": "user_93", "timestamp": "2026-03-04T10:15:02Z"}
      ]}'
```

```python
import os
import uuid
import requests

resp = requests.post(
    "https://api.birchwell.io/v1/usage/events",
    headers={
        "Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}",
        "Idempotency-Key": str(uuid.uuid4()),
    },
    json={"events": events},
    timeout=15,
)
```

## Response

`202 Accepted`, with a count of accepted and rejected events:

```json
{"accepted": 2, "rejected": 0, "errors": []}
```

Each rejected event appears in `errors` with its `position` in your array and a `code` (`unknown_meter`,
`subject_required`, `period_finalized`, `invalid_request`), and also triggers a `usage.rejected` webhook. Accepted
events in the same request are kept. See [Rejected events](rejected-events.md).

## Duplicates

`POST /v1/usage/events` dedupes on the `Idempotency-Key` header within 24 hours. Send the same key when you retry a
request; send a new key for new usage. Details on [Idempotency](idempotency.md).

## Request-level errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `batch_empty` | `events` is missing or empty |
| 413 | `batch_too_large` | More than 1,000 events |
| 422 | `idempotency_key_mismatch` | Key reused within 24 hours with a different body |
| 429 | `rate_limited` | Over 1,200 requests per minute |
