---
title: Webhook signatures
updated: 2026-03-02
---

# Webhook signatures

Each delivery carries a `Birchwell-Signature` header so you can confirm it came from Birchwell and was not changed on
the way. Reject anything that fails the check.

## Format

```
Birchwell-Signature: sha256=<hex>
```

`<hex>` is the HMAC-SHA256 of the raw request body, keyed with your endpoint's signing secret (`bwsec_...`), written as
64 lowercase hex characters. The `sha256=` prefix is part of the header value.

Only the body is signed. No timestamp or other header is included, so compute the HMAC over exactly the bytes you
received.

## Verifying in Python

```python
import hashlib
import hmac
import os

SECRET = os.environ["BIRCHWELL_WEBHOOK_SECRET"].encode()

def verify(raw_body: bytes, header_value: str) -> bool:
    expected = "sha256=" + hmac.new(SECRET, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_value or "")
```

Use your framework's raw body accessor: `request.get_data()` in Flask, `await request.body()` in FastAPI,
`request.body` in Django. If you parse the JSON and dump it again, spacing and key order change and the check fails.

## Comparing by hand

```bash
printf 'sha256=%s\n' "$(openssl dgst -sha256 -hmac "$BIRCHWELL_WEBHOOK_SECRET" -hex < body.json | awk '{print $NF}')"
```

Compare the output with the header value saved from the delivery log.

## Rotating the secret

```bash
curl -X POST https://api.birchwell.io/v1/webhook_endpoints/we_7e21c4/rotate_secret \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import requests

new_secret = requests.post(
    "https://api.birchwell.io/v1/webhook_endpoints/we_7e21c4/rotate_secret",
    headers={"Authorization": f"Bearer {key}"},
    timeout=10,
).json()["secret"]
```

For 24 hours after a rotation every delivery also carries `Birchwell-Signature-Previous`, signed with the old secret.
Accept either header during that day, deploy the new secret, then stop checking the old one.

## When the check fails

Answer `401` and do nothing with the body. Birchwell counts it as a failed delivery and retries on the normal schedule,
so fixing a wrong secret within a few hours loses no events. A run of failures usually means a proxy rewrote or
re-encoded the body before it reached your code.
