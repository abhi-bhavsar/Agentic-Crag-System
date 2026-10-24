import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    NodeTrace,
    DocumentChunk,
    WebSearchResult
)
from app.rag.graph import crag_graph
from app.config import settings

logger = logging.getLogger("rag.api.chat")
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Standard synchronous endpoint for running the CRAG + Self-RAG graph.
    Returns complete answer, step-by-step traces, sources, and hallucination verdict.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    initial_state = {
        "original_query": request.message,
        "current_query": request.message,
        "traces": [],
        "documents": [],
        "graded_documents": [],
        "web_results": [],
        "web_search_needed": False,
        "retry_count": 0,
        "model": request.model or settings.GROQ_MODEL,
        "temperature": request.temperature or 0.2,
        "mode": request.mode or "adaptive_crag_self_rag"
    }

    try:
        final_state = crag_graph.invoke(initial_state)

        # Convert traces
        traces = [
            NodeTrace(
                node=t.get("node", "step"),
                title=t.get("title", "Processing Step"),
                status=t.get("status", "completed"),
                details=t.get("details", {}),
                duration_ms=t.get("duration_ms", 0.0)
            )
            for t in final_state.get("traces", [])
        ]

        # Convert sources
        sources = []
        for d in final_state.get("graded_documents", []) or final_state.get("documents", []):
            sources.append(
                DocumentChunk(
                    content=d.get("content", ""),
                    source=d.get("source", "Document"),
                    page=d.get("page", 1),
                    chunk_index=d.get("chunk_index", 0),
                    relevance_score=d.get("relevance_score"),
                    grade=d.get("grade", "relevant"),
                    reasoning=d.get("reasoning")
                )
            )

        web_results = [
            WebSearchResult(
                title=wr.get("title", "Web Result"),
                snippet=wr.get("snippet", ""),
                link=wr.get("link", "")
            )
            for wr in final_state.get("web_results", [])
        ]

        return ChatResponse(
            answer=final_state.get("generation", "No response generated."),
            query=request.message,
            transformed_query=final_state.get("transformed_query"),
            sub_queries=final_state.get("sub_queries", []),
            route_decision=final_state.get("route", "vectorstore"),
            sources=sources,
            traces=traces,
            web_search_used=bool(web_results),
            web_results=web_results,
            hallucination_detected=(final_state.get("hallucination_verdict") == "hallucinated"),
            groundedness_score=final_state.get("groundedness_score", 1.0),
            faithfulness_verdict=final_state.get("hallucination_verdict", "grounded"),
            retries=final_state.get("retry_count", 0)
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Streaming Server-Sent Events (SSE) endpoint:
    Streams each node execution step in real-time to visualize graph transitions.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    async def event_generator() -> AsyncGenerator[str, None]:
        initial_state = {
            "original_query": request.message,
            "current_query": request.message,
            "traces": [],
            "documents": [],
            "graded_documents": [],
            "web_results": [],
            "web_search_needed": False,
            "retry_count": 0,
            "model": request.model or settings.GROQ_MODEL,
            "temperature": request.temperature or 0.2,
            "mode": request.mode or "adaptive_crag_self_rag"
        }

        try:
            # Yield initial started event
            yield f"data: {json.dumps({'event': 'started', 'query': request.message})}\n\n"

            # Stream graph execution
            final_state = dict(initial_state)
            for event in crag_graph.stream(initial_state):
                for node_name, node_output in event.items():
                    final_state.update(node_output)
                    # Find newly added trace
                    latest_trace = None
                    if "traces" in node_output and node_output["traces"]:
                        latest_trace = node_output["traces"][-1]

                    payload = {
                        "event": "node_update",
                        "node": node_name,
                        "trace": latest_trace,
                        "web_search_needed": final_state.get("web_search_needed", False)
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            # Yield final completion
            sources = []
            for d in final_state.get("graded_documents", []) or final_state.get("documents", []):
                sources.append({
                    "content": d.get("content", ""),
                    "source": d.get("source", "Document"),
                    "page": d.get("page", 1),
                    "chunk_index": d.get("chunk_index", 0),
                    "relevance_score": d.get("relevance_score"),
                    "grade": d.get("grade", "relevant")
                })

            final_payload = {
                "event": "completed",
                "answer": final_state.get("generation", ""),
                "transformed_query": final_state.get("transformed_query"),
                "sub_queries": final_state.get("sub_queries", []),
                "route": final_state.get("route", "vectorstore"),
                "sources": sources,
                "web_results": final_state.get("web_results", []),
                "hallucination_detected": (final_state.get("hallucination_verdict") == "hallucinated"),
                "groundedness_score": final_state.get("groundedness_score", 1.0),
                "retries": final_state.get("retry_count", 0),
                "traces": final_state.get("traces", [])
            }
            yield f"data: {json.dumps(final_payload)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            err_payload = {"event": "error", "error": str(e)}
            yield f"data: {json.dumps(err_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
