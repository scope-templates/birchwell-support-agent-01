---
title: Versioning
updated: 2025-09-15
---

# Versioning

The API version is in the path: `https://api.birchwell.io/v1/...`. v1 is the only version and there is no date-based
version header to pin.

## What may change within v1

We may, without notice:

- add endpoints, optional parameters and response fields;
- add values to fields documented as open-ended, such as error `message` text;
- raise limits, as on 2025-05-12 when the usage batch size went from 250 to 1,000 events.

We announce in the [changelog](changelog.md), and email account owners about, changes that need you to act. Two
examples from 2025:

- **2025-04-07.** Usage deduplication moved to the `Idempotency-Key` header, with a 24-hour window. Integrations that
  relied on `X-Request-Id` for deduplication had to add the new header.
- **2025-06-09.** Webhook deliveries began to be retried 8 times over 24 hours instead of 3 times over 1 hour, and two
  new event types appeared. Receivers that answered non-2xx for unknown types started seeing more retries.

## What will not change within v1

- Field names and types in responses.
- The meaning of an existing error `code`.
- The webhook event types an endpoint receives; it only gets the types listed in its own `events`.
- The 48-hour finalisation delay after a period closes.

## Writing tolerant clients

Ignore unknown response fields and unknown webhook event types. In Python, read with `.get()` where a field is
optional, and avoid strict schemas that reject extras:

```python
event = request.get_json()
handler = HANDLERS.get(event["type"])
if handler is not None:
    handler(event["data"])
return "", 200
```

Check the version you are calling in one place:

```python
import requests

API = "https://api.birchwell.io/v1"
r = requests.get(f"{API}/whoami", headers={"Authorization": f"Bearer {key}"}, timeout=10)
```

```bash
curl https://api.birchwell.io/v1/whoami -H "Authorization: Bearer $BIRCHWELL_KEY"
```

If a v2 is ever released, v1 will keep working for at least 12 months afterwards.
