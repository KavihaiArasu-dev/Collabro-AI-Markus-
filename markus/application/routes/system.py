"""
Markus AI — System & Settings API Routes

/api/system — system metrics, tools, permissions
/api/settings — app settings
"""

from __future__ import annotations

from fastapi import APIRouter

from tools.tool_router import tool_router
from security.permissions import permission_manager
from memory.memory_manager import memory_manager
from rag.retriever import rag_retriever

router = APIRouter(tags=["System"])


# ── System ──

@router.get("/api/system/metrics")
@router.get("/api/system/metrics/")
async def system_metrics():
    """Get live system metrics (CPU, RAM, GPU, disk)."""
    result = await tool_router.execute("system_info", {})
    return result.get("result", {})


@router.get("/api/system/tools")
@router.get("/api/system/tools/")
async def list_tools():
    """List all available tools."""
    return {"tools": tool_router.list_tools()}


@router.get("/api/system/permissions")
@router.get("/api/system/permissions/")
async def get_permissions():
    """Get pending permission requests and audit log."""
    return {
        "pending": [
            {
                "id": r.id,
                "action": r.action,
                "risk_level": r.risk_level.value,
                "description": r.description,
                "requested_by": r.requested_by,
                "timestamp": r.timestamp,
            }
            for r in permission_manager.get_pending_requests()
        ],
        "audit_log": permission_manager.get_audit_log(limit=50),
    }


@router.post("/api/system/permissions/{request_id}/approve")
async def approve_permission(request_id: str):
    """Approve a pending permission request."""
    result = permission_manager.approve(request_id)
    if result:
        return {"status": "approved", "action": result.action}
    return {"error": "Request not found"}


@router.post("/api/system/permissions/{request_id}/deny")
async def deny_permission(request_id: str):
    """Deny a pending permission request."""
    result = permission_manager.deny(request_id)
    if result:
        return {"status": "denied", "action": result.action}
    return {"error": "Request not found"}


# ── Memory ──

@router.get("/api/memory/stats")
@router.get("/api/memory/stats/")
async def memory_stats():
    """Get memory system statistics."""
    return memory_manager.get_stats()


# ── RAG ──

@router.get("/api/rag/stats")
@router.get("/api/rag/stats/")
async def rag_stats():
    """Get RAG knowledge base statistics."""
    return rag_retriever.get_stats()


@router.post("/api/rag/query")
@router.post("/api/rag/query/")
async def rag_query(query: dict):
    """Query the knowledge base."""
    results = rag_retriever.query(query.get("query", ""), query.get("top_k", 5))
    return {"results": results}


@router.post("/api/rag/ingest")
@router.post("/api/rag/ingest/")
async def rag_ingest(data: dict):
    """Ingest a file or directory into the knowledge base."""
    path = data.get("path", "")
    if not path:
        return {"error": "Path is required"}

    from pathlib import Path as P
    p = P(path)
    if p.is_dir():
        count = rag_retriever.ingest_directory(path)
    elif p.is_file():
        count = rag_retriever.ingest_file(path)
    else:
        return {"error": f"Path not found: {path}"}

    return {"status": "ingested", "chunks": count}
