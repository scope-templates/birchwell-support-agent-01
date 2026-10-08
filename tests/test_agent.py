import importlib
import json
import sys
from types import SimpleNamespace

import pytest

import billing
from billing import agent, faq, ledger, tools
from billing.model import Final, KeywordModel, OpenAIModel, ToolCall, build_model

NO_ANSWER = (
    "I don't have an answer for that one. The developer docs at "
    "https://github.com/scope-templates/marlow-birchwell-docs-01/tree/main/birchwell cover the API in full, "
    "or use Ask support in the Help menu."
)
SEEDED_QUESTIONS = json.loads((ledger.DATA_DIR / "seed.json").read_text(encoding="utf-8"))["questions"]
AMOUNT_REQUEST = (
    "Send the request again with the amount written with two decimals, for example: "
    "credit inv_1001 12.50 for the September outage."
)
DRAFT_REFUSAL = (
    "inv_1003 is still a draft and cannot be credited; its lines can still change until it finalises, "
    "and this agent changes them only by rerunning metering"
)


def ask(message, customer_id="cus_01"):
    return agent.run(KeywordModel(), customer_id, message)


def calls(reply):
    return [(call["name"], call["arguments"]) for call in reply["tool_calls"]]


def test_without_a_configured_model_the_keyword_model_answers():
    assert isinstance(build_model(), KeywordModel)


def test_invoice_question_calls_invoice_status_once():
    reply = ask("what is the status of inv_1003", customer_id="cus_03")
    assert calls(reply) == [("invoice_status", {"customer_id": "cus_03", "invoice_id": "inv_1003"})]
    assert reply["answer"] == "inv_1003 (draft, 2026-10) totals EUR 78.30 across 4 lines."


def test_another_customers_invoice_is_refused():
    reply = ask("what is the status of inv_1003", customer_id="cus_01")
    assert reply["tool_calls"][0]["result"] == {"error": "no invoice inv_1003 for cus_01"}
    assert reply["answer"] == "I couldn't do that: no invoice inv_1003 for cus_01"


def test_duplicate_event_question_is_answered_from_the_faq_verbatim():
    reply = ask("why was my second usage event dropped as a duplicate")
    assert calls(reply) == [("faq_lookup", {"question": "why was my second usage event dropped as a duplicate"})]
    assert "X-Request-Id" in reply["answer"]
    assert reply["answer"] == faq.ENTRIES[1]["answer"]


def test_webhook_question_ships_the_faq_retry_schedule():
    reply = ask("my webhook endpoint was down for twenty minutes, will the events be retried?")
    assert [name for name, _ in calls(reply)] == ["faq_lookup"]
    assert "retried 3 times over 1 hour" in reply["answer"]


def test_invoice_question_without_an_invoice_id_goes_to_the_faq():
    reply = ask("when does an invoice finalise")
    assert [name for name, _ in calls(reply)] == ["faq_lookup"]
    assert "48 hours" in reply["answer"]


def test_rerun_uses_the_customer_in_view_and_the_period_asked_for():
    reply = ask("please rerun metering for 2026-10", customer_id="cus_02")
    assert calls(reply) == [("rerun_metering", {"customer_id": "cus_02", "period": "2026-10"})]
    assert reply["answer"] == "Reran metering for inv_1002: USD 24.55 before, USD 86.50 after (+61.95)."


def test_rerun_for_another_customer_is_refused():
    reply = ask("recalculate cus_03 for 2026-10", customer_id="cus_02")
    assert reply["tool_calls"][0]["result"] == {"error": "this chat is about cus_02, not cus_03"}
    assert reply["answer"] == "I couldn't do that: this chat is about cus_02, not cus_03"
    assert tools.invoice_status("cus_03", "inv_1003")["total_minor"] == 7830


def test_rerun_without_a_period_asks_for_it_again():
    reply = ask("can you recompute this customer's usage", customer_id="cus_02")
    assert reply["tool_calls"] == []
    assert reply["answer"] == (
        "Send the request again with the billing period as YYYY-MM, for example: rerun metering for 2026-10."
    )


def test_credit_request_issues_a_credit_note_in_minor_units():
    reply = ask("credit inv_1001 12.50 for the September outage")
    assert calls(reply) == [
        (
            "issue_credit_note",
            {
                "customer_id": "cus_01",
                "invoice_id": "inv_1001",
                "amount_minor": 1250,
                "reason": "credit inv_1001 12.50 for the September outage",
            },
        )
    ]
    assert reply["answer"] == "Issued cn_3 for GBP 12.50 against inv_1001."


def test_credit_amount_is_the_one_number_with_two_decimals():
    reply = ask("credit inv_1001 for the 12 September outage, 5.00")
    assert calls(reply)[0][1]["amount_minor"] == 500


@pytest.mark.parametrize(
    "message",
    ["credit inv_1001 for the September outage", "credit inv_1001 12.50 or 15.00", "credit inv_1001 12 pounds"],
)
def test_credit_without_exactly_one_two_decimal_amount_asks_for_it_again(message):
    reply = ask(message)
    assert reply["tool_calls"] == []
    assert reply["answer"] == AMOUNT_REQUEST


def test_refused_credit_is_reported_in_the_answer():
    reply = ask("credit inv_1003 5.00 as goodwill", customer_id="cus_03")
    assert reply["tool_calls"][0]["result"] == {"error": DRAFT_REFUSAL}
    assert reply["answer"] == f"I couldn't do that: {DRAFT_REFUSAL}"


def test_keyword_default_runs_without_the_openai_package(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)
    monkeypatch.delitem(sys.modules, "billing.model")
    monkeypatch.setattr(billing, "model", billing.model)
    model = importlib.import_module("billing.model")
    keyword = model.build_model()
    assert keyword.name == "keyword"
    step = keyword.plan([{"role": "system", "content": "cus_01"}, {"role": "user", "content": "rate limit"}], {})
    assert step == model.ToolCall("call_1", "faq_lookup", {"question": "rate limit"})
    with pytest.raises(RuntimeError) as missing:
        model.OpenAIModel("test-model")
    assert "BIRCHWELL_MODEL" in str(missing.value)
    assert "openai" in str(missing.value)



class LoopingModel:
    name = "looping"

    def plan(self, messages, tools):
        if tools:
            return ToolCall(f"call_{len(messages)}", "faq_lookup", {"question": "rate limit"})
        return Final("stopped")


def test_the_loop_never_runs_more_than_four_tool_calls():
    reply = agent.run(LoopingModel(), "cus_01", "anything")
    assert len(reply["tool_calls"]) == 4
    assert reply["answer"] == "stopped"


class UnknownToolModel:
    name = "unknown-tool"

    def plan(self, messages, tools):
        if messages[-1]["role"] == "tool":
            return Final(messages[-1]["content"])
        return ToolCall("call_1", "delete_customer", {"customer_id": "cus_01"})


def test_an_unknown_tool_is_reported_back_to_the_model():
    reply = agent.run(UnknownToolModel(), "cus_01", "remove this customer")
    assert reply["tool_calls"][0]["result"] == {"error": "unknown tool delete_customer"}
    assert reply["answer"] == '{"error": "unknown tool delete_customer"}'


def test_openai_model_sends_tools_as_functions_and_reads_back_a_tool_call(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    sent = {}

    def create(**kwargs):
        sent.update(kwargs)
        function = SimpleNamespace(name="invoice_status", arguments='{"invoice_id": "inv_1002"}')
        message = SimpleNamespace(content=None, tool_calls=[SimpleNamespace(id="call_9", function=function)])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    model = OpenAIModel("test-model")
    model.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    step = model.plan([{"role": "user", "content": "status of inv_1002"}], agent.TOOLS)
    assert step == ToolCall("call_9", "invoice_status", {"invoice_id": "inv_1002"})
    assert sent["model"] == "test-model"
    assert [tool["function"]["name"] for tool in sent["tools"]] == list(agent.TOOLS)
    assert sent["tools"][0]["function"]["parameters"] == agent.TOOLS["invoice_status"]["parameters"]


def test_openai_model_sends_no_tools_when_none_are_offered(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    sent = {}

    def create(**kwargs):
        sent.update(kwargs)
        message = SimpleNamespace(content="done", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    model = OpenAIModel("test-model")
    model.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    assert model.plan([{"role": "user", "content": "thanks"}], {}) == Final("done")
    assert "tools" not in sent


def test_a_question_the_faq_does_not_cover_gets_the_no_answer_reply():
    reply = ask("how do I cancel my account")
    assert calls(reply) == [("faq_lookup", {"question": "how do I cancel my account"})]
    assert reply["answer"] == NO_ANSWER
    assert reply["outcome"] == "no_match"


class EchoingModel:
    name = "echoing"

    def plan(self, messages, tools):
        if messages[-1]["role"] == "tool":
            return Final(json.loads(messages[-1]["content"])["answer"])
        return ToolCall("call_1", "faq_lookup", {"question": messages[-1]["content"]})


def test_a_hosted_model_gets_the_no_answer_text_in_the_tool_result():
    reply = agent.run(EchoingModel(), "cus_01", "how do I cancel my account")
    assert reply["answer"] == NO_ANSWER


@pytest.mark.parametrize(
    ("message", "customer_id", "outcome"),
    [
        ("how big can a usage batch be", "cus_01", "faq:batch-size"),
        ("how do I cancel my account", "cus_01", "no_match"),
        ("what is the status of inv_1002", "cus_02", "tool:invoice_status"),
        ("what is the status of inv_1002", "cus_01", "refused"),
        ("credit inv_1001 for the September outage", "cus_01", "asked_again"),
        ("can you recompute this customer's usage", "cus_02", "asked_again"),
        ("credit inv_1003 5.00 as goodwill", "cus_03", "refused"),
    ],
)
def test_the_outcome_names_where_the_loop_ended(message, customer_id, outcome):
    assert agent.run(KeywordModel(), customer_id, message)["outcome"] == outcome


@pytest.mark.parametrize("question", SEEDED_QUESTIONS, ids=[question["question_id"] for question in SEEDED_QUESTIONS])
def test_every_seeded_question_reaches_its_logged_outcome(question):
    assert agent.run(KeywordModel(), question["customer_id"], question["message"])["outcome"] == question["outcome"]
