"""
Web search helper using DuckDuckGo (no API key needed).
Fetches top N results and extracts readable body text from each page.
"""
from ingestion import extract_text_from_url


def search_and_fetch(query: str, max_results: int = 3) -> str:
    from duckduckgo_search import DDGS

    combined = []
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))

    for r in results:
        url = r.get("href")
        if not url:
            continue
        try:
            text = extract_text_from_url(url)
            if text:
                combined.append(f"Source: {url}\n\n{text[:8000]}")
        except Exception:
            continue  # skip pages that fail to fetch

    if not combined:
        raise ValueError(f"No readable content found for query: {query!r}")

    return "\n\n=====\n\n".join(combined)