import time
import logging
from typing import Dict, Any, List
from app.rag.state import GraphState
from app.database import db_manager
from app.ingestion.indexer import DocumentIndexer
from app.config import settings

logger = logging.getLogger("rag.nodes.retriever")

def retrieve_node(state: GraphState) -> Dict[str, Any]:
    """
    Retrieval Node:
    Fetches candidate chunks from vector database (PostgreSQL pgvector or ChromaDB)
    using free HuggingFace embeddings (sentence-transformers/all-MiniLM-L6-v2).
    """
    start_time = time.time()
    traces = list(state.get("traces", []))
    query = state.get("current_query") or state.get("original_query", "")
    sub_queries = state.get("sub_queries", [])
    top_k = settings.RETRIEVAL_TOP_K

    all_queries = [query] + [sq for sq in sub_queries if sq.strip() and sq != query]
    retrieved_map: Dict[str, Dict[str, Any]] = {}

    for q in all_queries:
        try:
            # 1. Generate query embedding with free HuggingFace model
            query_emb = DocumentIndexer.embed_query(q)

            # 2. Vector search in PostgreSQL pgvector or local ChromaDB
            candidates = db_manager.similarity_search(query_emb, top_k=top_k)

            for cand in candidates:
                cid = cand.get("chunk_id") or f"{cand.get('source')}_{cand.get('chunk_index')}"
                if cid not in retrieved_map:
                    retrieved_map[cid] = cand
                else:
                    # Keep highest similarity score
                    if cand.get("similarity", 0) > retrieved_map[cid].get("similarity", 0):
                        retrieved_map[cid] = cand
        except Exception as e:
            logger.error(f"Error during retrieval for query '{q}': {e}")

    documents = list(retrieved_map.values())
    # Sort descending by similarity
    documents.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
    top_docs = documents[:top_k * 2]

    duration = round((time.time() - start_time) * 1000, 2)
    traces.append({
        "node": "retrieve",
        "title": "Vector Retrieval",
        "status": "completed",
        "details": {
            "query": query,
            "queries_executed": len(all_queries),
            "chunks_found": len(top_docs),
            "vector_store_backend": db_manager.backend,
            "top_similarity": top_docs[0]["similarity"] if top_docs else 0.0
        },
        "duration_ms": duration
    })

    return {
        "documents": top_docs,
        "traces": traces
    }
