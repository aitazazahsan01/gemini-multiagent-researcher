from ddgs import DDGS

def web_search(query: str, max_results: int = 4) -> list[dict]:
    raw_results = DDGS().text(query, max_results=max_results)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in raw_results
    ]
