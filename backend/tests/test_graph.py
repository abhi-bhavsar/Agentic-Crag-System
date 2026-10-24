import pytest
from app.rag.graph import crag_graph
from app.rag.nodes.router import transform_query_node
from app.rag.nodes.grader import grade_documents_node, decide_after_grading
from app.rag.nodes.guardrails import verify_hallucinations_node, decide_after_guardrails

def test_router_greeting_direct():
    state = {
        "original_query": "hello",
        "traces": [],
        "mode": "adaptive_crag_self_rag"
    }
    result = transform_query_node(state)
    assert result["route"] == "direct"

def test_crag_grading_relevant():
    state = {
        "original_query": "What is Python?",
        "current_query": "What is Python?",
        "documents": [
            {
                "chunk_id": "1",
                "content": "Python is a high-level, general-purpose programming language.",
                "similarity": 0.85,
                "source": "python.txt"
            },
            {
                "chunk_id": "2",
                "content": "Python supports multiple programming paradigms.",
                "similarity": 0.78,
                "source": "python.txt"
            }
        ],
        "traces": []
    }
    result = grade_documents_node(state)
    assert len(result["graded_documents"]) > 0
    # Relevant chunks >= 2 should not force web search
    assert result["web_search_needed"] is False

def test_crag_grading_insufficient_triggers_web_search():
    state = {
        "original_query": "What is quantum gravity theory in 2026?",
        "current_query": "What is quantum gravity theory in 2026?",
        "documents": [],
        "traces": []
    }
    result = grade_documents_node(state)
    assert result["web_search_needed"] is True
    decision = decide_after_grading(result)
    assert decision == "web_search"

def test_self_rag_guardrails_pass():
    state = {
        "original_query": "What is LangGraph?",
        "generation": "LangGraph is a library for building stateful, multi-actor applications with LLMs.",
        "graded_documents": [
            {"content": "LangGraph is a library for building stateful, multi-actor applications with LLMs."}
        ],
        "retry_count": 0,
        "traces": []
    }
    result = verify_hallucinations_node(state)
    assert result["hallucination_verdict"] == "grounded"
    decision = decide_after_guardrails(result)
    assert decision == "end"
