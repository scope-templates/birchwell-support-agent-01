# Birchwell support agent

Birchwell Billing meters usage and sends invoices for SaaS companies: you report usage events to our API, we
aggregate them into meters, and invoices go out when each billing period closes. This service is the support agent
that sits inside the Birchwell dashboard, where it answers your developers' integration questions and handles routine
account work on invoices, metering reruns and credit notes. Our developer docs at
https://github.com/scope-templates/marlow-birchwell-docs-01/tree/main/birchwell are the source of truth for every
integration question.

## Running

```
py -3.12 -m pip install -r requirements.txt
py -3.12 -m uvicorn billing.server:app --port 8081
```

On startup the service creates `data/birchwell.sqlite` and loads `data/seed.json` into it if the ledger is empty:
three customers, four meters, sixty usage events from 1 September to 7 October 2026, three invoices (`inv_1001` for
September, finalized on 3 October; `inv_1002` and `inv_1003` for October, still drafts), two credit notes on
`inv_1001`, and forty logged questions asked between 1 September and 7 October 2026. Set `BIRCHWELL_DB` to use another
file; delete the file to start again from the seed.

Tests: `py -3.12 -m pytest -q`.

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/chat` | `{"customer_id": "cus_01", "message": "..."}` | `{"question_id": "q_0041", "answer": "...", "tool_calls": [...]}`; 404 for an unknown customer |
| POST | `/chat/{question_id}/escalate` | | 204; marks the question as sent to support (the dashboard's Ask support button); 404 if unknown |
| GET | `/stats` | | questions from the 30 days up to the latest one, counted by outcome (`faq`, `no_match`, `tool`, `asked_again`, `refused`) and by how many were escalated |
| GET | `/invoices/{id}` | | the invoice with its lines, `total_minor` and `credited_minor`; 404 if unknown |
| GET | `/health` | | `{"status": "ok", "model": "keyword"}` or the configured model name |

`customer_id` is the customer the developer has open in the dashboard. Account actions are scoped to that customer: an
invoice or a request that belongs to any other customer is refused. Every tool call the agent made is returned with
its arguments and result:

```
POST /chat {"customer_id": "cus_03", "message": "what is the status of inv_1003"}

{
  "question_id": "q_0041",
  "answer": "inv_1003 (draft, 2026-10) totals EUR 78.30 across 4 lines.",
  "tool_calls": [
    {
      "name": "invoice_status",
      "arguments": {"customer_id": "cus_03", "invoice_id": "inv_1003"},
      "result": {"id": "inv_1003", ...}
    }
  ]
}
```

## Tools

The agent runs a plain loop in `billing/agent.py`: the model picks a tool, the tool runs against the ledger, the result
goes back to the model, and after at most four tool calls the model gives its answer.

| Tool | Arguments | Does |
|---|---|---|
| `invoice_status` | `customer_id`, `invoice_id` | status, period, currency, lines, total and credit issued so far; refuses another customer's invoice |
| `rerun_metering` | `customer_id`, `period` | recomputes a draft invoice's lines from its usage events and reports the change; refuses a finalized invoice |
| `issue_credit_note` | `customer_id`, `invoice_id`, `amount_minor`, `reason` | credits a finalized invoice; refuses another customer's invoice, drafts, and amounts above what is left uncredited |
| `faq_lookup` | `question` | the best-matching FAQ entry's answer and its `last_reviewed` date |

Meters aggregate with `sum`, `max` or `unique_count` (distinct `subject` values) over the period; see
`billing/metering.py`.

By default the keyword model plans each turn: a message with `rerun`, `recalculate` or `recompute` and a `YYYY-MM`
period reruns metering, `credit` with an invoice id issues a credit note, any other message with an invoice id looks
that invoice up, and everything else goes to `faq_lookup`. A credit request must contain exactly one amount written with
two decimals in major units, such as `12.50`; with none or more than one, the agent asks for the request again and
issues nothing. A rerun without a period is answered the same way. Its answer for an FAQ question is the FAQ entry's
text as written.

The `openai` package is installed by `requirements.txt` and used only when `BIRCHWELL_MODEL` is set: set it to a chat
model name, with `OPENAI_API_KEY` set, to have a hosted chat model plan the turns through the package's tool calling
instead of the keyword model.

## FAQ

Integration answers come from the eight entries in `billing/faq.py`, one per topic: authentication, duplicate usage
events, batch size, meter aggregation, invoice finalisation, webhooks, credit notes and rate limits. Each carries the
date support last reviewed it. A question the FAQ does not cover gets a no-answer reply that points at the
developer docs.

## Docs

The developer docs at https://github.com/scope-templates/marlow-birchwell-docs-01/tree/main/birchwell are the source
of truth for every integration question; the FAQ is the support team's shorthand.
