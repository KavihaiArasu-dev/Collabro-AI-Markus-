"""
Markus AI — RAG Document Chunker
Splits text and code into overlapping semantic windows.
"""

from __future__ import annotations

import re
from typing import List
from domain.entities import DocumentChunk


class DocumentChunker:
    """Chunks documents into semantic windows with sliding overlap."""

    def __init__(self, chunk_size: int = 450, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, doc_name: str) -> List[DocumentChunk]:
        """Split text into chunks by paragraphs and sliding windows."""
        if not text or not text.strip():
            return []

        # Normalize line endings
        normalized = text.replace("\r\n", "\n")
        paragraphs = re.split(r"\n\s*\n", normalized)

        chunks: List[DocumentChunk] = []
        current_text = ""
        chunk_idx = 1

        for p in paragraphs:
            p_clean = p.strip()
            if not p_clean:
                continue

            if len(current_text) + len(p_clean) <= self.chunk_size:
                current_text = f"{current_text}\n\n{p_clean}".strip()
            else:
                if current_text:
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{doc_name}_chunk_{chunk_idx}",
                            doc_name=doc_name,
                            text=current_text,
                            metadata={"doc_name": doc_name, "chunk_index": chunk_idx},
                        )
                    )
                    chunk_idx += 1
                    # Retain overlap from end of current_text
                    overlap_start = max(0, len(current_text) - self.chunk_overlap)
                    overlap_part = current_text[overlap_start:]
                    current_text = f"{overlap_part}\n\n{p_clean}".strip()
                else:
                    # Single paragraph exceeds chunk_size — split by sentences
                    sentences = re.split(r"(?<=[.!?])\s+", p_clean)
                    sub_text = ""
                    for s in sentences:
                        if len(sub_text) + len(s) <= self.chunk_size:
                            sub_text = f"{sub_text} {s}".strip()
                        else:
                            if sub_text:
                                chunks.append(
                                    DocumentChunk(
                                        chunk_id=f"{doc_name}_chunk_{chunk_idx}",
                                        doc_name=doc_name,
                                        text=sub_text,
                                        metadata={"doc_name": doc_name, "chunk_index": chunk_idx},
                                    )
                                )
                                chunk_idx += 1
                            sub_text = s
                    if sub_text:
                        current_text = sub_text

        if current_text:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc_name}_chunk_{chunk_idx}",
                    doc_name=doc_name,
                    text=current_text,
                    metadata={"doc_name": doc_name, "chunk_index": chunk_idx},
                )
            )

        return chunks
