from fastapi import APIRouter
from app.models.schemas import HealthStatus
from app.database import db_manager
from app.config import settings

router = APIRouter()

@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Returns live system diagnostics, PostgreSQL connection state, and vector stats.
    """
    pg_ok, pg_msg = db_manager.test_postgres_connection()
    stats = db_manager.get_stats()
    groq_ready = bool(settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_your_groq"))

    return HealthStatus(
        status="healthy",
        groq_configured=groq_ready,
        groq_model=settings.GROQ_MODEL,
        embedding_model=settings.EMBEDDING_MODEL_NAME,
        vector_db_backend=db_manager.backend,
        vector_db_connected=db_manager.is_connected,
        postgres_status={
            "reachable": pg_ok,
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "database": settings.POSTGRES_DB,
            "user": settings.POSTGRES_USER,
            "message": pg_msg
        },
        total_documents=stats.get("total_documents", 0),
        total_chunks=stats.get("total_chunks", 0)
    )


@router.get("/system/config")
async def get_system_config():
    """
    Safe non-sensitive configuration endpoint for UI settings panel.
    """
    groq_ready = bool(settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_your_groq"))
    pg_ok, _ = db_manager.test_postgres_connection()

    return {
        "groq_configured": groq_ready,
        "default_model": settings.GROQ_MODEL,
        "available_models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ],
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "embedding_dim": 384,
        "crag_threshold": settings.CRAG_RELEVANCE_THRESHOLD,
        "max_retries": settings.MAX_RETRIES,
        "retrieval_top_k": settings.RETRIEVAL_TOP_K,
        "active_backend": db_manager.backend,
        "postgres_connected": pg_ok
    }
