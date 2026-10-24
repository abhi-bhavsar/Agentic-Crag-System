from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict, total=False):
    """
    Represents the operational state of the Adaptive CRAG + Self-RAG pipeline.
    """
    original_query: str
    current_query: str
    transformed_query: Optional[str]
    sub_queries: List[str]
    route: str # "vectorstore", "web_search", "direct"
    
    # Retrieved & Graded Docs
    documents: List[Dict[str, Any]]
    graded_documents: List[Dict[str, Any]]
    
    # Web search fallback
    web_search_needed: bool
    web_results: List[Dict[str, Any]]
    
    # Generation & Self-RAG verification
    generation: str
    hallucination_verdict: str # "grounded", "hallucinated"
    groundedness_score: float
    is_useful: bool
    retry_count: int
    
    # Execution diagnostics for frontend visualizer
    traces: List[Dict[str, Any]]
    
    # User model and config overrides
    model: Optional[str]
    temperature: float
    mode: str
