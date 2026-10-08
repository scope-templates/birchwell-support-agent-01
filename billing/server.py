from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from billing import agent, ledger
from billing.model import build_model


class ChatRequest(BaseModel):
    customer_id: str
    message: str


@asynccontextmanager
async def lifespan(app):
    with ledger.connect() as conn:
        ledger.seed(conn)
    app.state.model = build_model()
    yield


app = FastAPI(title="Birchwell support agent", lifespan=lifespan)


@app.post("/chat")
def chat(request: ChatRequest):
    with ledger.connect() as conn:
        if conn.execute("SELECT 1 FROM customers WHERE id = ?", (request.customer_id,)).fetchone() is None:
            raise HTTPException(404, f"no customer {request.customer_id}")
    reply = agent.run(app.state.model, request.customer_id, request.message)
    with ledger.connect() as conn:
        row_id = conn.execute(
            "INSERT INTO questions (question_id, customer_id, asked_at, message, outcome)"
            " SELECT printf('q_%04d', count(*) + 1), ?, ?, ?, ? FROM questions",
            (
                request.customer_id,
                datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                request.message,
                reply["outcome"],
            ),
        ).lastrowid
        question_id = conn.execute("SELECT question_id FROM questions WHERE rowid = ?", (row_id,)).fetchone()[0]
    return {"question_id": question_id, "answer": reply["answer"], "tool_calls": reply["tool_calls"]}


@app.post("/chat/{question_id}/escalate", status_code=204)
def escalate(question_id: str):
    with ledger.connect() as conn:
        if conn.execute("UPDATE questions SET escalated = 1 WHERE question_id = ?", (question_id,)).rowcount == 0:
            raise HTTPException(404, f"no question {question_id}")
    return Response(status_code=204)


@app.get("/stats")
def stats():
    with ledger.connect() as conn:
        rows = conn.execute(
            "SELECT outcome, escalated FROM questions WHERE asked_at >="
            " (SELECT strftime('%Y-%m-%dT%H:%M:%SZ', max(asked_at), '-30 days') FROM questions)"
        ).fetchall()
    by_outcome = dict.fromkeys(("faq", "no_match", "tool", "asked_again", "refused"), 0)
    escalated = dict.fromkeys(("faq", "no_match", "tool", "asked_again", "refused"), 0)
    for row in rows:
        kind = row["outcome"].split(":")[0]
        by_outcome[kind] += 1
        escalated[kind] += row["escalated"]
    return {"questions": len(rows), "by_outcome": by_outcome, "escalated": escalated}


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    with ledger.connect() as conn:
        try:
            return ledger.get_invoice(conn, invoice_id)
        except KeyError as error:
            raise HTTPException(404, error.args[0]) from error


@app.get("/health")
def health():
    return {"status": "ok", "model": app.state.model.name}
