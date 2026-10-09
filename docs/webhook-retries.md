---
title: Webhook retries
updated: 2026-07-27
---

# Webhook retries

A delivery succeeds when your endpoint answers with a 2xx status within 15 seconds. A 3xx, 4xx or 5xx response, a
timeout, a refused connection or a TLS error is a failure, and Birchwell tries again. Failed deliveries are retried 8
times over 24 hours.

## Schedule

| Attempt | `Birchwell-Delivery-Attempt` | Sent after the original attempt |
|---|---|---|
| Original | `1` | immediately |
| Retry 1 | `2` | 5 minutes |
| Retry 2 | `3` | 30 minutes |
| Retry 3 | `4` | 1 hour |
| Retry 4 | `5` | 2 hours |
| Retry 5 | `6` | 4 hours |
| Retry 6 | `7` | 8 hours |
| Retry 7 | `8` | 16 hours |
| Retry 8 | `9` | 24 hours |

Every retry carries the same body, the same `Birchwell-Delivery-Id` and a fresh `Birchwell-Signature` computed over that
same body. If the ninth attempt fails, the delivery is marked `failed`.

This schedule has applied since 2025-06-09. Before that date deliveries were retried 3 times over 1 hour; see the
[changelog](changelog.md).

## Replaying a failed delivery

Deliveries can be replayed for 30 days, from the dashboard (**Developers**, then **Webhooks**) or the API:

```bash
curl -X POST https://api.birchwell.io/v1/webhook_deliveries/dlv_9a03f5/replay \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import os
import requests

resp = requests.post(
    "https://api.birchwell.io/v1/webhook_deliveries/dlv_9a03f5/replay",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=10,
)
resp.raise_for_status()
```

A replay starts again at attempt `1` with the full schedule.

## Designing for retries

- **Answer first, work later.** Put the event on a queue and return `204`. Slow handlers are the most common cause of
  repeated deliveries.
- **Skip duplicates.** A delivery that succeeded on your side but timed out on ours will arrive again. Store handled
  `Birchwell-Delivery-Id` values for at least 25 hours.
- **Do not depend on order.** A retried `invoice.finalized` can arrive after `invoice.paid` for the same invoice. Fetch
  the invoice with `GET /v1/invoices/{id}` if the status matters.

If every delivery to an endpoint fails for 5 consecutive days, the endpoint is disabled; see
[Webhook endpoints](webhook-endpoints.md).
