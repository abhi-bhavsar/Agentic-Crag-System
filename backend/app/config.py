from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Application Settings loaded from environment or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ---------------------------------------------------------
    # Groq API Configuration
    # ---------------------------------------------------------
    GROQ_API_KEY: str = Field(default="", description="Groq API Key")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Groq LLM Model")

    # ---------------------------------------------------------
    # Free HuggingFace Embeddings
    # ---------------------------------------------------------
    EMBEDDING_MODEL_NAME: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Local HuggingFace embedding model"
    )
    HUGGINGFACE_API_KEY: Optional[str] = Field(default=None)

    # ---------------------------------------------------------
    # PostgreSQL + pgvector Configuration
    # >>> USER INSERTION MARKER: PostgreSQL Connection Settings <<<
    # ---------------------------------------------------------
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="postgres", description="PostgreSQL password")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="rag_db", description="PostgreSQL database name")
    POSTGRES_SSLMODE: str = Field(default="disable", description="PostgreSQL SSL mode")

    # Vector store backend: 'auto' (preferred), 'postgres', or 'chroma'
    VECTOR_STORE_BACKEND: str = Field(default="auto")

    # ---------------------------------------------------------
    # Web Search Fallback Tool
    # ---------------------------------------------------------
    TAVILY_API_KEY: Optional[str] = Field(default=None)

    # ---------------------------------------------------------
    # CRAG & Self-RAG Thresholds
    # ---------------------------------------------------------
    CRAG_RELEVANCE_THRESHOLD: float = Field(default=0.6, description="Relevance score threshold")
    MAX_RETRIES: int = Field(default=2, description="Max self-correction loops")
    RETRIEVAL_TOP_K: int = Field(default=4, description="Number of chunks to retrieve")

    # ---------------------------------------------------------
    # Server & Paths
    # ---------------------------------------------------------
    BACKEND_HOST: str = Field(default="0.0.0.0")
    BACKEND_PORT: int = Field(default=8000)
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    CHROMA_DIR: Path = BASE_DIR / "chroma_db"
    DEBUG: bool = Field(default=True)

    @property
    def postgres_dsn(self) -> str:
        """Constructs standard PostgreSQL connection string."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            f"?sslmode={self.POSTGRES_SSLMODE}"
        )

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.CHROMA_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
