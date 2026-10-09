---
title: Pagination
updated: 2025-09-30
---

# Pagination

List endpoints such as `GET /v1/invoices`, `GET /v1/customers`, `GET /v1/meters`, `GET /v1/audit_log` and
`GET /v1/invoices/{id}/credit_notes` return one page at a time.

| Parameter | Default | Maximum |
|---|---|---|
| `limit` | 20 | 100 |
| `cursor` | first page | |

The response wraps the page in `data` and gives you `next_cursor`, which is `null` on the last page:

```json
{
  "data": [
    {"id": "inv_5d02c7", "customer_id": "cus_a81f20", "period": "2026-03", "status": "finalized"}
  ],
  "next_cursor": "cur_Zm9vYmFyMjAyNi0wMw"
}
```

Lists are newest first. The cursor pins the position, so objects created while you page do not cause repeats or gaps.

## Exporting every invoice for a customer

```python
import os
import requests

def invoices_for(customer_id):
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {os.environ['BIRCHWELL_KEY']}"
    params = {"customer_id": customer_id, "limit": 100}
    while True:
        page = s.get("https://api.birchwell.io/v1/invoices", params=params, timeout=10).json()
        yield from page["data"]
        if page["next_cursor"] is None:
            break
        params["cursor"] = page["next_cursor"]
```

```bash
curl "https://api.birchwell.io/v1/invoices?customer_id=cus_a81f20&limit=100" \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

## Filters

Filters are ordinary query parameters and must be the same on every page of one walk. Common ones:

- `GET /v1/invoices`: `customer_id`, `status`, `period`
- `GET /v1/customers`: `external_id`
- `GET /v1/meters`: `status` (`active` or `archived`)

## Errors

| Status | `error.code` | When |
|---|---|---|
| 400 | `invalid_request` | `limit` above 100, a malformed cursor, or filters changed mid-walk |

Cursors stay valid for 30 minutes. A page request counts as one request against the 1,200 requests per minute limit,
so a 10,000-invoice export at `limit=100` costs 100 requests.
