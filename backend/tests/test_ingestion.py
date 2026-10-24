import pytest
from app.ingestion.parser import DocumentParser
from app.ingestion.chunker import DocumentChunker

def test_document_parser_plaintext():
    sample_text = b"This is a sample document for testing the CRAG ingestion pipeline."
    pages = DocumentParser.parse_file(sample_text, "test.txt")
    assert len(pages) == 1
    assert "CRAG ingestion pipeline" in pages[0]["text"]

def test_document_chunker():
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
    pages = [{"page": 1, "text": "Sentence one. Sentence two is longer and provides more context for chunking."}]
    chunks = chunker.split_pages(pages, doc_id="doc123", filename="test.txt")
    assert len(chunks) > 0
    assert chunks[0]["metadata"]["document_id"] == "doc123"
    assert chunks[0]["metadata"]["filename"] == "test.txt"
