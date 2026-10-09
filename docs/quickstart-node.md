---
title: Quickstart for Node.js
updated: 2026-06-08
---

# Quickstart for Node.js

This guide reports usage from Node.js 18 or later. It uses the official `@birchwell/node` package; a plain `fetch`
version of each call is shown too, so you can see what goes over the wire.

```bash
npm install @birchwell/node
export BIRCHWELL_KEY=bw_test_7a41c0e9d25b36f8c1e04a9d
```

Create the test key under **Developers**, then **API keys** in the dashboard.

## Report usage with the package

```js
import { Birchwell } from "@birchwell/node";

const birchwell = new Birchwell({ apiKey: process.env.BIRCHWELL_KEY });

const result = await birchwell.usage.report(
  [{ customer_id: "cus_a81f20", meter: "api_calls", value: 1, timestamp: new Date().toISOString() }],
  { idempotencyKey: "signup-job-4471" },
);
console.log(result.accepted, result.rejected);
```

`usage.report` sends longer arrays in groups of 1,000, the API's limit per request, and gives each group its own
`Idempotency-Key` that it reuses on retries.

## The same with fetch

```js
const res = await fetch("https://api.birchwell.io/v1/usage/events", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${process.env.BIRCHWELL_KEY}`,
    "Idempotency-Key": crypto.randomUUID(),
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ events }),
});
```

## Checking from Python or a shell

When debugging a Node service it is often quickest to replay the request outside it:

```python
import os
import requests

r = requests.get(
    "https://api.birchwell.io/v1/usage/summary",
    headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"},
    params={"customer_id": "cus_a81f20", "meter": "api_calls", "period": "2026-03"},
    timeout=10,
)
print(r.json()["quantity"])
```

```bash
curl "https://api.birchwell.io/v1/usage/summary?customer_id=cus_a81f20&meter=api_calls&period=2026-03" \
  -H "Authorization: Bearer $BIRCHWELL_KEY"
```

## Things that trip people up

- **Generating a new idempotency key per retry.** Generate it once per batch; Birchwell dedupes on the
  `Idempotency-Key` header within 24 hours, but only if the retry carries the same key.
- **Sending one event per request.** At 1,200 requests per minute per key, that caps you at 1,200 events a minute.
  Batch instead (see [Batching](batching.md)).
- **Calling from the browser.** The package throws when it detects a browser; keys belong on servers.

The package reference is on [Node library](node-library.md).
