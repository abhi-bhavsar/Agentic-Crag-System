"""
Database Module for PostgreSQL + pgvector with Graceful Local ChromaDB Fallback.

================================================================================
>>> USER INSERTION MARKER: POSTGRESQL & PGADMIN CREDENTIALS <<<
You can configure your PostgreSQL credentials in .env:
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=your_password
  POSTGRES_HOST=localhost
  POSTGRES_PORT=5432
  POSTGRES_DB=rag_db
================================================================================
"""

import logging
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger("rag.database")

# Try importing PostgreSQL / SQLAlchemy components
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from sqlalchemy import create_engine, text
    PG_AVAILABLE = True
except ImportError:
    PG_AVAILABLE = False
    logger.warning("psycopg2 / sqlalchemy not installed. PostgreSQL mode will be disabled.")

# Try importing ChromaDB components for local vector fallback
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("chromadb not installed.")


class DatabaseManager:
    """
    Manages Vector Storage and Document Metadata across PostgreSQL (pgvector)
    and Local ChromaDB fallback.
    """

    def __init__(self):
        self.backend = "unknown"
        self.is_connected = False
        self.pg_engine = None
        self.chroma_client = None
        self.chroma_collection = None
        self.doc_metadata_cache: Dict[str, Dict[str, Any]] = {}

        # Initialize storage backend
        self.initialize()

    def test_postgres_connection(self) -> Tuple[bool, str]:
        """
        Tests if PostgreSQL is reachable and pgvector extension is available.
        """
        if not PG_AVAILABLE:
            return False, "psycopg2 / sqlalchemy packages not installed."

        try:
            # >>> USER INSERTION POINT: CONNECTING TO POSTGRESQL <<<
            engine = create_engine(
                settings.postgres_dsn,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3}
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1;"))
            return True, "PostgreSQL connected successfully."
        except Exception as e:
            return False, f"PostgreSQL connection failed: {str(e)}"

    def initialize_postgres(self) -> bool:
        """
        Initializes PostgreSQL schema and pgvector extension.
        """
        try:
            logger.info(f"Connecting to PostgreSQL at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
            self.pg_engine = create_engine(
                settings.postgres_dsn,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )

            with self.pg_engine.connect() as conn:
                # 1. Enable pgvector extension
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

                # 2. Document Master Table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id VARCHAR(64) PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        file_type VARCHAR(50) NOT NULL,
                        file_size INTEGER NOT NULL,
                        chunk_count INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """))

                # 3. Document Chunks Table with Vector(384) for all-MiniLM-L6-v2 embeddings
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id VARCHAR(64) PRIMARY KEY,
                        document_id VARCHAR(64) REFERENCES documents(id) ON DELETE CASCADE,
                        chunk_index INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                        embedding vector(384)
                    );
                """))

                # 4. Create vector search index (HNSW for fast cosine similarity)
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS doc_chunks_embedding_hnsw_idx 
                        ON document_chunks USING hnsw (embedding vector_cosine_ops);
                    """))
                except Exception as idx_err:
                    logger.warning(f"HNSW index creation note: {idx_err}")

                conn.commit()

            self.backend = "postgres_pgvector"
            self.is_connected = True
            logger.info("Successfully initialized PostgreSQL with pgvector!")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            return False

    def initialize_chroma(self) -> bool:
        """
        Initializes local persistent ChromaDB as fallback or standalone storage.
        """
        if not CHROMA_AVAILABLE:
            logger.error("ChromaDB is not installed and PostgreSQL is unavailable.")
            return False

        try:
            settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(
                path=str(settings.CHROMA_DIR),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name="rag_knowledge_base",
                metadata={"hnsw:space": "cosine"}
            )
            self.backend = "chroma_local"
            self.is_connected = True
            logger.info(f"Initialized local ChromaDB storage at {settings.CHROMA_DIR}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            return False

    def initialize(self):
        """
        Auto-detection:
        If VECTOR_STORE_BACKEND is 'postgres', strictly use PostgreSQL.
        If VECTOR_STORE_BACKEND is 'chroma', use ChromaDB.
        If VECTOR_STORE_BACKEND is 'auto', test PostgreSQL; if available, use it;
        otherwise fall back to local ChromaDB with clear notifications.
        """
        mode = settings.VECTOR_STORE_BACKEND.lower()

        if mode == "postgres":
            if not self.initialize_postgres():
                raise ConnectionError("PostgreSQL required by configuration but failed to initialize.")
        elif mode == "chroma":
            self.initialize_chroma()
        else: # 'auto'
            pg_ok, _ = self.test_postgres_connection()
            if pg_ok and self.initialize_postgres():
                logger.info("Auto-detected active PostgreSQL + pgvector instance.")
            else:
                logger.info("PostgreSQL not active or reachable. Gracefully using local ChromaDB fallback.")
                self.initialize_chroma()

    # -------------------------------------------------------------------------
    # Document Metadata CRUD
    # -------------------------------------------------------------------------
    def save_document(
        self,
        doc_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        chunk_count: int
    ) -> None:
        """Saves document record in database."""
        if self.backend == "postgres_pgvector" and self.pg_engine:
            with self.pg_engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO documents (id, filename, file_type, file_size, chunk_count, created_at)
                        VALUES (:id, :filename, :file_type, :file_size, :chunk_count, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO UPDATE SET
                            filename = EXCLUDED.filename,
                            chunk_count = EXCLUDED.chunk_count;
                    """),
                    {
                        "id": doc_id,
                        "filename": filename,
                        "file_type": file_type,
                        "file_size": file_size,
                        "chunk_count": chunk_count
                    }
                )
                conn.commit()
        else:
            # Memory cache for Chroma fallback
            self.doc_metadata_cache[doc_id] = {
                "id": doc_id,
                "filename": filename,
                "file_type": file_type,
                "file_size": file_size,
                "chunk_count": chunk_count,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

    def list_documents(self) -> List[Dict[str, Any]]:
        """Lists all ingested documents."""
        if self.backend == "postgres_pgvector" and self.pg_engine:
            try:
                with self.pg_engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT id, filename, file_type, file_size, chunk_count, created_at 
                        FROM documents 
                        ORDER BY created_at DESC;
                    """))
                    docs = []
                    for row in result:
                        docs.append({
                            "id": row.id,
                            "filename": row.filename,
                            "file_type": row.file_type,
                            "file_size": row.file_size,
                            "chunk_count": row.chunk_count,
                            "created_at": row.created_at.isoformat() if row.created_at else ""
                        })
                    return docs
            except Exception as e:
                logger.error(f"Error querying Postgres documents: {e}")
                return list(self.doc_metadata_cache.values())
        else:
            return list(self.doc_metadata_cache.values())

    def delete_document(self, doc_id: str) -> bool:
        """Deletes a document and its associated vector chunks."""
        if self.backend == "postgres_pgvector" and self.pg_engine:
            try:
                with self.pg_engine.connect() as conn:
                    conn.execute(
                        text("DELETE FROM documents WHERE id = :doc_id;"),
                        {"doc_id": doc_id}
                    )
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error deleting Postgres document {doc_id}: {e}")
                return False
        else:
            if self.chroma_collection:
                try:
                    self.chroma_collection.delete(where={"document_id": doc_id})
                except Exception as e:
                    logger.warning(f"Chroma delete chunks: {e}")
            self.doc_metadata_cache.pop(doc_id, None)
            return True

    # -------------------------------------------------------------------------
    # Vector Chunks Ingestion & Search
    # -------------------------------------------------------------------------
    def insert_chunks(
        self,
        doc_id: str,
        chunks: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """Inserts text chunks and their embeddings."""
        if not chunks:
            return

        if self.backend == "postgres_pgvector" and self.pg_engine:
            with self.pg_engine.connect() as conn:
                for idx, (content, emb, meta) in enumerate(zip(chunks, embeddings, metadatas)):
                    chunk_id = f"{doc_id}_{idx}"
                    # Format embedding list as string for pgvector: '[0.1, 0.2, ...]'
                    emb_str = f"[{','.join(str(f) for f in emb)}]"
                    conn.execute(
                        text("""
                            INSERT INTO document_chunks (id, document_id, chunk_index, content, metadata, embedding)
                            VALUES (:id, :doc_id, :idx, :content, :meta, :emb)
                            ON CONFLICT (id) DO UPDATE SET
                                content = EXCLUDED.content,
                                metadata = EXCLUDED.metadata,
                                embedding = EXCLUDED.embedding;
                        """),
                        {
                            "id": chunk_id,
                            "doc_id": doc_id,
                            "idx": idx,
                            "content": content,
                            "meta": json.dumps(meta),
                            "emb": emb_str
                        }
                    )
                conn.commit()
            logger.info(f"Inserted {len(chunks)} chunks into PostgreSQL pgvector for doc {doc_id}")
        else:
            if self.chroma_collection:
                ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
                # Chroma requires flat primitive metadata
                clean_metas = []
                for m in metadatas:
                    cm = {}
                    for k, v in m.items():
                        cm[k] = str(v) if not isinstance(v, (str, int, float, bool)) else v
                    clean_metas.append(cm)

                self.chroma_collection.add(
                    ids=ids,
                    documents=chunks,
                    embeddings=embeddings,
                    metadatas=clean_metas
                )
                logger.info(f"Inserted {len(chunks)} chunks into local ChromaDB for doc {doc_id}")

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Performs Cosine Similarity vector search.
        Returns list of chunks with source, content, and cosine score.
        """
        results = []

        if self.backend == "postgres_pgvector" and self.pg_engine:
            try:
                emb_str = f"[{','.join(str(f) for f in query_embedding)}]"
                with self.pg_engine.connect() as conn:
                    # 1 - (embedding <=> :emb) calculates Cosine Similarity (1 is identical)
                    stmt = text("""
                        SELECT 
                            id, 
                            document_id, 
                            chunk_index, 
                            content, 
                            metadata,
                            1 - (embedding <=> :emb) AS similarity
                        FROM document_chunks
                        ORDER BY embedding <=> :emb
                        LIMIT :limit;
                    """)
                    rows = conn.execute(stmt, {"emb": emb_str, "limit": top_k}).fetchall()
                    for r in rows:
                        meta = r.metadata if isinstance(r.metadata, dict) else json.loads(r.metadata or "{}")
                        results.append({
                            "chunk_id": r.id,
                            "document_id": r.document_id,
                            "chunk_index": r.chunk_index,
                            "content": r.content,
                            "source": meta.get("source", "Document"),
                            "page": meta.get("page", 1),
                            "similarity": float(r.similarity) if r.similarity is not None else 0.0,
                            "metadata": meta
                        })
                return results
            except Exception as e:
                logger.error(f"Error during PostgreSQL vector search: {e}")
                # Fallback to chroma if postgres query fails
                if self.chroma_collection:
                    return self._chroma_search(query_embedding, top_k)
                return []
        else:
            return self._chroma_search(query_embedding, top_k)

    def _chroma_search(self, query_embedding: List[float], top_k: int) -> List[Dict[str, Any]]:
        if not self.chroma_collection:
            return []
        try:
            res = self.chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            results = []
            if res and res.get("documents") and len(res["documents"]) > 0:
                docs = res["documents"][0]
                metas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(docs)
                dists = res["distances"][0] if res.get("distances") else [0.5] * len(docs)
                ids = res["ids"][0] if res.get("ids") else [""] * len(docs)

                for doc_text, meta, dist, cid in zip(docs, metas, dists, ids):
                    # Chroma cosine distance is in [0, 2], similarity = 1 - (distance / 2) or 1 - dist
                    sim = max(0.0, 1.0 - float(dist))
                    results.append({
                        "chunk_id": cid,
                        "document_id": meta.get("document_id", ""),
                        "chunk_index": meta.get("chunk_index", 0),
                        "content": doc_text,
                        "source": meta.get("source", "Document"),
                        "page": int(meta.get("page", 1)),
                        "similarity": round(sim, 4),
                        "metadata": meta
                    })
            return results
        except Exception as e:
            logger.error(f"Error during ChromaDB vector search: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Returns database statistics for health endpoint."""
        total_docs = 0
        total_chunks = 0
        if self.backend == "postgres_pgvector" and self.pg_engine:
            try:
                with self.pg_engine.connect() as conn:
                    doc_r = conn.execute(text("SELECT COUNT(*) FROM documents;")).scalar()
                    chunk_r = conn.execute(text("SELECT COUNT(*) FROM document_chunks;")).scalar()
                    total_docs = int(doc_r or 0)
                    total_chunks = int(chunk_r or 0)
            except Exception:
                pass
        else:
            total_docs = len(self.doc_metadata_cache)
            if self.chroma_collection:
                try:
                    total_chunks = self.chroma_collection.count()
                except Exception:
                    pass

        return {
            "backend": self.backend,
            "is_connected": self.is_connected,
            "total_documents": total_docs,
            "total_chunks": total_chunks
        }


# Global singleton instance
db_manager = DatabaseManager()
