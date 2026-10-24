import time
import logging
import json
from typing import Dict, Any, List
from app.rag.state import GraphState
from app.config import settings
from app.rag.nodes.router import get_groq_llm

logger = logging.getLogger("rag.nodes.grader")

def grade_documents_node(state: GraphState) -> Dict[str, Any]:
    """
    Retrieval Grading Node (CRAG Pattern):
    Evaluates each retrieved chunk for semantic relevance and sufficiency.
    - Relevant: passes forward to generation.
    - Ambiguous / Insufficient: triggers web search fallback.
    - Irrelevant: filtered out, triggers query reformulation if no relevant docs exist.
    """
    start_time = time.time()
    traces = list(state.get("traces", []))
    query = state.get("current_query") or state.get("original_query", "")
    documents = state.get("documents", [])
    threshold = settings.CRAG_RELEVANCE_THRESHOLD

    graded_docs = []
    web_search_needed = False
    ambiguous_count = 0
    irrelevant_count = 0
    relevant_count = 0

    llm = get_groq_llm(model=state.get("model"), temperature=0.0)

    if not documents:
        # No documents retrieved at all -> definitely need web search fallback
        web_search_needed = True
        traces.append({
            "node": "grade_documents",
            "title": "CRAG Document Grading",
            "status": "warning",
            "details": {
                "message": "Zero vector documents retrieved. Triggering web search fallback.",
                "relevant_count": 0,
                "web_search_needed": True
            },
            "duration_ms": round((time.time() - start_time) * 1000, 2)
        })
        return {
            "graded_documents": [],
            "web_search_needed": True,
            "traces": traces
        }

    for doc in documents:
        content = doc.get("content", "")
        sim_score = doc.get("similarity", 0.0)

        grade = "relevant"
        score = sim_score
        reasoning = "Evaluated relevance"

        if llm:
            prompt = f"""You are an expert retrieval relevance grader for a Corrective RAG (CRAG) system.
Grade whether the following document snippet is relevant and informative for answering the user's query.

User Query: "{query}"

Document Content:
"{content[:1200]}"

Classification Guidelines:
- "relevant": The document contains facts, concepts, or details directly answering or shedding light on the query.
- "ambiguous": The document is somewhat related or tangentially mentions the topic, but is incomplete, vague, or insufficient on its own.
- "irrelevant": The document is off-topic, unrelated, or contains noisy text.

Respond strictly in valid JSON format:
{{
  "grade": "relevant" | "ambiguous" | "irrelevant",
  "score": 0.0 to 1.0,
  "reasoning": "brief justification"
}}"""
            try:
                response = llm.invoke(prompt)
                resp_text = response.content.strip()
                if "```json" in resp_text:
                    resp_text = resp_text.split("```json")[1].split("```")[0].strip()
                elif "```" in resp_text:
                    resp_text = resp_text.split("```")[1].split("```")[0].strip()

                parsed = json.loads(resp_text)
                grade = parsed.get("grade", "relevant").lower()
                score = float(parsed.get("score", sim_score))
                reasoning = parsed.get("reasoning", "")
            except Exception as e:
                logger.warning(f"CRAG LLM grading fallback: {e}")
                # Score-based fallback
                if sim_score >= threshold:
                    grade = "relevant"
                elif sim_score >= threshold - 0.2:
                    grade = "ambiguous"
                else:
                    grade = "irrelevant"
        else:
            # Deterministic heuristic based on cosine similarity
            if sim_score >= threshold:
                grade = "relevant"
                reasoning = f"Cosine similarity {sim_score:.2f} >= threshold {threshold}"
            elif sim_score >= threshold - 0.2:
                grade = "ambiguous"
                reasoning = f"Cosine similarity {sim_score:.2f} in ambiguous range"
            else:
                grade = "irrelevant"
                reasoning = f"Cosine similarity {sim_score:.2f} < threshold"

        doc_graded = dict(doc)
        doc_graded["relevance_score"] = score
        doc_graded["grade"] = grade
        doc_graded["reasoning"] = reasoning

        if grade == "relevant":
            relevant_count += 1
            graded_docs.append(doc_graded)
        elif grade == "ambiguous":
            ambiguous_count += 1
            graded_docs.append(doc_graded) # Keep for partial context, but flag for web search
        else:
            irrelevant_count += 1
            # Filtered out (CRAG noise removal)

    # CRAG Evaluation Decision:
    # 1. If any doc is ambiguous, or relevant docs < 2, or no relevant docs exist -> web search fallback
    if relevant_count == 0 or ambiguous_count > 0 or len(graded_docs) < 2:
        web_search_needed = True

    duration = round((time.time() - start_time) * 1000, 2)
    traces.append({
        "node": "grade_documents",
        "title": "CRAG Document Grading & Filtering",
        "status": "completed",
        "details": {
            "total_candidates": len(documents),
            "relevant_kept": relevant_count,
            "ambiguous_detected": ambiguous_count,
            "irrelevant_filtered": irrelevant_count,
            "web_search_fallback_triggered": web_search_needed,
            "threshold": threshold
        },
        "duration_ms": duration
    })

    return {
        "graded_documents": graded_docs,
        "web_search_needed": web_search_needed,
        "traces": traces
    }


def decide_after_grading(state: GraphState) -> str:
    """
    CRAG Conditional Edge:
    - If web_search_needed is True -> route to 'web_search'
    - Else -> route to 'generate'
    """
    if state.get("web_search_needed", False):
        return "web_search"
    return "generate"
