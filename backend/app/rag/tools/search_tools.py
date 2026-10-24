import logging
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger("rag.tools.search")

def search_web_fallback(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Executes web search for CRAG fallback.
    Uses DuckDuckGo by default (zero API key required).
    If TAVILY_API_KEY is configured, can use Tavily.
    """
    results = []

    # 1. Try DuckDuckGo Search (100% free, no key required)
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for r in raw_results:
                results.append({
                    "title": r.get("title", "Web Result"),
                    "snippet": r.get("body", "") or r.get("snippet", ""),
                    "link": r.get("href", "") or r.get("link", ""),
                    "source": "Web Search (DuckDuckGo)"
                })
            if results:
                logger.info(f"DuckDuckGo search returned {len(results)} results for '{query}'")
                return results
    except Exception as e:
        logger.warning(f"DuckDuckGo search encountered an issue: {e}")

    # 2. Try Tavily fallback if configured
    if settings.TAVILY_API_KEY and settings.TAVILY_API_KEY.strip():
        try:
            import httpx
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results
                },
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                for r in data.get("results", []):
                    results.append({
                        "title": r.get("title", "Web Result"),
                        "snippet": r.get("content", ""),
                        "link": r.get("url", ""),
                        "source": "Web Search (Tavily)"
                    })
                logger.info(f"Tavily search returned {len(results)} results for '{query}'")
                return results
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}")

    # Return whatever results found or clean fallback
    return results
