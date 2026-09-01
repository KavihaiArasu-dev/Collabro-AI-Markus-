"""
Markus AI — Settings API Routes (§9)

/api/settings — application settings and configuration inspection
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from config.settings import settings

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("")
@router.get("/")
async def get_settings():
    """Get public application configuration settings."""
    return {
        "app": {
            "host": settings.host,
            "port": settings.port,
            "env": settings.env,
            "debug": settings.debug,
            "log_level": settings.log_level,
        },
        "omniroute": {
            "base_url": settings.omniroute.base_url,
            "timeout": settings.omniroute.timeout,
        },
        "rag": {
            "embedding_model": settings.rag.embedding_model,
            "chunk_size": settings.rag.chunk_size,
            "top_k": settings.rag.top_k,
        },
        "memory": {
            "db_path": settings.memory.db_path,
        },
    }
