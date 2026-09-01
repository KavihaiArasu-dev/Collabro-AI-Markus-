"""
Markus AI — Files API Routes (§9)

/api/files — read, write, list, and search project files
"""

from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tools.tool_router import tool_router

router = APIRouter(prefix="/api/files", tags=["Files"])


class WriteFileRequest(BaseModel):
    path: str
    content: str


@router.get("/list")
async def list_files(path: str = "."):
    """List files in a directory."""
    result = await tool_router.execute("list_directory", {"path": path})
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"files": result["result"]}


@router.get("/read")
async def read_file(path: str):
    """Read contents of a file."""
    result = await tool_router.execute("read_file", {"path": path})
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"path": path, "content": result["result"]}


@router.post("/write")
async def write_file(request: WriteFileRequest):
    """Write contents to a file."""
    result = await tool_router.execute("write_file", {"path": request.path, "content": request.content})
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "ok", "message": result["result"]}


@router.get("/search")
async def search_files(query: str, directory: str = "."):
    """Search files by query."""
    result = await tool_router.execute("search_files", {"directory": directory, "query": query})
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"results": result["result"]}
