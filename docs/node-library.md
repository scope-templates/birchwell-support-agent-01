---
title: Node.js library
updated: 2026-06-22
---

# Node.js library

`@birchwell/node` is the official client for Node.js 18 and later. It sets the `Authorization` header, generates and
reuses `Idempotency-Key` values on retries, splits usage batches into groups of 1,000 and waits out `429` responses.
There is no official Python package; Python services call the HTTP API with `requests`, as shown throughout these docs.

```bash
npm install @birchwell/node
```

## Reporting usage

```js
import { Birchwell } from "@birchwell/node";

const birchwell = new Birchwell({ apiKey: process.env.BIRCHWELL_KEY, maxRetries: 3 });

const result = await birchwell.usage.report(events); // any length; sent 1,000 at a time
console.log(result.accepted, result.rejected);
```

Each group of 1,000 gets its own `Idempotency-Key`, and a retry of that group reuses it, so a timeout never counts
usage twice. Pass `idempotencyKey` yourself if you want the key to come from your job id.

## Invoices and credit notes

```js
const invoice = await birchwell.invoices.get("inv_5d02c7");
if (invoice.status !== "draft") {
  await birchwell.invoices.creditNotes.create("inv_5d02c7", {
    amount_minor: 1500,
    reason: "Service credit for the 14 March outage",
  });
}
```

## Webhook verification

```js
import { verifySignature } from "@birchwell/node/webhooks";

app.post("/birchwell/webhooks", express.raw({ type: "application/json" }), (req, res) => {
  if (!verifySignature(req.body, req.get("Birchwell-Signature"), process.env.BIRCHWELL_WEBHOOK_SECRET)) {
    return res.sendStatus(401);
  }
  queue.push(JSON.parse(req.body));
  res.sendStatus(204);
});
```

## Errors

Failed calls reject with a `BirchwellError` holding `status`, `code`, `message` and `requestId`. Codes are the same
as the HTTP API's, listed on [Errors](errors.md).

## Comparing with a raw call

When the library and your expectations differ, repeat the call directly:

```python
import os
import requests

r = requests.get("https://api.birchwell.io/v1/invoices/inv_5d02c7",
                 headers={"Authorization": f"Bearer {os.environ['BIRCHWELL_KEY']}"}, timeout=10)
print(r.status_code, r.headers["Birchwell-Request-Id"])
```

```bash
curl -i https://api.birchwell.io/v1/invoices/inv_5d02c7 -H "Authorization: Bearer $BIRCHWELL_KEY"
```
