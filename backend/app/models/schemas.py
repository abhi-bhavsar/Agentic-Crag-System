from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

class NodeTrace(BaseModel):
    """Execution trace of an individual node in the CRAG / Self-RAG graph."""
    node: str = Field(..., description="Node identifier (e.g. router, grader, web_search)")
    title: str = Field(..., description="Human-friendly step description")
    status: str = Field("completed", description="Status: 'completed', 'warning', 'skipped', 'failed'")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostics, scores, or decisions")
    duration_ms: float = Field(0.0, description="Execution time in milliseconds")

class DocumentChunk(BaseModel):
    """A retrieved chunk with CRAG relevance grading."""
    content: str
    source: str
    page: Optional[int] = None
    chunk_index: Optional[int] = None
    relevance_score: Optional[float] = None
    grade: Optional[str] = "relevant" # "relevant", "ambiguous", "irrelevant"
    reasoning: Optional[str] = None

class ChatRequest(BaseModel):
    """User query payload."""
    message: str = Field(..., min_length=1, description="User question or instruction")
    model: Optional[str] = Field(None, description="Groq model override (e.g. llama-3.3-70b-versatile)")
    temperature: Optional[float] = Field(0.2, ge=0.0, le=1.0)
    mode: Optional[str] = Field(
        "adaptive_crag_self_rag",
        description="Mode: 'adaptive_crag_self_rag', 'naive_rag', 'web_search_only'"
    )
    conversation_id: Optional[str] = Field(None, description="Session tracking id")

class WebSearchResult(BaseModel):
    """External search result from DuckDuckGo / Tavily fallback."""
    title: str
    snippet: str
    link: str

class ChatResponse(BaseModel):
    """Rich response containing generated answer, CRAG/Self-RAG traces, and sources."""
    answer: str
    query: str
    transformed_query: Optional[str] = None
    sub_queries: List[str] = Field(default_factory=list)
    route_decision: str = "vectorstore" # "vectorstore", "web_search", "direct"
    sources: List[DocumentChunk] = Field(default_factory=list)
    traces: List[NodeTrace] = Field(default_factory=list)
    web_search_used: bool = False
    web_results: List[WebSearchResult] = Field(default_factory=list)
    hallucination_detected: bool = False
    groundedness_score: Optional[float] = 1.0
    faithfulness_verdict: str = "grounded"
    retries: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DocumentItem(BaseModel):
    """Metadata of an ingested document."""
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    created_at: str

class DocumentUploadResponse(BaseModel):
    """Response after document parsing and vector indexing."""
    document_id: str
    filename: str
    chunk_count: int
    status: str = "indexed"
    message: str

class HealthStatus(BaseModel):
    """System health check and database connection diagnostic."""
    status: str
    groq_configured: bool
    groq_model: str
    embedding_model: str
    vector_db_backend: str # 'postgres_pgvector' or 'chroma_local'
    vector_db_connected: bool
    postgres_status: Dict[str, Any]
    total_documents: int
    total_chunks: int
