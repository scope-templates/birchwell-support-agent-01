import re

ENTRIES = [
    {
        "id": "auth",
        "question": "How do I authenticate my API requests?",
        "answer": (
            "Send your secret key as a bearer token in the Authorization header: "
            "`Authorization: Bearer bw_live_...` for live data, or `Authorization: Bearer bw_test_...` "
            "while you are testing. Keep live keys on your servers; never ship them in a browser or mobile app."
        ),
        "last_reviewed": "2025-01-15",
    },
    {
        "id": "usage-dedupe",
        "question": "Why are duplicate usage events dropped?",
        "answer": (
            "Birchwell dedupes usage events on the `X-Request-Id` header. If a retried "
            "`POST /v1/usage/events` carries the same `X-Request-Id` as an earlier request, it is accepted "
            "but not counted again. Use an id your worker already has, such as the job id, so retries are "
            "always safe."
        ),
        "last_reviewed": "2024-09-30",
    },
    {
        "id": "batch-size",
        "question": "How many usage events can I send in one batch?",
        "answer": (
            "A single `POST /v1/usage/events` request takes up to 250 events. Larger batches are rejected "
            "as a whole, so split them into groups of 250 before sending."
        ),
        "last_reviewed": "2024-10-21",
    },
    {
        "id": "meter-aggregation",
        "question": "Which aggregation types can a meter use?",
        "answer": (
            "Meters aggregate with `sum`: every event's quantity is added up over the billing period. "
            "If you need a peak value or a count of distinct users, work it out in your own system and "
            "report the result as a single event."
        ),
        "last_reviewed": "2024-07-08",
    },
    {
        "id": "invoice-finalisation",
        "question": "When does an invoice finalise?",
        "answer": (
            "An invoice finalises 48 hours after its billing period closes. Until then it is a draft and "
            "its lines are editable, so late usage can still land on it. Once finalised it is locked, and "
            "corrections go through a credit note."
        ),
        "last_reviewed": "2025-02-03",
    },
    {
        "id": "webhooks",
        "question": "Why did my webhook fail, and is it retried?",
        "answer": (
            "Birchwell sends `invoice.paid` to your webhook endpoint when an invoice is paid. If your "
            "endpoint does not answer with a 2xx, the delivery is retried 3 times over 1 hour and then "
            "marked as failed. Check that the endpoint is publicly reachable and returns 200 quickly."
        ),
        "last_reviewed": "2024-06-25",
    },
    {
        "id": "credit-notes",
        "question": "How do I issue a credit note?",
        "answer": (
            "Send `POST /v1/invoices/{id}/credit_notes` with `amount_minor` and a `reason`. Credit notes "
            "can only be issued on finalised invoices; a draft invoice's lines can still change until it "
            "finalises."
        ),
        "last_reviewed": "2025-01-15",
    },
    {
        "id": "rate-limit",
        "question": "What is the rate limit for an API key?",
        "answer": (
            "Each API key can make 1,200 requests per minute. If a backfill or batch job needs more, "
            "spread it across several minutes rather than sending it all at once."
        ),
        "last_reviewed": "2024-12-12",
    },
]


STOPWORDS = frozenset(
    "how do i my the a an is can in to of we our it what with for on and you your be get when does there".split()
)


def pick(question):
    words = set(re.findall(r"\w+", question.lower())) - STOPWORDS
    shared, entry = max(
        ((len(words & set(re.findall(r"\w+", entry["question"].lower()))), entry) for entry in ENTRIES),
        key=lambda scored: scored[0],
    )
    return entry if shared >= 2 else None
