---
title: Webhook endpoints
updated: 2025-11-17
---

# Webhook endpoints

An endpoint is an HTTPS URL plus the event types it should receive. Manage endpoints in the dashboard under
**Developers**, then **Webhooks**, or with the API below. Endpoints created with a `bw_test_` key receive only
test-mode events; those created with a `bw_live_` key receive only live ones.

## Create

```bash
curl -X POST https://api.birchwell.io/v1/webhook_endpoints \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://billing.example.com/birchwell/webhooks", "events": ["invoice.finalized", "invoice.paid"]}'
```

```json
{
  "id": "we_7e21c4",
  "url": "https://billing.example.com/birchwell/webhooks",
  "events": ["invoice.finalized", "invoice.paid"],
  "secret": "bwsec_8d41a07c2f95e3b6",
  "enabled": true,
  "livemode": true
}
```

`secret` appears only in this response and after a rotation.

## Manage

```python
import os
import requests

BASE = "https://api.birchwell.io/v1/webhook_endpoints"
H = {"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"}

requests.patch(f"{BASE}/we_7e21c4", headers=H,
               json={"events": ["invoice.finalized", "invoice.paid", "usage.rejected"]}, timeout=10)
endpoints = requests.get(BASE, headers=H, params={"limit": 20}, timeout=10).json()["data"]
requests.delete(f"{BASE}/we_7e21c4", headers=H, timeout=10)
```

`events` accepts any of `invoice.finalized`, `invoice.paid` and `usage.rejected`. Changes apply to events created
afterwards; deliveries already scheduled still go out.

## Rules

- HTTPS only, with a valid public certificate.
- Up to 10 endpoints per account.
- The endpoint must answer 2xx within 15 seconds.

## Automatic disabling

If every delivery to an endpoint fails for 5 consecutive days, Birchwell sets `"enabled": false` and emails the account
owners. Fix the receiver, re-enable with `PATCH` and `{"enabled": true}`, then replay what you missed from the
delivery log (deliveries stay replayable for 30 days).

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | Empty `events`, or an unknown event type |
| 403 | `insufficient_permissions` | A `usage_only` key |
| 404 | `webhook_endpoint_not_found` | Unknown id, or one from the other mode |
| 422 | `invalid_webhook_url` | Not HTTPS, or not a public host |
