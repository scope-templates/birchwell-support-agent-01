---
title: Service status
updated: 2026-03-09
---

# Service status

Current health and past incidents are published at `status.birchwell.io`, split into components: Usage ingestion,
Invoicing, Webhooks, Dashboard and API. Subscribe there to receive incident notices by email.

## What an incident means for your data

Billing data must not be lost, so the components fail in a deliberate order:

- **Usage ingestion degraded.** `POST /v1/usage/events` may answer `503 service_unavailable` with `Retry-After`.
  Nothing in a 503 response was recorded. Retry with the same `Idempotency-Key`; deduplication within 24 hours makes
  that safe even if an earlier attempt did land.
- **Invoicing degraded.** Finalisation may run late. An invoice due to finalise 48 hours after its period closes will
  finalise as soon as invoicing recovers, and `invoice.finalized` is sent then. Late usage keeps being accepted until
  the invoice actually finalises.
- **Webhooks degraded.** Events queue up and are sent once delivery recovers. The retry schedule (8 retries over 24
  hours) starts at the first attempt, so an outage does not use up your retries.

## Health endpoint

`GET /v1/health` needs no key and is not rate limited:

```bash
curl https://api.birchwell.io/v1/health
```

```json
{"usage_ingestion": "ok", "invoicing": "ok", "webhooks": "ok"}
```

```python
import requests

health = requests.get("https://api.birchwell.io/v1/health", timeout=5).json()
if health["usage_ingestion"] != "ok":
    pause_usage_flush()
```

Pausing a usage worker while ingestion is degraded is optional; retries with backoff do the same job.

## Maintenance

Planned maintenance is announced at least 5 days ahead and runs between 02:00 and 04:00 UTC on a Saturday, never in
the first three days of a month, when finalisations are busiest.

## Uptime commitments

| Plan | Monthly uptime | Credits |
|---|---|---|
| Launch | 99.5% | No |
| Scale | 99.9% | Yes |
| Enterprise | 99.95% | Yes |

Uptime counts minutes in which `POST /v1/usage/events` and `GET /v1/invoices/{id}` succeed for valid requests.
