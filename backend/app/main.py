import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import settings
from app.database import db_manager

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rag.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown hooks.
    """
    logger.info("=" * 60)
    logger.info("Starting Self-Corrective & Adaptive Agentic RAG Service")
    logger.info(f"Active Vector Storage Backend: {db_manager.backend.upper()}")
    logger.info(f"Free Embedding Model: {settings.EMBEDDING_MODEL_NAME}")
    logger.info(f"Groq Model Target: {settings.GROQ_MODEL}")
    logger.info("=" * 60)
    yield
    logger.info("Shutting down RAG service.")


app = FastAPI(
    title="Self-Corrective & Adaptive Agentic RAG (CRAG + Self-RAG)",
    description=(
        "Production-ready Agentic RAG architecture featuring Query Transformation, "
        "Corrective RAG (CRAG) document relevance grading with web search fallback, "
        "and Self-RAG hallucination verification guardrails."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)

@app.get("/")
async def root():
    return JSONResponse({
        "service": "Self-Corrective & Adaptive Agentic RAG API",
        "status": "online",
        "docs": "/docs",
        "active_backend": db_manager.backend,
        "embeddings": settings.EMBEDDING_MODEL_NAME
    })
