"""
Markus AI — Document Ingestion & Loader
Parses files (.md, .txt, .py, .json, .pdf) from data/documents or uploads.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional
from rag.chunker import DocumentChunker
from rag.vector_store import vector_store
from domain.entities import DocumentChunk

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loads and ingests documents into the RAG Vector Store."""

    def __init__(self):
        self.chunker = DocumentChunker()

    def ingest_text(self, text: str, doc_name: str) -> List[DocumentChunk]:
        """Ingest raw text content into RAG memory."""
        chunks = self.chunker.chunk_text(text, doc_name)
        if chunks:
            vector_store.add_chunks(chunks)
        return chunks

    def ingest_file(self, file_path: str) -> List[DocumentChunk]:
        """Read and ingest a file from disk."""
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return []

        doc_name = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext in [".md", ".txt", ".py", ".js", ".ts", ".json", ".html", ".css", ".yaml", ".yml"]:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                return self.ingest_text(content, doc_name)
            elif ext == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    content = "\n\n".join([page.extract_text() or "" for page in reader.pages])
                    return self.ingest_text(content, doc_name)
                except Exception as e:
                    logger.warning(f"PDF parsing error: {e}")
                    return []
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                return self.ingest_text(content, doc_name)
        except Exception as e:
            logger.error(f"Failed to ingest file {file_path}: {e}")
            return []

    def ingest_directory(self, dir_path: str = "./data/documents") -> int:
        """Ingest all supported files in a directory."""
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            return 0

        total_chunks = 0
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                chunks = self.ingest_file(file_path)
                total_chunks += len(chunks)

        logger.info(f"Ingested directory '{dir_path}': {total_chunks} total chunks created.")
        return total_chunks


document_loader = DocumentLoader()
