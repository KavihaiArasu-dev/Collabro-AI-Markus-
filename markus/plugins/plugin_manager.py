"""
Markus AI — Plugin Management System (§8)
Manages dynamic extensions, tools, and custom agent integrations.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    enabled: bool = True
    entry_point: Optional[str] = None
    tools_provided: list[str] = field(default_factory=list)


class PluginManager:
    """Manages the lifecycle of plugins in Markus AI."""

    def __init__(self):
        self._plugins: dict[str, PluginMetadata] = {}
        self._plugin_hooks: dict[str, list[Callable]] = {}
        logger.info("Plugin Manager initialized")

    def register_plugin(self, metadata: PluginMetadata) -> bool:
        """Register a plugin with Markus."""
        self._plugins[metadata.name] = metadata
        logger.info(f"Plugin registered: {metadata.name} (v{metadata.version})")
        return True

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all registered plugins."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "enabled": p.enabled,
                "tools_provided": p.tools_provided,
            }
            for p in self._plugins.values()
        ]

    def get_plugin(self, name: str) -> Optional[PluginMetadata]:
        """Get details for a specific plugin."""
        return self._plugins.get(name)

    def toggle_plugin(self, name: str, enabled: bool) -> bool:
        """Enable or disable a plugin."""
        if name in self._plugins:
            self._plugins[name].enabled = enabled
            logger.info(f"Plugin {name} enabled status set to: {enabled}")
            return True
        return False


# Singleton
plugin_manager = PluginManager()
