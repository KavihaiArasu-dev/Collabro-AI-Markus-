"""
Markus AI — RAG Retriever & Knowledge Augmenter (§6b)
Searches VectorStore and builds clean prompt context for the AI Assistant.
"""

from __future__ import annotations

import logging
from typing import List, Tuple
from rag.vector_store import vector_store
from domain.entities import RAGSearchResult

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Retrieves top-k context chunks and formats system prompt injection."""

    def __init__(self, default_top_k: int = 3, similarity_threshold: float = 0.12):
        self.default_top_k = default_top_k
        self.similarity_threshold = similarity_threshold

    def retrieve(self, query: str, top_k: int = 3) -> List[RAGSearchResult]:
        """Search relevant chunks for a user query."""
        results = vector_store.similarity_search(query, top_k=top_k)
        # Filter by threshold
        filtered = [r for r in results if r.similarity_score >= self.similarity_threshold]
        return filtered

    def build_rag_context(self, query: str, top_k: int = 3) -> Tuple[str, List[RAGSearchResult]]:
        """
        Build formatted RAG knowledge context string for system prompt.
        """
        matches = self.retrieve(query, top_k=top_k)
        if not matches:
            return ("", [])

        lines = [
            "--- KNOWLEDGE BASE CONTEXT (From User's Documents) ---",
            "Use the following excerpts to answer the user's question accurately when relevant:",
        ]

        for idx, match in enumerate(matches, 1):
            lines.append(f"\n[Source #{idx}: {match.chunk.doc_name} (Relevance {int(match.similarity_score * 100)}%)]")
            lines.append(match.chunk.text.strip())

        lines.append("--- END KNOWLEDGE BASE CONTEXT ---")
        return ("\n".join(lines), matches)


rag_retriever = RAGRetriever()
