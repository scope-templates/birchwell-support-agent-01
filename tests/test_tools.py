import inspect
from datetime import date

import pytest

from billing import faq, tools


def test_invoice_status_reports_a_finalized_invoice():
    status = tools.invoice_status("cus_01", "inv_1001")
    assert status["status"] == "finalized"
    assert status["period"] == "2026-09"
    assert status["currency"] == "GBP"
    assert status["total_minor"] == 6580
    assert len(status["lines"]) == 4


def test_invoice_status_refuses_an_unknown_invoice():
    with pytest.raises(KeyError):
        tools.invoice_status("cus_01", "inv_9999")


def test_invoice_status_refuses_another_customers_invoice():
    with pytest.raises(KeyError, match="no invoice inv_1003 for cus_01"):
        tools.invoice_status("cus_01", "inv_1003")


def test_rerun_metering_rewrites_the_draft_from_late_usage():
    assert tools.rerun_metering("cus_02", "2026-10") == {
        "invoice_id": "inv_1002",
        "currency": "USD",
        "before_minor": 2455,
        "after_minor": 8650,
        "delta_minor": 6195,
    }
    assert tools.invoice_status("cus_02", "inv_1002")["total_minor"] == 8650
    assert tools.rerun_metering("cus_02", "2026-10")["delta_minor"] == 0


def test_rerun_metering_refuses_a_finalized_invoice_and_leaves_it_alone():
    before = tools.invoice_status("cus_01", "inv_1001")
    with pytest.raises(ValueError, match="finalized"):
        tools.rerun_metering("cus_01", "2026-09")
    assert tools.invoice_status("cus_01", "inv_1001") == before


def test_rerun_metering_refuses_a_period_with_no_invoice():
    with pytest.raises(KeyError):
        tools.rerun_metering("cus_03", "2026-09")


def test_issue_credit_note_credits_a_finalized_invoice():
    note = tools.issue_credit_note("cus_01", "inv_1001", 500, "API outage on 12 September")
    assert note["invoice_id"] == "inv_1001"
    assert note["amount_minor"] == 500
    assert note["credit_note_id"].startswith("cn_")
    assert tools.invoice_status("cus_01", "inv_1001")["credited_minor"] == 2450


def test_issue_credit_note_refuses_another_customers_invoice():
    with pytest.raises(KeyError, match="no invoice inv_1001 for cus_02"):
        tools.issue_credit_note("cus_02", "inv_1001", 500, "goodwill")
    assert tools.invoice_status("cus_01", "inv_1001")["credited_minor"] == 1950


def test_issue_credit_note_refuses_a_draft_invoice():
    with pytest.raises(ValueError, match="draft"):
        tools.issue_credit_note("cus_03", "inv_1003", 100, "goodwill")
    assert tools.invoice_status("cus_03", "inv_1003")["credited_minor"] == 0


@pytest.mark.parametrize("amount_minor", [0, -100, 4631, 12.5, "500"])
def test_issue_credit_note_refuses_amounts_outside_the_invoice_total(amount_minor):
    with pytest.raises(ValueError):
        tools.issue_credit_note("cus_01", "inv_1001", amount_minor, "goodwill")


def test_issue_credit_note_counts_earlier_credit_against_the_total():
    tools.issue_credit_note("cus_01", "inv_1001", 4000, "September outage")
    with pytest.raises(ValueError):
        tools.issue_credit_note("cus_01", "inv_1001", 700, "September outage, second week")
    assert tools.issue_credit_note("cus_01", "inv_1001", 630, "September outage, second week")["amount_minor"] == 630


def test_faq_has_eight_entries_with_review_dates():
    assert len(faq.ENTRIES) == 8
    assert len({entry["id"] for entry in faq.ENTRIES}) == 8
    for entry in faq.ENTRIES:
        date.fromisoformat(entry["last_reviewed"])


@pytest.mark.parametrize("question", ["asdf", "how do I cancel my account", "how do I get my API invoices"])
def test_faq_pick_finds_nothing_without_two_shared_words(question):
    assert faq.pick(question) is None


def test_faq_pick_ignores_filler_words_but_still_finds_the_batch_entry():
    assert faq.pick("how big can a usage batch be")["id"] == "batch-size"


def test_faq_lookup_without_a_match_returns_no_entry():
    assert tools.faq_lookup("how do I cancel my account") == {
        "faq_id": None,
        "answer": (
            "I don't have an answer for that one. The developer docs at "
            "https://github.com/scope-templates/marlow-birchwell-docs-01/tree/main/birchwell cover the API in "
            "full, or use Ask support in the Help menu."
        ),
        "last_reviewed": None,
    }


@pytest.mark.parametrize(
    ("question", "entry_id", "claim"),
    [
        ("how do I authenticate my API requests", "auth", "Authorization: Bearer bw_live_"),
        ("why was my second usage event dropped as a duplicate", "usage-dedupe", "X-Request-Id"),
        ("how big can a usage batch be", "batch-size", "250"),
        ("which aggregation types can a meter use", "meter-aggregation", "`sum`"),
        ("when does an invoice finalise", "invoice-finalisation", "48 hours"),
        ("why did my webhook fail", "webhooks", "3 times over 1 hour"),
        ("how do I issue a credit note", "credit-notes", "/v1/invoices/{id}/credit_notes"),
        ("what is the rate limit for my key", "rate-limit", "1,200 requests per minute"),
    ],
)
def test_faq_lookup_returns_the_matching_answer_verbatim(question, entry_id, claim):
    entry = next(entry for entry in faq.ENTRIES if entry["id"] == entry_id)
    assert tools.faq_lookup(question) == {
        "faq_id": entry_id,
        "answer": entry["answer"],
        "last_reviewed": entry["last_reviewed"],
    }
    assert claim in entry["answer"]


def test_every_tool_schema_names_its_function_parameters():
    assert sorted(tools.TOOLS) == ["faq_lookup", "invoice_status", "issue_credit_note", "rerun_metering"]
    for tool in tools.TOOLS.values():
        parameters = list(inspect.signature(tool["fn"]).parameters)
        assert tool["description"]
        assert tool["parameters"]["type"] == "object"
        assert list(tool["parameters"]["properties"]) == parameters
        assert tool["parameters"]["required"] == parameters
