"""
Markus AI — Projects API Routes (§8, §9)

/api/projects — create, list, and manage developer projects
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from domain.entities import Project, ProjectStatus

router = APIRouter(prefix="/api/projects", tags=["Projects"])

# In-memory store for projects
_projects: dict[str, Project] = {
    "default": Project(
        id="default",
        name="Markus AI Workspace",
        description="Active Markus AI Assistant workspace",
        path=".",
        language="Python / TypeScript",
    )
}


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    path: str = "."
    language: str = "python"
    framework: Optional[str] = None


@router.get("")
@router.get("/")
async def list_projects():
    """List all workspace projects."""
    return {
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "path": p.path,
                "language": p.language,
                "framework": p.framework,
                "status": p.status.value,
                "created_at": p.created_at,
            }
            for p in _projects.values()
        ]
    }


@router.post("")
@router.post("/")
async def create_project(request: CreateProjectRequest):
    """Register a new workspace project."""
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Project name cannot be empty")

    proj = Project(
        name=request.name,
        description=request.description,
        path=request.path,
        language=request.language,
        framework=request.framework,
    )
    _projects[proj.id] = proj
    return {
        "status": "created",
        "project": {
            "id": proj.id,
            "name": proj.name,
            "path": proj.path,
        }
    }


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    proj = _projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": proj.id,
        "name": proj.name,
        "description": proj.description,
        "path": proj.path,
        "language": proj.language,
        "framework": proj.framework,
        "status": proj.status.value,
        "created_at": proj.created_at,
    }
