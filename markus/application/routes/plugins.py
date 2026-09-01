"""
Markus AI — Plugins API Routes (§9)

/api/plugins — plugin marketplace and lifecycle management
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from plugins.plugin_manager import plugin_manager, PluginMetadata

router = APIRouter(prefix="/api/plugins", tags=["Plugins"])


class TogglePluginRequest(BaseModel):
    enabled: bool


@router.get("")
@router.get("/")
async def list_plugins():
    """List all available plugins and extensions."""
    return {"plugins": plugin_manager.list_plugins()}


@router.get("/{name}")
async def get_plugin(name: str):
    """Get details of a specific plugin."""
    plugin = plugin_manager.get_plugin(name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
    return {
        "name": plugin.name,
        "version": plugin.version,
        "description": plugin.description,
        "author": plugin.author,
        "enabled": plugin.enabled,
        "tools_provided": plugin.tools_provided,
    }


@router.post("/{name}/toggle")
async def toggle_plugin(name: str, request: TogglePluginRequest):
    """Enable or disable a plugin."""
    success = plugin_manager.toggle_plugin(name, request.enabled)
    if not success:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
    return {"status": "ok", "name": name, "enabled": request.enabled}
