import time
import logging
import json
from typing import Dict, Any, List
from app.rag.state import GraphState
from app.config import settings

logger = logging.getLogger("rag.nodes.router")

def get_groq_llm(model: str = None, temperature: float = 0.1):
    """Initializes Groq LLM client if API key is provided."""
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_your_groq"):
        return None
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=model or settings.GROQ_MODEL,
            temperature=temperature
        )
    except Exception as e:
        logger.warning(f"Could not initialize ChatGroq: {e}")
        return None


def transform_query_node(state: GraphState) -> Dict[str, Any]:
    """
    Routing & Query Transformation Node:
    1. Analyzes the incoming prompt.
    2. Decides whether to route to Vectorstore Retrieval, Web Search, or Direct answer.
    3. Rewrites ambiguous queries into standalone, retrieval-optimized questions.
    4. Decomposes multi-part questions into sub-queries.
    """
    start_time = time.time()
    original_query = state.get("original_query", "").strip()
    mode = state.get("mode", "adaptive_crag_self_rag")

    traces = list(state.get("traces", []))
    sub_queries = []
    transformed_query = original_query
    route = "vectorstore"

    # Quick heuristic check for greetings / meta-questions
    lower_q = original_query.lower()
    is_greeting = any(lower_q.startswith(g) for g in ["hi", "hello", "hey", "who are you", "what can you do"]) and len(lower_q.split()) <= 4
    
    if is_greeting and mode != "naive_rag":
        route = "direct"
        transformed_query = original_query
    elif mode == "web_search_only":
        route = "web_search"
    else:
        # Use LLM for intelligent query transformation if Groq is available
        llm = get_groq_llm(model=state.get("model"), temperature=0.1)
        if llm:
            prompt = f"""You are an advanced query analysis and routing module for an agentic RAG system.
Given the user prompt below:
1. Route: Choose 'vectorstore' (if the query seeks factual knowledge or internal documents), 'web_search' (if it explicitly asks for breaking news, current 2026/future events, or live web info), or 'direct' (if it's a simple greeting or general creative question).
2. Rewrite: Rewrite the question into a clean, standalone, keyword-rich query optimized for vector semantic search.
3. Decompose: If the user query has multiple comparison points or distinct sub-questions, extract 2-3 focused sub-queries. Otherwise, return an empty list.

User Prompt: "{original_query}"

Respond strictly in valid JSON format:
{{
  "route": "vectorstore" | "web_search" | "direct",
  "transformed_query": "standalone search query",
  "sub_queries": ["sub query 1", "sub query 2"],
  "reasoning": "brief reason"
}}"""
            try:
                response = llm.invoke(prompt)
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                parsed = json.loads(content)
                route = parsed.get("route", "vectorstore")
                transformed_query = parsed.get("transformed_query", original_query)
                sub_queries = parsed.get("sub_queries", [])
            except Exception as e:
                logger.warning(f"LLM query transformation fallback: {e}")
                # Fallback rule-based
                transformed_query = original_query
                route = "vectorstore"
        else:
            # Deterministic heuristic fallback
            transformed_query = original_query
            if any(term in lower_q for term in ["today", "latest news", "weather", "current stock"]):
                route = "web_search"
            else:
                route = "vectorstore"

    duration = round((time.time() - start_time) * 1000, 2)
    traces.append({
        "node": "query_transform",
        "title": "Routing & Query Transformation",
        "status": "completed",
        "details": {
            "original_query": original_query,
            "transformed_query": transformed_query,
            "sub_queries": sub_queries,
            "route_decision": route
        },
        "duration_ms": duration
    })

    return {
        "current_query": transformed_query,
        "transformed_query": transformed_query,
        "sub_queries": sub_queries,
        "route": route,
        "traces": traces
    }


def route_query(state: GraphState) -> str:
    """
    Conditional edge selector based on router decision.
    """
    return state.get("route", "vectorstore")
