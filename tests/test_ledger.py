from collections import Counter

import pytest

from billing import ledger, metering


def count(table):
    with ledger.connect() as conn:
        return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_seed_loads_the_three_customers_their_invoices_and_usage():
    assert count("customers") == 3
    assert count("meters") == 4
    assert count("invoices") == 3
    assert count("usage_events") == 60
    assert count("questions") == 40


def test_seeding_an_already_seeded_ledger_adds_nothing():
    with ledger.connect() as conn:
        ledger.seed(conn)
    assert count("customers") == 3
    assert count("usage_events") == 60
    assert count("invoice_lines") == 11
    assert count("credit_notes") == 2
    assert count("questions") == 40


def test_seeded_question_log_covers_tools_faq_answers_and_unanswered_questions():
    with ledger.connect() as conn:
        rows = conn.execute("SELECT question_id, outcome, escalated FROM questions ORDER BY question_id").fetchall()
    assert [row["question_id"] for row in rows] == [f"q_{n:04d}" for n in range(1, 41)]
    assert Counter(row["outcome"].split(":")[0] for row in rows) == {"tool": 8, "faq": 10, "no_match": 22}
    assert Counter(row["outcome"].split(":")[0] for row in rows if row["escalated"]) == {"faq": 4, "no_match": 15}
    assert sorted(row["outcome"] for row in rows if row["escalated"] and row["outcome"].startswith("faq:")) == [
        "faq:batch-size",
        "faq:meter-aggregation",
        "faq:rate-limit",
        "faq:usage-dedupe",
    ]


def test_only_the_september_invoice_is_finalized():
    with ledger.connect() as conn:
        finalized = ledger.get_invoice(conn, "inv_1001")
        drafts = [ledger.get_invoice(conn, invoice_id) for invoice_id in ("inv_1002", "inv_1003")]
    assert finalized["status"] == "finalized"
    assert finalized["finalized_at"] == "2026-10-03T00:00:00Z"
    assert [(draft["status"], draft["finalized_at"]) for draft in drafts] == [("draft", None), ("draft", None)]


def test_get_invoice_totals_its_lines():
    with ledger.connect() as conn:
        invoice = ledger.get_invoice(conn, "inv_1001")
    assert invoice["customer_id"] == "cus_01"
    assert invoice["period"] == "2026-09"
    assert invoice["currency"] == "GBP"
    assert [line["meter_id"] for line in invoice["lines"]] == [
        "mtr_api_calls",
        "mtr_compute",
        "mtr_seats",
        "mtr_storage",
    ]
    assert invoice["total_minor"] == 6580
    assert invoice["credited_minor"] == 1950


def test_seeded_credit_notes_are_the_ones_the_question_log_issued():
    with ledger.connect() as conn:
        notes = conn.execute("SELECT invoice_id, amount_minor, reason, created_at FROM credit_notes ORDER BY id").fetchall()
        asked = conn.execute(
            "SELECT message, asked_at FROM questions WHERE outcome = 'tool:issue_credit_note' ORDER BY asked_at"
        ).fetchall()
    assert [(note["reason"], note["created_at"]) for note in notes] == [(row["message"], row["asked_at"]) for row in asked]
    assert [(note["invoice_id"], note["amount_minor"]) for note in notes] == [("inv_1001", 1500), ("inv_1001", 450)]
    assert all(row["asked_at"] > "2026-10-03T00:00:00Z" for row in asked)


def test_draft_lines_are_what_the_logged_reruns_left_behind():
    with ledger.connect() as conn:
        reruns = dict(
            conn.execute(
                "SELECT customer_id, asked_at FROM questions WHERE outcome = 'tool:rerun_metering'"
            ).fetchall()
        )
        last_event = dict(
            conn.execute("SELECT customer_id, max(occurred_at) FROM usage_events GROUP BY customer_id").fetchall()
        )
        assert reruns["cus_03"] >= last_event["cus_03"]
        assert metering.compute_lines(conn, "cus_03", "2026-10") == ledger.get_invoice(conn, "inv_1003")["lines"]
        assert reruns["cus_02"].startswith("2026-10-03")
        assert last_event["cus_02"] > reruns["cus_02"]
        conn.execute(
            "DELETE FROM usage_events WHERE customer_id = 'cus_02' AND occurred_at > ?", (reruns["cus_02"],)
        )
        assert metering.compute_lines(conn, "cus_02", "2026-10") == ledger.get_invoice(conn, "inv_1002")["lines"]
        conn.rollback()


def test_no_seeded_date_is_after_the_seventh_of_october_2026():
    with ledger.connect() as conn:
        assert conn.execute("SELECT max(occurred_at) FROM usage_events").fetchone()[0] < "2026-10-08"
        assert conn.execute("SELECT max(asked_at) FROM questions").fetchone()[0] < "2026-10-08"
        assert conn.execute("SELECT min(asked_at) FROM questions").fetchone()[0] >= "2026-09-01"


def test_unknown_invoice_raises_key_error():
    with ledger.connect() as conn, pytest.raises(KeyError):
        ledger.get_invoice(conn, "inv_9999")
