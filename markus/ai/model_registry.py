"""
Markus AI — Model Registry (§6a)

Maps Markus modes to OmniRoute routing aliases.
The provider behind each alias is dynamic — discovered from OmniRoute, not assumed.
"""

from __future__ import annotations

import logging
from typing import Optional

from config.constants import RouteAlias, MODEL_PROFILES

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Registry of model profiles and their OmniRoute routes.

    Markus says "give me a coding-capable response" and the registry
    resolves that to the correct OmniRoute route alias. The actual
    provider/model is OmniRoute's responsibility.
    """

    def __init__(self):
        self._profiles = dict(MODEL_PROFILES)
        self._available_models: list[dict] = []
        logger.info(f"Model registry initialized with {len(self._profiles)} profiles")

    def get_route(self, profile_name: str) -> str:
        """Get the OmniRoute route for a given profile name."""
        profile = self._profiles.get(profile_name)
        if profile:
            return profile["route"].value if hasattr(profile["route"], "value") else profile["route"]
        logger.warning(f"Unknown profile '{profile_name}', falling back to 'auto'")
        return RouteAlias.AUTO.value

    def get_profile(self, profile_name: str) -> Optional[dict]:
        """Get full profile details."""
        return self._profiles.get(profile_name)

    def list_profiles(self) -> dict[str, dict]:
        """List all available profiles."""
        return dict(self._profiles)

    def register_profile(self, name: str, route: str, description: str = ""):
        """Register a new model profile."""
        self._profiles[name] = {
            "route": route,
            "description": description,
        }
        logger.info(f"Registered model profile: {name} → {route}")

    def update_available_models(self, models: list[dict]):
        """Update the list of models discovered from OmniRoute."""
        self._available_models = models
        logger.info(f"Updated available models: {len(models)} models")

    def get_available_models(self) -> list[dict]:
        """Get the list of available models from OmniRoute."""
        return self._available_models


# Singleton
model_registry = ModelRegistry()
