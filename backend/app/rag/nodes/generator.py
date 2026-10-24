import time
import logging
from typing import Dict, Any, List
from app.rag.state import GraphState
from app.rag.nodes.router import get_groq_llm
from app.config import settings

logger = logging.getLogger("rag.nodes.generator")

def generate_node(state: GraphState) -> Dict[str, Any]:
    """
    Generation Node:
    Synthesizes the final answer using Groq API (LLaMA 3.3 70B / 8B).
    Enforces factual grounding, source citations, and Self-RAG correction prompts.
    """
    start_time = time.time()
    traces = list(state.get("traces", []))
    query = state.get("original_query", "")
    documents = state.get("graded_documents") or state.get("documents") or []
    retry_count = state.get("retry_count", 0)
    route = state.get("route", "vectorstore")

    llm = get_groq_llm(model=state.get("model"), temperature=state.get("temperature", 0.2))

    # Build context string with attribution
    context_blocks = []
    for idx, d in enumerate(documents):
        source = d.get("source", "Unknown Document")
        page = d.get("page", 1)
        content = d.get("content", "").strip()
        context_blocks.append(f"[Source {idx+1}: {source} (Page {page})]\n{content}")

    context_str = "\n\n".join(context_blocks) if context_blocks else "No relevant internal documents found."

    # Direct conversational handling
    if route == "direct" and not documents:
        if llm:
            try:
                resp = llm.invoke(f"You are an intelligent, helpful agentic assistant. Answer the user courteously and concisely: {query}")
                answer = resp.content.strip()
            except Exception as e:
                answer = f"Hello! I am your Self-Corrective & Adaptive Agentic RAG assistant. How can I assist you with your knowledge base today?"
        else:
            answer = f"Hello! I am your Self-Corrective & Adaptive Agentic RAG assistant. Insert your `GROQ_API_KEY` in `.env` to enable full LLaMA 3.3 generation."
    
    # RAG Generation
    else:
        # Check if Groq API key is active
        if not llm:
            answer = (
                "⚠️ **Groq API Key Not Configured**\n\n"
                "The Self-Corrective RAG pipeline successfully executed query transformation, vector retrieval, and CRAG document grading. "
                "To generate synthesized answers with LLaMA 3.3, please open `.env` and set:\n"
                "```env\nGROQ_API_KEY=gsk_your_actual_key_here\n```\n\n"
                f"**Retrieved Context Summary ({len(documents)} chunks found):**\n"
                + "\n\n".join([f"- **{d.get('source')}**: {d.get('content')[:180]}..." for d in documents[:3]])
            )
        else:
            self_rag_warning = ""
            if retry_count > 0:
                self_rag_warning = (
                    "\n\n[SELF-CORRECTION DIRECTIVE]: Your previous generation attempt was flagged for UNGROUNDED STATEMENTS OR HALLUCINATIONS. "
                    "You MUST strictly confine your assertions ONLY to facts explicitly stated in the context below. "
                    "Do NOT extrapolate, guess, or invent unverified information."
                )

            system_prompt = (
                "You are an enterprise-grade AI research assistant running a Self-Corrective RAG (CRAG + Self-RAG) architecture. "
                "Your objective is to provide precise, truthful, fact-based answers grounded exclusively in the provided context.\n\n"
                "Guidelines:\n"
                "1. Base your answer strictly on the provided Context Blocks. Do not hallucinate.\n"
                "2. When stating facts, cite the source using brackets like [Source: filename.pdf] or [Web: URL].\n"
                "3. If the context does not contain enough evidence to answer a question, state clearly what is known and what is missing.\n"
                "4. Maintain a clear, professional, and well-structured response with Markdown formatting."
                f"{self_rag_warning}"
            )

            user_prompt = f"""CONTEXT BLOCKS:
{context_str}

USER QUERY:
{query}

ANSWER:"""

            try:
                from langchain_core.messages import SystemMessage, HumanMessage
                messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
                response = llm.invoke(messages)
                answer = response.content.strip()
            except Exception as e:
                logger.error(f"Error calling Groq API: {e}")
                answer = f"Error during generation: {str(e)}"

    duration = round((time.time() - start_time) * 1000, 2)
    traces.append({
        "node": "generate",
        "title": f"LLM Generation (Attempt {retry_count + 1})",
        "status": "completed",
        "details": {
            "model": state.get("model") or settings.GROQ_MODEL,
            "context_chunks_used": len(documents),
            "retry_attempt": retry_count,
            "answer_preview": answer[:150] + "..." if len(answer) > 150 else answer
        },
        "duration_ms": duration
    })

    return {
        "generation": answer,
        "traces": traces
    }
