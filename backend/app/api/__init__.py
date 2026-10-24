from fastapi import APIRouter
from .routes_chat import router as chat_router
from .routes_documents import router as documents_router
from .routes_health import router as health_router

api_router = APIRouter(prefix="/api")
api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(documents_router, tags=["Documents"])
api_router.include_router(health_router, tags=["Health & System"])

__all__ = ["api_router"]
