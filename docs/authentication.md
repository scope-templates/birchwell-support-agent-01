---
title: Authentication
updated: 2026-01-20
---

# Authentication

Birchwell authenticates every request with an API key passed as a bearer token:

```
Authorization: Bearer bw_live_...
Authorization: Bearer bw_test_...
```

The prefix of the key decides the mode. `bw_live_` keys act on real customers and real invoices; `bw_test_` keys act
on a separate set of test objects on the same host. Both are created in the dashboard under **Developers**, then
**API keys**.

## Examples

```bash
curl https://api.birchwell.io/v1/customers/cus_a81f20 \
  -H "Authorization: Bearer bw_test_7a41c0e9d25b36f8c1e04a9d"
```

```python
import os
import requests

session = requests.Session()
session.headers["Authorization"] = f"Bearer {os.environ['BIRCHWELL_KEY']}"

customer = session.get("https://api.birchwell.io/v1/customers/cus_a81f20", timeout=10).json()
```

Keys never go in the URL or the body. A `?api_key=` parameter is ignored, and the request fails as if no key had been
sent.

## Failures

| Status | `error.code` | Cause |
|---|---|---|
| 401 | `missing_authorization` | No `Authorization` header, or a scheme other than `Bearer` |
| 401 | `invalid_api_key` | The token is not a Birchwell key |
| 401 | `api_key_revoked` | The key was revoked |
| 403 | `insufficient_permissions` | A `usage_only` key called something other than usage endpoints |

A common slip is sending `Authorization: bw_live_...` without the word `Bearer`. That returns
`missing_authorization`, not `invalid_api_key`, because the scheme is checked first.

## Key types

Keys are either `full` or `usage_only`. A `usage_only` key may call `POST /v1/usage/events` and
`GET /v1/usage/summary` and nothing else. Give workers that only report usage a `usage_only` key so a leak cannot
issue credit notes or read invoices. See [API keys](api-keys.md).

## Where to call from

Call Birchwell from your servers and background workers. Never ship a key to a browser or mobile app; anyone with a
`full` live key can read every customer's invoices.
