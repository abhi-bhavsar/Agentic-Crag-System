import time
import logging
from typing import Dict, Any, List
from app.rag.state import GraphState
from app.rag.tools.search_tools import search_web_fallback

logger = logging.getLogger("rag.nodes.web_search")

def web_search_node(state: GraphState) -> Dict[str, Any]:
    """
    Web Search Fallback Node (CRAG Pattern):
    Executes external web search when vector retrieval is insufficient, ambiguous,
    or when real-time external knowledge is demanded.
    """
    start_time = time.time()
    traces = list(state.get("traces", []))
    query = state.get("current_query") or state.get("original_query", "")
    existing_docs = list(state.get("graded_documents") or [])

    logger.info(f"Triggering CRAG Web Search Fallback for query: '{query}'")
    web_results = search_web_fallback(query, max_results=3)

    # Convert web results into document chunks with attribution
    augmented_docs = list(existing_docs)
    for idx, wr in enumerate(web_results):
        augmented_docs.append({
            "chunk_id": f"web_{idx}",
            "document_id": f"web_{idx}",
            "chunk_index": idx,
            "content": f"{wr.get('title', '')}\n{wr.get('snippet', '')}",
            "source": wr.get("link", "Web Search"),
            "page": 1,
            "similarity": 0.85,
            "relevance_score": 0.85,
            "grade": "relevant (web)",
            "reasoning": "Retrieved from external web search fallback"
        })

    duration = round((time.time() - start_time) * 1000, 2)
    traces.append({
        "node": "web_search",
        "title": "CRAG Web Search Fallback",
        "status": "completed" if web_results else "warning",
        "details": {
            "query": query,
            "results_count": len(web_results),
            "web_sources": [wr.get("link") for wr in web_results],
            "total_context_chunks": len(augmented_docs)
        },
        "duration_ms": duration
    })

    return {
        "graded_documents": augmented_docs,
        "web_results": web_results,
        "traces": traces
    }
