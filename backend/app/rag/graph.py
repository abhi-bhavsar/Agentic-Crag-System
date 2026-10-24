from langgraph.graph import StateGraph, END
from app.rag.state import GraphState
from app.rag.nodes.router import transform_query_node, route_query
from app.rag.nodes.retriever import retrieve_node
from app.rag.nodes.grader import grade_documents_node, decide_after_grading
from app.rag.nodes.web_search import web_search_node
from app.rag.nodes.generator import generate_node
from app.rag.nodes.guardrails import verify_hallucinations_node, decide_after_guardrails

def build_crag_self_rag_graph():
    """
    Constructs and compiles the Adaptive CRAG + Self-RAG LangGraph State Machine.
    """
    workflow = StateGraph(GraphState)

    # 1. Register Graph Nodes
    workflow.add_node("transform_query", transform_query_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("verify_hallucination", verify_hallucinations_node)

    # 2. Set Entry Point
    workflow.set_entry_point("transform_query")

    # 3. Router Edge (Adaptive Query Routing)
    workflow.add_conditional_edges(
        "transform_query",
        route_query,
        {
            "vectorstore": "retrieve",
            "web_search": "web_search",
            "direct": "generate"
        }
    )

    # 4. Retrieval -> CRAG Document Grading
    workflow.add_edge("retrieve", "grade_documents")

    # 5. CRAG Decision Edge (Relevant vs Ambiguous/Insufficient Fallback)
    workflow.add_conditional_edges(
        "grade_documents",
        decide_after_grading,
        {
            "web_search": "web_search",
            "generate": "generate"
        }
    )

    # 6. Web Search Fallback -> Generation
    workflow.add_edge("web_search", "generate")

    # 7. Generation -> Self-RAG Hallucination Guardrail
    workflow.add_edge("generate", "verify_hallucination")

    # 8. Self-RAG Guardrail Decision (Self-Correction Loop vs Finish)
    workflow.add_conditional_edges(
        "verify_hallucination",
        decide_after_guardrails,
        {
            "generate": "generate",
            "end": END
        }
    )

    # Compile Graph
    return workflow.compile()

# Global compiled instance
crag_graph = build_crag_self_rag_graph()
