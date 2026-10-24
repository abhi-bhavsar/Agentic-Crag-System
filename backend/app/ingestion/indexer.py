import logging
from typing import List, Dict, Any, Optional
import numpy as np

from app.config import settings
from app.database import db_manager

logger = logging.getLogger("rag.indexer")

_EMBEDDING_MODEL = None

def get_embedding_model():
    """
    Lazy singleton loader for the local free HuggingFace Embedding model:
    sentence-transformers/all-MiniLM-L6-v2 (384 dimensions, zero API cost).
    """
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading HuggingFace embedding model: {settings.EMBEDDING_MODEL_NAME}")
            _EMBEDDING_MODEL = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            logger.info("Successfully loaded HuggingFace embedding model.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")
            raise RuntimeError(f"Could not load embedding model: {e}")
    return _EMBEDDING_MODEL


class DocumentIndexer:
    """
    Indexes document chunks into Vector Database (pgvector / ChromaDB).
    """

    @staticmethod
    def embed_texts(texts: List[str]) -> List[List[float]]:
        """Generates normalized vector embeddings for a list of texts."""
        if not texts:
            return []
        model = get_embedding_model()
        # sentence-transformers encodes to numpy array
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()

    @staticmethod
    def embed_query(query: str) -> List[float]:
        """Generates a single normalized vector embedding for user query."""
        model = get_embedding_model()
        embedding = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()

    @staticmethod
    def index_document(
        doc_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        chunks: List[Dict[str, Any]]
    ) -> int:
        """
        Embeds chunks and inserts into the database.
        Returns total number of chunks indexed.
        """
        if not chunks:
            db_manager.save_document(doc_id, filename, file_type, file_size, 0)
            return 0

        chunk_texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # 1. Generate embeddings using free HuggingFace model
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks of '{filename}'...")
        embeddings = DocumentIndexer.embed_texts(chunk_texts)

        # 2. Save document record
        db_manager.save_document(doc_id, filename, file_type, file_size, len(chunks))

        # 3. Insert chunks into PostgreSQL pgvector or local ChromaDB
        db_manager.insert_chunks(doc_id, chunk_texts, embeddings, metadatas)

        logger.info(f"Successfully indexed document {doc_id} with {len(chunks)} chunks.")
        return len(chunks)
