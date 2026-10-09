---
title: Unique-count meters
updated: 2025-10-27
---

# Unique-count meters

A `unique_count` meter counts how many distinct `subject` values a customer sent during the period. It is the meter
for "monthly active users", "devices seen" or "workspaces with activity", where sending the same subject twice should
not cost twice.

## Sending events

Every event on a `unique_count` meter must carry a `subject`, a string of up to 128 characters. `value` is ignored and
may be left out.

```bash
curl -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Idempotency-Key: 5e2a9c40-login-0412" \
  -H "Content-Type: application/json" \
  -d '{"events": [{"customer_id": "cus_a81f20", "meter": "active_users", "subject": "user_93", "timestamp": "2026-04-12T07:41:00Z"}]}'
```

```python
import os
import requests

def record_active(customer_id, user_id, at):
    requests.post(
        "https://api.birchwell.io/v1/usage/events",
        headers={
            "Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}",
            "Idempotency-Key": f"active-{customer_id}-{user_id}-{at[:10]}",
        },
        json={"events": [{"customer_id": customer_id, "meter": "active_users",
                          "subject": user_id, "timestamp": at}]},
        timeout=10,
    ).raise_for_status()
```

Keying on the user and the day means a user's many logins in one day send at most one request that counts, while the
meter itself takes care of the same user on different days.

## What to use as the subject

Use a stable internal id, such as `user_93`, not an email address. Subjects appear on usage exports, and an id that
changes when a user edits their profile would be counted twice.

## Counting rules

- Subjects are compared exactly. `User_93` and `user_93` are two subjects.
- Distinct subjects are counted per customer per period. A user active in March and April counts once in each.
- Subjects are not shared between customers: the same `user_93` under two customers counts once for each.

## Errors

| Status | `error.code` | When |
|---|---|---|
| per event | `subject_required` | `subject` missing or empty |
| per event | `invalid_request` | `subject` longer than 128 characters |
| 413 | `batch_too_large` | More than 1,000 events in the request |

Rejected events are listed in the `errors` array with their `position` and also sent as `usage.rejected` webhooks.
The running count is available from [the usage summary](usage-summary.md).
