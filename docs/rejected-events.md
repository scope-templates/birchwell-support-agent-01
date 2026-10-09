---
title: Rejected usage events
updated: 2026-05-19
---

# Rejected usage events

`POST /v1/usage/events` validates each event on its own. A batch with a few bad events is not refused as a whole: the
good events are accepted and the bad ones are reported in two places.

## 1. In the response

```json
{
  "accepted": 998,
  "rejected": 2,
  "errors": [
    {"position": 14, "code": "unknown_meter", "message": "No meter with key 'api_call'."},
    {"position": 611, "code": "subject_required", "message": "Meter 'active_users' needs a subject."}
  ]
}
```

`position` is the zero-based place of the event in the `events` array you sent. The status is still `202`.

## 2. As a `usage.rejected` webhook

Every rejected event also produces a `usage.rejected` event, so a worker that fires and forgets can still be noticed by
a separate service. The `data` holds the original event and the reason:

```json
{
  "id": "evt_b41c92e0",
  "type": "usage.rejected",
  "created_at": "2026-04-02T10:00:03Z",
  "livemode": true,
  "data": {
    "code": "period_finalized",
    "event": {"customer_id": "cus_a81f20", "meter": "api_calls", "value": 40, "timestamp": "2026-02-27T11:00:00Z"}
  }
}
```

## Reasons an event is rejected

| `code` | Fix |
|---|---|
| `unknown_meter` | Create the meter, or correct the key |
| `subject_required` | Add `subject` for `unique_count` meters |
| `period_finalized` | The period's invoice is final; bill it by hand next period |
| `customer_not_found` | Create the customer first |
| `meter_archived` | Send to the replacement meter |
| `invalid_request` | Negative `value`, bad timestamp, or more than 5 minutes in the future |

## Handling them in Python

```python
import os
import requests

resp = requests.post(
    "https://api.birchwell.io/v1/usage/events",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}", "Idempotency-Key": batch_id},
    json={"events": events},
    timeout=30,
)
body = resp.json()
for err in body["errors"]:
    dead_letter.put(events[err["position"]], reason=err["code"])
```

```bash
curl -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Idempotency-Key: 7d1b55e4-retry-check" \
  -H "Content-Type: application/json" \
  -d '{"events": [{"customer_id": "cus_a81f20", "meter": "api_call", "value": 1, "timestamp": "2026-04-02T09:00:00Z"}]}'
```

Do not resend a rejected event unchanged; it will be rejected again. Fix it and send it in a new request with a new
`Idempotency-Key`.
