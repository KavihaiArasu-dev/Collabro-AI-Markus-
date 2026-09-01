"""
Markus AI — Global Search API Routes (§9)

/api/search — unified search across memory, RAG documents, and project files
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from memory.memory_manager import memory_manager
from rag.retriever import rag_retriever
from tools.tool_router import tool_router

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("")
@router.get("/")
async def global_search(q: str, limit: int = 5):
    """Unified search across memory, knowledge base, and files."""
    if not q.strip():
        return {"memories": [], "rag": [], "files": []}

    memories = memory_manager.recall(query=q, limit=limit)
    rag_results = rag_retriever.query(query_text=q, top_k=limit)
    files_res = await tool_router.execute("search_files", {"directory": ".", "query": q})
    files = files_res.get("result", []) if files_res["success"] else []

    return {
        "query": q,
        "memories": memories,
        "rag": rag_results,
        "files": files[:limit],
    }
