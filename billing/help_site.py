import html
import re
from pathlib import Path

import markdown
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

LAYOUT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} - Birchwell Billing developer docs</title>
</head>
<body>
<header>
<p><a href="/help">Birchwell Billing developer docs</a></p>
<form action="/help/search" method="get">
<input type="text" name="q" value="{query}">
<button type="submit">Search</button>
</form>
</header>
<main>
{content}
</main>
<footer>
<p>Still stuck? Ask the support assistant (POST /chat).</p>
</footer>
</body>
</html>
"""

PAGES = {}
for path in DOCS_DIR.glob("*.md"):
    _, front, body = path.read_text(encoding="utf-8").split("---\n", 2)
    fields = dict(line.split(": ", 1) for line in front.splitlines())
    body = body.lstrip().removeprefix(f"# {fields['title']}\n")
    PAGES[path.stem] = {
        "title": fields["title"],
        "updated": fields["updated"],
        "body": body,
        "title_words": set(re.findall(r"\w+", fields["title"].lower())),
        "words": set(re.findall(r"\w+", f"{fields['title']}\n{body}".lower())),
    }

router = APIRouter()


def page(title, content, query=""):
    return HTMLResponse(LAYOUT.format(title=html.escape(title), query=html.escape(query), content=content))


@router.get("/help")
def contents():
    items = "\n".join(
        f'<li><a href="/help/{slug}">{html.escape(doc["title"])}</a></li>'
        for slug, doc in sorted(PAGES.items(), key=lambda item: item[1]["title"].lower())
    )
    return page("Contents", f"<h1>Birchwell Billing developer docs</h1>\n<ul>\n{items}\n</ul>")


@router.get("/help/search")
def search(q: str = ""):
    words = set(re.findall(r"\w+", q.lower()))
    scored = sorted(
        ((len(words & doc["words"]), slug, doc) for slug, doc in PAGES.items()),
        key=lambda hit: (-hit[0], not words & hit[2]["title_words"], hit[2]["title"].lower()),
    )
    results = []
    for score, slug, doc in scored:
        if score == 0:
            break
        first = re.search(rf"\b(?:{'|'.join(map(re.escape, words))})\b", doc["body"], re.IGNORECASE)
        start = max(first.start() - 80, 0) if first else 0
        snippet = " ".join(doc["body"][start : start + 200].split())
        results.append(
            f'<li><a href="/help/{slug}">{html.escape(doc["title"])}</a><p>{html.escape(snippet)}</p></li>'
        )
    content = "<ul>\n" + "\n".join(results) + "\n</ul>" if results else "<p>No pages match.</p>"
    return page(f"Search: {q}", f"<h1>Search results for {html.escape(q)}</h1>\n{content}", q)


@router.get("/help/{slug}")
def show(slug: str):
    doc = PAGES.get(slug)
    if doc is None:
        raise HTTPException(404, f"no page {slug}")
    body = markdown.markdown(doc["body"], extensions=["fenced_code", "tables"])
    body = re.sub(r'href="(?:\./)?([\w-]+)\.md(#[\w-]*)?"', r'href="/help/\1\2"', body)
    return page(
        doc["title"],
        f"<h1>{html.escape(doc['title'])}</h1>\n<p>Updated {doc['updated']}</p>\n{body}",
    )
