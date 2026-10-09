---
title: Usage timestamps and late events
updated: 2026-02-17
---

# Usage timestamps and late events

Every usage event carries a `timestamp`, and that timestamp, not the time Birchwell receives the event, decides which
billing period it counts toward. Periods are calendar months in UTC, named like `2026-03`.

## Format

Send ISO 8601 in UTC with a `Z` suffix: `2026-03-14T09:30:00Z`. Offsets such as `+01:00` are accepted and converted, but
UTC avoids surprises around the month boundary, where a Paris timestamp of 00:30 on 1 April still belongs to March.

## How late can an event be?

A period closes at 00:00 UTC on the first of the next month. Its invoice finalises 48 hours later. Until then, events
for the closed period are still accepted and the draft invoice is recomputed to include them.

| Event timestamp falls in | Accepted? |
|---|---|
| The current period | Yes |
| A closed period whose invoice is still `draft` | Yes, within the 48-hour window |
| A period whose invoice is `finalized` | No: `period_finalized` |
| More than 5 minutes in the future | No: `invalid_request` |

For March 2026: the period closes at `2026-04-01T00:00:00Z` and finalises at `2026-04-03T00:00:00Z`. An event stamped
`2026-03-31T23:58:00Z` and sent at `2026-04-02T10:00:00Z` still counts toward March.

## Example

```bash
curl -X POST https://api.birchwell.io/v1/usage/events \
  -H "Authorization: Bearer $BIRCHWELL_KEY" \
  -H "Idempotency-Key: 0f6c1d2e-late-march-batch" \
  -H "Content-Type: application/json" \
  -d '{"events": [{"customer_id": "cus_a81f20", "meter": "api_calls", "value": 40, "timestamp": "2026-03-31T23:58:00Z"}]}'
```

```python
import datetime as dt
import os
import requests

stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
resp = requests.post(
    "https://api.birchwell.io/v1/usage/events",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    json={"events": [{"customer_id": "cus_a81f20", "meter": "api_calls", "value": 1, "timestamp": stamp}]},
    timeout=10,
)
```

## When an event is too late

A late event is not an error for the whole request. The response is still `202`; the event is listed in `errors` with
`"code": "period_finalized"` and a `usage.rejected` webhook is sent. Usage that missed a finalised invoice can only be
billed by a manual line on the next period's draft (see [Invoice lines](invoice-lines.md)), or refunded with a
[credit note](credit-notes.md) if it was over-counted.

Stamp events with the time the usage happened, from the clock of the machine that saw it, and keep those clocks synced.
