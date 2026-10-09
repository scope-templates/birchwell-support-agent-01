---
title: API keys
updated: 2025-11-17
---

# API keys

Keys are managed in the dashboard under **Developers**, then **API keys**. Only account owners and admins can create
or revoke them (see [Team roles](team-roles.md)).

## Format

```
bw_live_3c9e5a10f27b48d6a1e0c4b2
bw_test_7a41c0e9d25b36f8c1e04a9d
```

A prefix of `bw_live_` or `bw_test_` followed by 24 lowercase hex characters. Anything else is rejected with
`401 invalid_api_key` before the request is looked at.

## Choosing a type

| Type | Can call | Use it for |
|---|---|---|
| `full` | Every endpoint | Your billing backend, admin tools |
| `usage_only` | `POST /v1/usage/events`, `GET /v1/usage/summary` | Workers and services that report usage |

Most integrations have one `full` key on the billing service and a `usage_only` key per service that emits usage.
Other calls with a `usage_only` key fail with `403 insufficient_permissions`.

## Creating a key

Choose **Create key**, pick live or test, pick the type and name it after the service that will use it. The key is
shown once. Store it in your secret manager immediately; afterwards the dashboard only shows the last four characters.

## Checking which key a service is using

`GET /v1/whoami` works with either key type and does not count toward any quota other than the rate limit:

```bash
curl https://api.birchwell.io/v1/whoami -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import os
import requests

me = requests.get(
    "https://api.birchwell.io/v1/whoami",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=10,
).json()
print(me["key"]["name"], me["key"]["type"], me["livemode"])
```

```json
{
  "account_id": "bwacc_0193",
  "livemode": true,
  "key": {"name": "metering-worker", "type": "usage_only", "last4": "c4b2"}
}
```

## Limits

- Up to 20 active keys per account, live and test combined.
- Each key has its own rate limit of 1,200 requests per minute.
- Revoked keys stop working within a minute and return `401 api_key_revoked`. Revocation cannot be undone; see
  [Rotating API keys](key-rotation.md) for the order of steps.
