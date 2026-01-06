import time
from ddgs import DDGS
from ddgs.exceptions import DDGSException

def web_search(query: str, max_results: int = 4, retries: int = 3) -> list[dict]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            raw_results = DDGS().text(query, max_results=max_results)
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in raw_results
            ]
        except DDGSException as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_error
