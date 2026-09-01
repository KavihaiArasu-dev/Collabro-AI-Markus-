"""
Markus AI — Lightweight Embedded Vector Store
Provides fast in-memory embedding storage, persistent JSON save/load, and cosine similarity ranking.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple
from domain.entities import DocumentChunk, RAGSearchResult

logger = logging.getLogger(__name__)

STORE_PATH = os.path.join("data", "vector_store.json")


class VectorStore:
    """
    In-memory vector store with TF-IDF / term-frequency sparse embeddings.
    Zero external native dependencies required; persists to disk.
    """

    def __init__(self, storage_path: str = STORE_PATH):
        self.storage_path = storage_path
        self.chunks: Dict[str, DocumentChunk] = {}
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self._load_store()

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text)]

    def _compute_tf_vector(self, tokens: List[str]) -> Dict[str, float]:
        counts = Counter(tokens)
        total = len(tokens) or 1
        return {term: count / total for term, count in counts.items()}

    def _recalculate_idf(self):
        doc_count = len(self.chunks)
        if doc_count == 0:
            self.idf = {}
            return

        doc_freq: Counter[str] = Counter()
        for chunk in self.chunks.values():
            tokens = set(self._tokenize(chunk.text))
            doc_freq.update(tokens)

        self.idf = {
            term: math.log((1.0 + doc_count) / (1.0 + freq)) + 1.0
            for term, freq in doc_freq.items()
        }

    def _embed_text(self, text: str) -> Dict[str, float]:
        tokens = self._tokenize(text)
        tf = self._compute_tf_vector(tokens)
        vector: Dict[str, float] = {}
        norm_sq = 0.0

        for term, tf_val in tf.items():
            idf_val = self.idf.get(term, 1.0)
            val = tf_val * idf_val
            vector[term] = val
            norm_sq += val * val

        # L2 normalize
        norm = math.sqrt(norm_sq) or 1.0
        return {t: v / norm for t, v in vector.items()}

    def add_chunks(self, chunks: List[DocumentChunk]):
        """Add new chunks to the vector store and update index."""
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk

        self._recalculate_idf()
        self._save_store()
        logger.info(f"VectorStore: Indexed {len(chunks)} chunks (Total: {len(self.chunks)})")

    def similarity_search(self, query: str, top_k: int = 4) -> List[RAGSearchResult]:
        """Search top-k most relevant chunks using cosine similarity."""
        if not self.chunks or not query.strip():
            return []

        query_vec = self._embed_text(query)
        scores: List[Tuple[str, float]] = []

        for chunk_id, chunk in self.chunks.items():
            chunk_vec = self._embed_text(chunk.text)
            # Dot product of normalized vectors = cosine similarity
            dot_product = sum(
                query_vec[term] * chunk_vec[term]
                for term in query_vec
                if term in chunk_vec
            )
            # Exact keyword boost
            query_lower = query.lower()
            if any(word in chunk.text.lower() for word in query_lower.split() if len(word) > 3):
                dot_product += 0.15

            if dot_product > 0.05:
                scores.append((chunk_id, dot_product))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_results = scores[:top_k]

        results: List[RAGSearchResult] = []
        for chunk_id, score in top_results:
            chunk = self.chunks[chunk_id]
            # Excerpt snippet
            excerpt = chunk.text[:280] + ("..." if len(chunk.text) > 280 else "")
            results.append(RAGSearchResult(chunk=chunk, similarity_score=round(score, 3), excerpt=excerpt))

        return results

    def clear(self):
        """Clear all indexed documents."""
        self.chunks.clear()
        self.idf.clear()
        self._save_store()

    def get_document_names(self) -> List[str]:
        return list({c.doc_name for c in self.chunks.values()})

    def _save_store(self):
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = {
                chunk_id: {
                    "chunk_id": c.chunk_id,
                    "doc_name": c.doc_name,
                    "text": c.text,
                    "metadata": c.metadata,
                }
                for chunk_id, c in self.chunks.items()
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save VectorStore: {e}")

    def _load_store(self):
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chunks = {
                    cid: DocumentChunk(
                        chunk_id=item["chunk_id"],
                        doc_name=item["doc_name"],
                        text=item["text"],
                        metadata=item.get("metadata", {}),
                    )
                    for cid, item in data.items()
                }
                self._recalculate_idf()
        except Exception as e:
            logger.warning(f"Failed to load VectorStore: {e}")
            self.chunks = {}


vector_store = VectorStore()
