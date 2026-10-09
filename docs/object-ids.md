---
title: Object ids
updated: 2025-10-27
---

# Object ids

Birchwell ids are strings with a short prefix that names the object type. Store them as text of up to 40 characters
and compare them exactly; they are case sensitive.

| Prefix | Object | Example |
|---|---|---|
| `cus_` | Customer | `cus_a81f20` |
| `inv_` | Invoice | `inv_5d02c7` |
| `il_` | Invoice line | `il_0c3e71` |
| `cn_` | Credit note | `cn_19b4e0` |
| `pay_` | Payment | `pay_7f20d1` |
| `we_` | Webhook endpoint | `we_7e21c4` |
| `evt_` | Webhook event | `evt_b41c92e0` |
| `dlv_` | Webhook delivery | `dlv_9a03f5` |
| `req_` | Request | `req_6b2d0f91` |
| `bw_live_`, `bw_test_` | API key | `bw_live_3c9e5a10f27b48d6a1e0c4b2` |

Meters are the exception: they are addressed by the `key` you chose, such as `api_calls` or `active_users`, not by a
generated id.

## Your own ids

Customers can carry an `external_id`, your own account id, so you never need a lookup table:

```bash
curl "https://api.birchwell.io/v1/customers?external_id=acct_2291" \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

```python
import os
import requests

page = requests.get(
    "https://api.birchwell.io/v1/customers",
    params={"external_id": "acct_2291"},
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    timeout=10,
).json()
customer_id = page["data"][0]["id"] if page["data"] else None
```

`external_id` is unique per mode. Usage events, however, need the Birchwell `customer_id`; resolve it once and cache
it rather than looking it up for every event.

## Ids across modes

Test and live objects share the same prefixes. An id from test mode used with a live key is not found
(`404 customer_not_found`, `404 invoice_not_found` and so on), never silently matched to a live object.

## Validation

Do not parse ids or rely on their length. A cheap sanity check on input is the prefix:

```python
def looks_like_invoice(value: str) -> bool:
    return value.startswith("inv_") and len(value) <= 40
```
