---
title: Changelog
updated: 2026-09-14
---

# Changelog

Changes to the Birchwell Billing API, newest first.

## 2026-09-14

- The request log under **Developers** shows the `Idempotent-Replayed` header and can be filtered on it.

## 2026-05-18

- `GET /v1/whoami` reports the key's type (`full` or `usage_only`) and the last four characters of the key.

## 2026-05-11

- Invoice PDFs format numbers by the invoice currency: `eur` invoices print `1.234,56 €`, `gbp` invoices `£1,234.56`.

## 2026-01-20

- New key type `usage_only`, limited to `POST /v1/usage/events` and `GET /v1/usage/summary`. Other calls return
  `403 insufficient_permissions`.

## 2025-10-06

- Test mode: `POST /v1/test/advance_period` accepts `{"skip_grace": true}` to finalise a test invoice without the
  48-hour wait.

## 2025-06-09

- Webhook deliveries are retried 8 times over 24 hours (5 minutes, 30 minutes, 1, 2, 4, 8, 16 and 24 hours after the
  original attempt). Previously they were retried 3 times over 1 hour.
- New webhook events `invoice.finalized` and `usage.rejected`, alongside `invoice.paid`.
- Every delivery is signed in the `Birchwell-Signature` header. See [Webhook signatures](webhook-signatures.md).

## 2025-05-12

- `POST /v1/usage/events` accepts up to 1,000 events per request, up from 250. Larger requests return
  `413 batch_too_large`.

## 2025-04-07

- `POST /v1/usage/events` dedupes on the `Idempotency-Key` header within 24 hours. `X-Request-Id` is no longer used
  for deduplication.

```bash
curl -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Idempotency-Key: 6f1d2c0e-batch-0001" \
  -H "Content-Type: application/json" -d @batch.json
```

```python
requests.post("https://api.birchwell.io/v1/usage/events",
              headers={"Authorization": f"Bearer {key}", "Idempotency-Key": batch_key},
              json={"events": events}, timeout=15)
```

## 2025-03-17

- Meters support three aggregations: `sum`, `max` and `unique_count`. Previously every meter summed its events.
- Usage events accept a `subject` field, required for `unique_count` meters.
