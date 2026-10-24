from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunker:
    """
    Chunks extracted document pages using semantic recursive character splitting.
    """

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def split_pages(
        self,
        pages: List[Dict[str, Any]],
        doc_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Splits pages into chunks with rich metadata.
        Returns:
            List of dicts: { "text": str, "metadata": dict }
        """
        all_chunks = []
        chunk_idx = 0

        for p in pages:
            page_num = p.get("page", 1)
            raw_text = p.get("text", "")
            if not raw_text.strip():
                continue

            sub_chunks = self.splitter.split_text(raw_text)
            for sub in sub_chunks:
                clean = sub.strip()
                if clean:
                    all_chunks.append({
                        "text": clean,
                        "metadata": {
                            "document_id": doc_id,
                            "filename": filename,
                            "source": filename,
                            "page": page_num,
                            "chunk_index": chunk_idx,
                            "char_count": len(clean)
                        }
                    })
                    chunk_idx += 1

        return all_chunks
