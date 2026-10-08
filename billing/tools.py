from datetime import UTC, datetime

from billing import faq, ledger, metering


def invoice_status(customer_id, invoice_id):
    with ledger.connect() as conn:
        invoice = ledger.get_invoice(conn, invoice_id)
    if invoice["customer_id"] != customer_id:
        raise KeyError(f"no invoice {invoice_id} for {customer_id}")
    return invoice


def rerun_metering(customer_id, period):
    with ledger.connect() as conn:
        row = conn.execute(
            "SELECT id FROM invoices WHERE customer_id = ? AND period = ?", (customer_id, period)
        ).fetchone()
        if row is None:
            raise KeyError(f"no invoice for {customer_id} in {period}")
        invoice = ledger.get_invoice(conn, row["id"])
        if invoice["status"] == "finalized":
            raise ValueError(
                f"{invoice['id']} was finalized at {invoice['finalized_at']}; its lines can no longer change"
            )
        lines = metering.compute_lines(conn, customer_id, period)
        conn.execute("DELETE FROM invoice_lines WHERE invoice_id = ?", (invoice["id"],))
        conn.executemany(
            "INSERT INTO invoice_lines VALUES (:invoice_id, :meter_id, :quantity, :amount_minor)",
            [{**line, "invoice_id": invoice["id"]} for line in lines],
        )
    after_minor = sum(line["amount_minor"] for line in lines)
    return {
        "invoice_id": invoice["id"],
        "currency": invoice["currency"],
        "before_minor": invoice["total_minor"],
        "after_minor": after_minor,
        "delta_minor": after_minor - invoice["total_minor"],
    }


def issue_credit_note(customer_id, invoice_id, amount_minor, reason):
    with ledger.connect() as conn:
        invoice = ledger.get_invoice(conn, invoice_id)
        if invoice["customer_id"] != customer_id:
            raise KeyError(f"no invoice {invoice_id} for {customer_id}")
        if invoice["status"] == "draft":
            raise ValueError(
                f"{invoice_id} is still a draft and cannot be credited; its lines can still change until it "
                "finalises, and this agent changes them only by rerunning metering"
            )
        uncredited = invoice["total_minor"] - invoice["credited_minor"]
        if type(amount_minor) is not int or not 0 < amount_minor <= uncredited:
            raise ValueError(f"{invoice_id} has {uncredited} minor units left to credit, not {amount_minor}")
        created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        note_id = conn.execute(
            "INSERT INTO credit_notes (invoice_id, amount_minor, reason, created_at) VALUES (?, ?, ?, ?)",
            (invoice_id, amount_minor, reason, created_at),
        ).lastrowid
    return {
        "credit_note_id": f"cn_{note_id}",
        "invoice_id": invoice_id,
        "currency": invoice["currency"],
        "amount_minor": amount_minor,
        "reason": reason,
        "created_at": created_at,
    }


def faq_lookup(question):
    entry = faq.pick(question)
    if entry is None:
        return {
            "faq_id": None,
            "answer": (
                "I don't have an answer for that one. The developer docs at "
                "https://github.com/scope-templates/marlow-birchwell-docs-01/tree/main/birchwell cover the API in "
                "full, or use Ask support in the Help menu."
            ),
            "last_reviewed": None,
        }
    return {"faq_id": entry["id"], "answer": entry["answer"], "last_reviewed": entry["last_reviewed"]}


TOOLS = {
    "invoice_status": {
        "description": "Look up one invoice: status, period, currency, lines, total and how much has been credited.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer in view, such as cus_01."},
                "invoice_id": {"type": "string", "description": "Invoice id, such as inv_1001."},
            },
            "required": ["customer_id", "invoice_id"],
        },
        "fn": invoice_status,
    },
    "rerun_metering": {
        "description": (
            "Recompute a customer's draft invoice for one billing period from its recorded usage events "
            "and report the change. Finalized invoices cannot be rerun."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer in view, such as cus_01."},
                "period": {"type": "string", "description": "Billing period as YYYY-MM."},
            },
            "required": ["customer_id", "period"],
        },
        "fn": rerun_metering,
    },
    "issue_credit_note": {
        "description": (
            "Issue a credit note against a finalized invoice. The amount is in minor units and cannot exceed "
            "what is left uncredited on the invoice."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer in view, such as cus_01."},
                "invoice_id": {"type": "string", "description": "Invoice id, such as inv_1001."},
                "amount_minor": {"type": "integer", "description": "Amount in minor units, so 1250 is 12.50."},
                "reason": {"type": "string", "description": "Why the credit is being issued."},
            },
            "required": ["customer_id", "invoice_id", "amount_minor", "reason"],
        },
        "fn": issue_credit_note,
    },
    "faq_lookup": {
        "description": (
            "Answer a developer's integration question (authentication, usage events, batching, meters, "
            "invoice finalisation, webhooks, credit notes, rate limits) from the support FAQ."
        ),
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "The developer's question."}},
            "required": ["question"],
        },
        "fn": faq_lookup,
    },
}
