"""
Markus AI — Workflows API Routes (§9)

/api/workflows — CRUD and execution for automated workflows
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from workflows.workflow_engine import workflow_engine

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


class CreateWorkflowRequest(BaseModel):
    name: str
    description: str = ""
    trigger_type: str = "manual"
    steps: list[dict[str, Any]] = []


@router.get("")
@router.get("/")
async def list_workflows():
    """List all registered workflows."""
    return {"workflows": workflow_engine.list_workflows()}


@router.post("")
@router.post("/")
async def create_workflow(request: CreateWorkflowRequest):
    """Create a new workflow."""
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Workflow name cannot be empty")

    wf = workflow_engine.create_workflow(
        name=request.name,
        description=request.description,
        steps=request.steps,
        trigger_type=request.trigger_type,
    )
    return {
        "status": "created",
        "workflow": {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "steps_count": len(wf.steps),
        }
    }


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow details."""
    wf = workflow_engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": wf.id,
        "name": wf.name,
        "description": wf.description,
        "trigger_type": wf.trigger_type.value,
        "is_active": wf.is_active,
        "steps": [
            {
                "id": s.id,
                "name": s.name,
                "agent": s.agent,
                "tool": s.tool,
                "status": s.status.value,
            }
            for s in wf.steps
        ],
    }
