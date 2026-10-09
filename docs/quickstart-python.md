---
title: Quickstart for Python
updated: 2026-06-08
---

# Quickstart for Python

Birchwell does not publish a Python package; the HTTP API is small enough that `requests` covers it. In about fifteen
minutes this guide creates a customer and a meter, reports usage, and reads the draft invoice, all in test mode.

## 1. A test key

In the dashboard open **Developers**, then **API keys**, and create a `full` test key. It starts `bw_test_`.

```bash
export BIRCHWELL_KEY=bw_test_7a41c0e9d25b36f8c1e04a9d
pip install requests
```

## 2. A session with auth

```python
import os
import uuid
import requests

API = "https://api.birchwell.io/v1"
s = requests.Session()
s.headers["Authorization"] = f"Bearer {os.environ['BIRCHWELL_KEY']}"
```

## 3. Customer and meter

```python
customer = s.post(f"{API}/customers", json={
    "name": "Fenmore Analytics", "email": "billing@fenmore.example",
    "currency": "gbp", "external_id": "acct_2291",
}, timeout=10).json()

s.post(f"{API}/meters", json={
    "key": "api_calls", "name": "API calls", "aggregation": "sum", "unit": "call",
}, timeout=10)
```

`aggregation` is one of `sum`, `max` or `unique_count`; see [Aggregation](aggregation.md).

## 4. Report usage

```python
resp = s.post(
    f"{API}/usage/events",
    headers={"Idempotency-Key": str(uuid.uuid4())},
    json={"events": [
        {"customer_id": customer["id"], "meter": "api_calls", "value": 250,
         "timestamp": "2026-03-04T10:15:00Z"},
    ]},
    timeout=15,
)
print(resp.status_code, resp.json())   # 202 {'accepted': 1, 'rejected': 0, 'errors': []}
```

Up to 1,000 events fit in one request. Keep the `Idempotency-Key` if you retry: requests are deduplicated on it within
24 hours.

## 5. Read the draft invoice

```python
invoices = s.get(f"{API}/invoices", params={"customer_id": customer["id"]}, timeout=10).json()["data"]
draft = invoices[0]
print(draft["status"], draft["period"], draft["total_minor"])
```

The same call from a shell:

```bash
curl "https://api.birchwell.io/v1/invoices?customer_id=cus_a81f20" \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

The invoice stays `draft` until 48 hours after the period closes, then finalises.

## Errors you may hit

| Status | `error.code` | Fix |
|---|---|---|
| 401 | `missing_authorization` | Header must read `Bearer bw_test_...` |
| 422 | `unknown_meter` (in `errors`) | Create the meter first |
| 409 | `meter_key_taken` | The meter already exists; reuse it |

Next: [webhooks](webhooks.md), so your app hears when invoices finalise.
