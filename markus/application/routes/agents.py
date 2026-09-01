"""
Markus AI — Agents API Routes

/api/agents — agent management, status, and task execution
"""

from __future__ import annotations

from fastapi import APIRouter

from agents.orchestrator import orchestrator

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("")
@router.get("/")
async def list_agents():
    """List all available agents with their status."""
    return {"agents": orchestrator.list_agents()}


@router.get("/statuses/all")
async def get_all_statuses():
    """Get status of all agents (for dashboard)."""
    return {"agents": orchestrator.get_all_agent_statuses()}


@router.get("/{agent_type}")
async def get_agent_status(agent_type: str):
    """Get the status of a specific agent."""
    status = orchestrator.get_agent_status(agent_type)
    if not status:
        return {"error": f"Agent not found: {agent_type}"}
    return status
