"""
Markus AI — Models API Routes

/api/models — exposes current OmniRoute routing aliases and live provider resolution
"""

from __future__ import annotations

from fastapi import APIRouter

from ai.model_registry import model_registry
from ai.routing_policy import routing_policy
from core.model_router import model_router

router = APIRouter(prefix="/api/models", tags=["Models"])


@router.get("")
@router.get("/")
async def get_models():
    """Get current OmniRoute routing aliases and available models."""
    status = await model_router.check_gateway_status()
    return {
        "gateway": status,
        "profiles": model_registry.list_profiles(),
        "tiers": routing_policy.get_tier_info(),
    }


@router.get("/status")
@router.get("/status/")
async def gateway_status():
    """Check OmniRoute gateway connection status."""
    return await model_router.check_gateway_status()
