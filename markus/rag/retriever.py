"""
Markus AI — RAG Retriever (§6)

Retrieval-Augmented Generation pipeline:
1. Ingest documents (PDF, Markdown, Word, Text, Code)
2. Chunk documents
3. Generate embeddings
4. Store in vector database
5. Query: embed query → search vectors → return context
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from config.settings import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Processes documents for RAG ingestion."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
                           ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".sh", ".bat",
                           ".java", ".go", ".rs", ".c", ".cpp", ".h", ".sql"}

    def process_file(self, file_path: str) -> list[dict]:
        """Process a file and return chunks."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return []

        ext = path.suffix.lower()
        content = ""

        try:
            if ext == ".pdf":
                content = self._read_pdf(path)
            elif ext == ".docx":
                content = self._read_docx(path)
            elif ext in self.SUPPORTED_EXTENSIONS:
                content = path.read_text(encoding="utf-8", errors="ignore")
            else:
                logger.warning(f"Unsupported file type: {ext}")
                return []
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []

        if not content.strip():
            return []

        chunks = self._chunk_text(content, file_path)
        logger.info(f"Processed {file_path}: {len(chunks)} chunks")
        return chunks

    def _read_pdf(self, path: Path) -> str:
        """Read PDF content."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.warning("pypdf not installed, skipping PDF")
            return ""

    def _read_docx(self, path: Path) -> str:
        """Read DOCX content."""
        try:
            from docx import Document
            doc = Document(str(path))
            return "\n\n".join(para.text for para in doc.paragraphs)
        except ImportError:
            logger.warning("python-docx not installed, skipping DOCX")
            return ""

    def _chunk_text(self, text: str, source: str) -> list[dict]:
        """Split text into overlapping chunks."""
        chunk_size = settings.rag.chunk_size
        overlap = settings.rag.chunk_overlap
        chunks = []

        words = text.split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            if chunk_words:
                chunks.append({
                    "id": str(uuid4())[:12],
                    "content": " ".join(chunk_words),
                    "source": source,
                    "chunk_index": len(chunks),
                })

        return chunks


class RAGRetriever:
    """
    RAG query pipeline.

    Uses ChromaDB for vector storage when available, falls back to
    simple keyword matching for local operation without dependencies.
    """

    def __init__(self):
        self._processor = DocumentProcessor()
        self._documents: list[dict] = []  # Simple in-memory store fallback
        self._chroma_collection = None
        self._init_vector_store()
        logger.info("RAG Retriever initialized")

    def _init_vector_store(self):
        """Initialize ChromaDB if available."""
        try:
            import chromadb
            store_path = settings.rag.vector_store_path
            Path(store_path).mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=store_path)
            self._chroma_collection = client.get_or_create_collection(
                name="markus_knowledge",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB vector store initialized")
        except ImportError:
            logger.warning("ChromaDB not available, using in-memory document store")
        except Exception as e:
            logger.warning(f"ChromaDB init failed: {e}, using in-memory store")

    def ingest_file(self, file_path: str) -> int:
        """Ingest a file into the knowledge base. Returns number of chunks added."""
        chunks = self._processor.process_file(file_path)

        if not chunks:
            return 0

        if self._chroma_collection:
            self._chroma_collection.add(
                ids=[c["id"] for c in chunks],
                documents=[c["content"] for c in chunks],
                metadatas=[{"source": c["source"], "chunk_index": c["chunk_index"]} for c in chunks],
            )
        else:
            self._documents.extend(chunks)

        logger.info(f"Ingested {len(chunks)} chunks from {file_path}")
        return len(chunks)

    def ingest_directory(self, dir_path: str) -> int:
        """Ingest all supported files from a directory."""
        total = 0
        path = Path(dir_path)
        if not path.is_dir():
            return 0

        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in DocumentProcessor.SUPPORTED_EXTENSIONS | {".pdf", ".docx"}:
                total += self.ingest_file(str(file_path))

        logger.info(f"Ingested {total} total chunks from {dir_path}")
        return total

    def query(self, query_text: str, top_k: int = None) -> list[dict]:
        """
        Query the knowledge base and return relevant documents.

        Args:
            query_text: The search query.
            top_k: Number of results to return.

        Returns:
            List of dicts with 'content', 'source', 'relevance' keys.
        """
        top_k = top_k or settings.rag.top_k

        if self._chroma_collection:
            try:
                results = self._chroma_collection.query(
                    query_texts=[query_text],
                    n_results=top_k,
                )
                return [
                    {
                        "content": doc,
                        "source": meta.get("source", "unknown"),
                        "relevance": 1.0 - (dist if dist else 0),
                    }
                    for doc, meta, dist in zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0] if results.get("distances") else [0] * len(results["documents"][0]),
                    )
                ]
            except Exception as e:
                logger.error(f"ChromaDB query failed: {e}")

        # Fallback: simple keyword matching
        query_lower = query_text.lower()
        scored = []
        for doc in self._documents:
            content_lower = doc["content"].lower()
            score = sum(1 for word in query_lower.split() if word in content_lower)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"content": doc["content"], "source": doc["source"], "relevance": score / len(query_lower.split())}
            for score, doc in scored[:top_k]
        ]

    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        if self._chroma_collection:
            count = self._chroma_collection.count()
        else:
            count = len(self._documents)

        return {
            "total_chunks": count,
            "using_chromadb": self._chroma_collection is not None,
        }


# Singleton
rag_retriever = RAGRetriever()
document_processor = DocumentProcessor()
