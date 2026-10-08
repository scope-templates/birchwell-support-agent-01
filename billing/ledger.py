import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    currency TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    aggregation TEXT NOT NULL CHECK (aggregation IN ('sum', 'max', 'unique_count')),
    unit_price_minor INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers (id),
    meter_id TEXT NOT NULL REFERENCES meters (id),
    subject TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    occurred_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers (id),
    period TEXT NOT NULL,
    currency TEXT NOT NULL,
    finalized_at TEXT,
    UNIQUE (customer_id, period)
);
CREATE TABLE IF NOT EXISTS invoice_lines (
    invoice_id TEXT NOT NULL REFERENCES invoices (id),
    meter_id TEXT NOT NULL REFERENCES meters (id),
    quantity INTEGER NOT NULL,
    amount_minor INTEGER NOT NULL,
    PRIMARY KEY (invoice_id, meter_id)
);
CREATE TABLE IF NOT EXISTS credit_notes (
    id INTEGER PRIMARY KEY,
    invoice_id TEXT NOT NULL REFERENCES invoices (id),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS questions (
    question_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers (id),
    asked_at TEXT NOT NULL,
    message TEXT NOT NULL,
    outcome TEXT NOT NULL
        CHECK (outcome IN ('no_match', 'asked_again', 'refused') OR outcome LIKE 'faq:%' OR outcome LIKE 'tool:%'),
    escalated INTEGER NOT NULL DEFAULT 0 CHECK (escalated IN (0, 1))
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(os.environ.get("BIRCHWELL_DB", DATA_DIR / "birchwell.sqlite"))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def seed(conn):
    conn.executescript(SCHEMA)
    if conn.execute("SELECT 1 FROM customers").fetchone():
        return
    data = json.loads((DATA_DIR / "seed.json").read_text(encoding="utf-8"))
    conn.executemany("INSERT INTO customers VALUES (:id, :name, :currency)", data["customers"])
    conn.executemany(
        "INSERT INTO meters VALUES (:id, :name, :aggregation, :unit_price_minor)", data["meters"]
    )
    conn.executemany(
        "INSERT INTO usage_events (customer_id, meter_id, subject, quantity, occurred_at, idempotency_key)"
        " VALUES (:customer_id, :meter_id, :subject, :quantity, :occurred_at, :idempotency_key)",
        data["usage_events"],
    )
    for invoice in data["invoices"]:
        conn.execute(
            "INSERT INTO invoices VALUES (:id, :customer_id, :period, :currency, :finalized_at)", invoice
        )
        conn.executemany(
            "INSERT INTO invoice_lines VALUES (:invoice_id, :meter_id, :quantity, :amount_minor)",
            [{**line, "invoice_id": invoice["id"]} for line in invoice["lines"]],
        )
    conn.executemany(
        "INSERT INTO credit_notes VALUES (:id, :invoice_id, :amount_minor, :reason, :created_at)",
        data["credit_notes"],
    )
    conn.executemany(
        "INSERT INTO questions VALUES (:question_id, :customer_id, :asked_at, :message, :outcome, :escalated)",
        data["questions"],
    )


def get_invoice(conn, invoice_id):
    row = conn.execute(
        "SELECT i.*, (SELECT coalesce(sum(amount_minor), 0) FROM credit_notes WHERE invoice_id = i.id)"
        " AS credited_minor FROM invoices i WHERE i.id = ?",
        (invoice_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"no invoice {invoice_id}")
    lines = [
        dict(line)
        for line in conn.execute(
            "SELECT meter_id, quantity, amount_minor FROM invoice_lines WHERE invoice_id = ? ORDER BY meter_id",
            (invoice_id,),
        )
    ]
    return {
        **dict(row),
        "status": "finalized" if row["finalized_at"] else "draft",
        "lines": lines,
        "total_minor": sum(line["amount_minor"] for line in lines),
    }
