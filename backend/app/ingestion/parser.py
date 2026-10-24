import io
import os
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger("rag.parser")

class DocumentParser:
    """
    Parses various document formats (PDF, DOCX, TXT, MD, CSV) into structured text pages.
    """

    @staticmethod
    def parse_file(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Extracts content from uploaded bytes, returning a list of page dicts:
        [{ "page": 1, "text": "..." }, ...]
        """
        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            return DocumentParser._parse_pdf(file_bytes)
        elif ext in [".docx", ".doc"]:
            return DocumentParser._parse_docx(file_bytes)
        elif ext in [".txt", ".md", ".markdown", ".csv", ".json", ".log"]:
            return DocumentParser._parse_plain_text(file_bytes)
        else:
            # Fallback to UTF-8 text decoding
            return DocumentParser._parse_plain_text(file_bytes)

    @staticmethod
    def _parse_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
        pages = []
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                clean_text = text.strip()
                if clean_text:
                    pages.append({"page": i + 1, "text": clean_text})
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            # Fallback plain decode
            pages.append({"page": 1, "text": file_bytes.decode("utf-8", errors="ignore")})
        return pages or [{"page": 1, "text": ""}]

    @staticmethod
    def _parse_docx(file_bytes: bytes) -> List[Dict[str, Any]]:
        pages = []
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())
            pages.append({"page": 1, "text": "\n\n".join(full_text)})
        except Exception as e:
            logger.error(f"Error parsing DOCX: {e}")
            pages.append({"page": 1, "text": file_bytes.decode("utf-8", errors="ignore")})
        return pages

    @staticmethod
    def _parse_plain_text(file_bytes: bytes) -> List[Dict[str, Any]]:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="ignore")
        return [{"page": 1, "text": text.strip()}]
