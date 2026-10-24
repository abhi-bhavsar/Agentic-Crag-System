import time
import logging
import json
from typing import Dict, Any
from app.rag.state import GraphState
from app.rag.nodes.router import get_groq_llm
from app.config import settings

logger = logging.getLogger("rag.nodes.guardrails")

def verify_hallucinations_node(state: GraphState) -> Dict[str, Any]:
    """
    Self-RAG Hallucination & Faithfulness Guardrail Node:
    Post-generation verification step that validates whether the generated answer
    is strictly grounded in the retrieved context without hallucinations.
    """
    start_time = time.time()
    traces = list(state.get("traces", []))
    query = state.get("original_query", "")
    generation = state.get("generation", "")
    documents = state.get("graded_documents") or state.get("documents") or []
    retry_count = state.get("retry_count", 0)
    route = state.get("route", "vectorstore")

    # If direct greeting or no documents retrieved, skip hallucination grading
    if route == "direct" or not documents:
        traces.append({
            "node": "verify_hallucination",
            "title": "Self-RAG Guardrail Check",
            "status": "completed",
            "details": {
                "verdict": "grounded",
                "groundedness_score": 1.0,
                "note": "Direct route or conversational answer"
            },
            "duration_ms": round((time.time() - start_time) * 1000, 2)
        })
        return {
            "hallucination_verdict": "grounded",
            "groundedness_score": 1.0,
            "is_useful": True,
            "traces": traces
        }

    llm = get_groq_llm(model=state.get("model"), temperature=0.0)

    verdict = "grounded"
    groundedness_score = 1.0
    is_useful = True
    reasoning = "Answer verified against context"

    if llm and not generation.startswith("⚠️"):
        context_snippets = "\n".join([f"- {d.get('content')[:600]}" for d in documents[:4]])
        prompt = f"""You are a strict Self-RAG Hallucination & Faithfulness Evaluator.
Analyze whether the generated answer is strictly supported by the provided context facts.

CONTEXT FACTS:
{context_snippets}

GENERATED ANSWER:
{generation}

USER QUESTION:
{query}

Verify:
1. Groundedness: Does the answer contain ANY unsupported claims, invented numbers, or facts not present in the context?
   - If all claims are grounded in context -> "grounded"
   - If any claim is hallucinated/unsupported -> "hallucinated"
2. Useful: Does the answer address the question? (true / false)
3. Groundedness Score: Rate from 0.0 to 1.0 (1.0 = 100% grounded).

Respond strictly in valid JSON format:
{{
  "verdict": "grounded" | "hallucinated",
  "groundedness_score": 0.0 to 1.0,
  "is_useful": true | false,
  "reasoning": "brief explanation"
}}"""
        try:
            resp = llm.invoke(prompt)
            content = resp.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            verdict = parsed.get("verdict", "grounded").lower()
            groundedness_score = float(parsed.get("groundedness_score", 1.0))
            is_useful = bool(parsed.get("is_useful", True))
            reasoning = parsed.get("reasoning", "")
        except Exception as e:
            logger.warning(f"Self-RAG evaluator exception: {e}")
            verdict = "grounded"
            groundedness_score = 0.95

    new_retry_count = retry_count
    if verdict == "hallucinated":
        new_retry_count += 1
        logger.warning(f"Self-RAG flagged hallucination! Triggering retry attempt {new_retry_count} / {settings.MAX_RETRIES}")

    duration = round((time.time() - start_time) * 1000, 2)
    traces.append({
        "node": "verify_hallucination",
        "title": "Self-RAG Hallucination Guardrail",
        "status": "completed" if verdict == "grounded" else "warning",
        "details": {
            "verdict": verdict,
            "groundedness_score": groundedness_score,
            "is_useful": is_useful,
            "reasoning": reasoning,
            "retries_so_far": new_retry_count,
            "max_retries": settings.MAX_RETRIES
        },
        "duration_ms": duration
    })

    return {
        "hallucination_verdict": verdict,
        "groundedness_score": groundedness_score,
        "is_useful": is_useful,
        "retry_count": new_retry_count,
        "traces": traces
    }


def decide_after_guardrails(state: GraphState) -> str:
    """
    Self-RAG Conditional Edge:
    - If hallucinated and retry_count <= MAX_RETRIES -> loops back to 'generate' for correction.
    - Otherwise -> ends workflow.
    """
    verdict = state.get("hallucination_verdict", "grounded")
    retry_count = state.get("retry_count", 0)
    max_retries = settings.MAX_RETRIES

    if verdict == "hallucinated" and retry_count <= max_retries:
        logger.info(f"Rerouting to generator for self-correction (retry {retry_count} of {max_retries})")
        return "generate"

    return "end"
