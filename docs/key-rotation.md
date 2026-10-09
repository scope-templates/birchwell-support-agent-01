---
title: Rotating API keys
updated: 2025-10-06
---

# Rotating API keys

Birchwell keys do not expire. Rotate them when someone with access leaves, when a key may have been exposed in logs or
a repository, and at least once a year.

Because each account can hold up to 20 active keys, old and new keys can run side by side. The order that avoids
downtime is: create, deploy, confirm, revoke.

## 1. Create

Under **Developers**, then **API keys**, create a key of the same mode and type. A `usage_only` live key is replaced
with a `usage_only` live key; changing type at the same time makes failures harder to read.

## 2. Deploy

Put the new key in your secret store and restart the services that read it. Usage workers often run as many replicas;
make sure every replica has restarted.

## 3. Confirm

Each key's row in the dashboard shows when it was last used. From a host, `GET /v1/whoami` shows which key is
configured:

```bash
curl -s https://api.birchwell.io/v1/whoami -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import os
import requests

me = requests.get(
    "https://api.birchwell.io/v1/whoami",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=10,
).json()
if me["key"]["last4"] != os.environ["BIRCHWELL_KEY"][-4:]:
    raise SystemExit("unexpected key")
```

Wait until the old key's last-used time stops advancing. Jobs that only run at the end of the month, such as a
reconciliation script, will not show up until they run, so check your schedulers.

## 4. Revoke

Revoke the old key. Requests still using it fail with `401 api_key_revoked` within a minute.

## A note on usage in flight

If a usage worker is retrying a failed `POST /v1/usage/events` when its key changes, it must keep the same
`Idempotency-Key` for the retry. The key used for deduplication is the header, not the API key, so a retry under the new
API key is still recognised as a repeat within 24 hours and is not counted twice.

## If a key has leaked

Revoke it first. A leaked `full` live key can read invoices and issue credit notes; the few minutes of failed requests
while you deploy a new key are the lesser problem.
