import pytest
from fastapi.testclient import TestClient

from billing import ledger
from billing.server import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_chat_returns_an_answer_and_its_tool_calls_and_nothing_else(client):
    response = client.post(
        "/chat", json={"customer_id": "cus_01", "message": "how many usage events can I send in one batch"}
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"question_id", "answer", "tool_calls"}
    assert "250" in body["answer"]
    assert body["tool_calls"][0]["name"] == "faq_lookup"
    assert set(body["tool_calls"][0]) == {"name", "arguments", "result"}
    assert set(body["tool_calls"][0]["result"]) == {"faq_id", "answer", "last_reviewed"}


def logged(question_id):
    with ledger.connect() as conn:
        return dict(conn.execute("SELECT * FROM questions WHERE question_id = ?", (question_id,)).fetchone())


def test_chat_logs_each_question_with_its_outcome(client):
    first = client.post("/chat", json={"customer_id": "cus_01", "message": "how do I cancel my account"}).json()
    second = client.post("/chat", json={"customer_id": "cus_03", "message": "status of inv_1003"}).json()
    assert (first["question_id"], second["question_id"]) == ("q_0041", "q_0042")
    row = logged("q_0041")
    assert (row["customer_id"], row["message"], row["outcome"], row["escalated"]) == (
        "cus_01",
        "how do I cancel my account",
        "no_match",
        0,
    )
    assert row["asked_at"].endswith("Z")
    assert logged("q_0042")["outcome"] == "tool:invoice_status"


def test_escalating_a_question_marks_it_for_support(client):
    question_id = client.post("/chat", json={"customer_id": "cus_02", "message": "can I pause a meter"}).json()[
        "question_id"
    ]
    response = client.post(f"/chat/{question_id}/escalate")
    assert response.status_code == 204
    assert response.content == b""
    assert logged(question_id)["escalated"] == 1


def test_escalating_an_unknown_question_is_404(client):
    response = client.post("/chat/q_9999/escalate")
    assert response.status_code == 404
    assert response.json() == {"detail": "no question q_9999"}


def test_stats_count_the_last_30_days_of_the_seeded_question_log(client):
    assert client.get("/stats").json() == {
        "questions": 36,
        "by_outcome": {"faq": 9, "no_match": 20, "tool": 7, "asked_again": 0, "refused": 0},
        "escalated": {"faq": 4, "no_match": 14, "tool": 0, "asked_again": 0, "refused": 0},
    }


def test_chat_runs_an_account_action_against_the_ledger(client):
    response = client.post("/chat", json={"customer_id": "cus_02", "message": "rerun metering for 2026-10"})
    assert response.json()["tool_calls"][0]["result"]["after_minor"] == 8650
    assert client.get("/invoices/inv_1002").json()["total_minor"] == 8650


def test_chat_for_an_unknown_customer_is_404(client):
    response = client.post("/chat", json={"customer_id": "cus_99", "message": "status of inv_1001"})
    assert response.status_code == 404


def test_chat_rejects_a_body_without_a_message(client):
    assert client.post("/chat", json={"customer_id": "cus_01"}).status_code == 422


def test_get_invoice_returns_the_invoice(client):
    response = client.get("/invoices/inv_1003")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "inv_1003"
    assert body["status"] == "draft"
    assert body["total_minor"] == 7830


def test_get_unknown_invoice_is_404(client):
    assert client.get("/invoices/inv_9999").status_code == 404


def test_health_names_the_keyword_model(client):
    assert client.get("/health").json() == {"status": "ok", "model": "keyword"}
