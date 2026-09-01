"""
Markus AI — RAG API Routes
Endpoints for ingesting documents, querying knowledge base, and inspecting vectors.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from rag.document_loader import document_loader
from rag.retriever import rag_retriever
from rag.vector_store import vector_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["RAG"])


class IngestTextRequest(BaseModel):
    title: str
    content: str


class QueryRAGRequest(BaseModel):
    query: str
    top_k: Optional[int] = 4


@router.post("/ingest-text")
async def ingest_text(request: IngestTextRequest):
    """Ingest raw text or markdown into RAG knowledge store."""
    chunks = document_loader.ingest_text(request.content, request.title)
    return {
        "status": "success",
        "doc_name": request.title,
        "chunks_created": len(chunks),
        "total_indexed_chunks": len(vector_store.chunks),
    }


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and ingest a file (.txt, .md, .py, .pdf, .json) into RAG knowledge."""
    try:
        content_bytes = await file.read()
        filename = file.filename or "uploaded_doc.txt"
        text = content_bytes.decode("utf-8", errors="ignore")
        chunks = document_loader.ingest_text(text, filename)
        return {
            "status": "success",
            "filename": filename,
            "chunks_created": len(chunks),
            "total_indexed_chunks": len(vector_store.chunks),
        }
    except Exception as e:
        logger.error(f"Upload RAG error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_rag(request: QueryRAGRequest):
    """Search knowledge base for relevant chunks."""
    results = rag_retriever.retrieve(request.query, top_k=request.top_k or 4)
    context_str, _ = rag_retriever.build_rag_context(request.query, top_k=request.top_k or 4)
    return {
        "query": request.query,
        "results_count": len(results),
        "results": [
            {
                "chunk_id": r.chunk.chunk_id,
                "doc_name": r.chunk.doc_name,
                "similarity_score": r.similarity_score,
                "text": r.chunk.text,
            }
            for r in results
        ],
        "context_prompt": context_str,
    }


@router.get("/documents")
async def list_documents():
    """List all indexed document names in RAG knowledge."""
    return {
        "documents": vector_store.get_document_names(),
        "total_chunks": len(vector_store.chunks),
    }


@router.delete("/clear")
async def clear_rag():
    """Clear all documents from RAG memory."""
    vector_store.clear()
    return {"status": "success", "message": "Cleared all RAG knowledge"}
