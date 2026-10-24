import uuid
import logging
from typing import List
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import DocumentItem, DocumentUploadResponse
from app.database import db_manager
from app.ingestion.parser import DocumentParser
from app.ingestion.chunker import DocumentChunker
from app.ingestion.indexer import DocumentIndexer
from app.config import settings

logger = logging.getLogger("rag.api.documents")
router = APIRouter(prefix="/documents")

chunker = DocumentChunker(chunk_size=600, chunk_overlap=100)

@router.get("", response_model=List[DocumentItem])
async def get_documents():
    """
    Returns list of all documents ingested in PostgreSQL (pgvector) or local ChromaDB.
    """
    try:
        raw_docs = db_manager.list_documents()
        return [
            DocumentItem(
                id=d["id"],
                filename=d["filename"],
                file_type=d["file_type"],
                file_size=d["file_size"],
                chunk_count=d["chunk_count"],
                created_at=str(d.get("created_at", ""))
            )
            for d in raw_docs
        ]
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=List[DocumentUploadResponse])
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Uploads and indexes documents into the Vector Store using Free HuggingFace Embeddings.
    Supported file types: PDF, DOCX, TXT, MD, CSV, JSON.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    responses = []

    for file in files:
        filename = file.filename or "uploaded_file"
        try:
            content = await file.read()
            file_size = len(content)

            if file_size == 0:
                continue

            doc_id = str(uuid.uuid4())[:8]
            ext = Path(filename).suffix.lower()

            # 1. Parse document into pages
            pages = DocumentParser.parse_file(content, filename)

            # 2. Split pages into semantic chunks
            chunks = chunker.split_pages(pages, doc_id=doc_id, filename=filename)

            # 3. Generate Free HuggingFace embeddings and store
            chunk_count = DocumentIndexer.index_document(
                doc_id=doc_id,
                filename=filename,
                file_type=ext.replace(".", "").upper() or "TXT",
                file_size=file_size,
                chunks=chunks
            )

            responses.append(
                DocumentUploadResponse(
                    document_id=doc_id,
                    filename=filename,
                    chunk_count=chunk_count,
                    status="indexed",
                    message=f"Successfully parsed and embedded {chunk_count} chunks with HuggingFace MiniLM."
                )
            )

        except Exception as e:
            logger.error(f"Failed to process file '{filename}': {e}", exc_info=True)
            responses.append(
                DocumentUploadResponse(
                    document_id="",
                    filename=filename,
                    chunk_count=0,
                    status="failed",
                    message=f"Failed to ingest: {str(e)}"
                )
            )

    return responses


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Deletes a document and all its indexed vector chunks.
    """
    success = db_manager.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found or could not be deleted.")
    return {"status": "deleted", "document_id": document_id}
