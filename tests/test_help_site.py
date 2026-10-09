import re

import pytest
from fastapi.testclient import TestClient

from billing.help_site import DOCS_DIR
from billing.server import app

TITLES = {
    path.stem: re.search(r"^title: (.+)$", path.read_text(encoding="utf-8"), re.MULTILINE).group(1)
    for path in DOCS_DIR.glob("*.md")
}
SEARCH_FORM = (
    '<form action="/help/search" method="get">\n<input type="text" name="q" value="">\n'
    '<button type="submit">Search</button>\n</form>'
)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_contents_lists_every_page_by_title_in_order(client):
    response = client.get("/help")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert len(TITLES) == 48
    linked = re.findall(r'<li><a href="/help/([\w-]+)">([^<]+)</a></li>', response.text)
    assert dict(linked) == TITLES
    assert [title for _, title in linked] == sorted(TITLES.values(), key=str.lower)


def test_a_page_renders_its_title_date_and_links_to_other_pages(client):
    response = client.get("/help/idempotency")
    assert response.status_code == 200
    assert response.text.count("<h1>Idempotency</h1>") == 1
    assert "<p>Updated 2026-07-28</p>" in response.text
    assert '<a href="/help/usage-summary">usage summaries</a>' in response.text
    assert ".md" not in response.text
    assert "title: Idempotency" not in response.text


def test_an_unknown_page_is_404(client):
    assert client.get("/help/no-such-page").status_code == 404


def test_a_word_from_one_title_finds_that_page_first(client):
    assert [slug for slug, title in TITLES.items() if "pagination" in title.lower()] == ["pagination"]
    response = client.get("/help/search", params={"q": "Pagination"})
    assert response.status_code == 200
    hits = re.findall(r'<li><a href="/help/([\w-]+)">', response.text)
    assert hits[0] == "pagination"
    assert len(hits) > 1


@pytest.mark.parametrize("query", ["zzzqqq", ""])
def test_a_search_without_hits_says_no_pages_match(client, query):
    response = client.get("/help/search", params={"q": query})
    assert response.status_code == 200
    assert "<p>No pages match.</p>" in response.text
    assert "<li>" not in response.text


def test_every_help_page_has_the_search_form_and_the_footer(client):
    for path in ("/help", "/help/webhooks", "/help/search?q=webhook"):
        text = client.get(path).text
        assert "Birchwell Billing developer docs" in text
        assert '<form action="/help/search" method="get">' in text
        assert "Still stuck? Ask the support assistant (POST /chat)." in text
    assert SEARCH_FORM in client.get("/help/webhooks").text


def test_the_openapi_docs_still_live_at_docs(client):
    assert client.get("/docs").status_code == 200
