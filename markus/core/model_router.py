"""
Markus AI — Model Router (§6a)

The Markus-level policy layer that decides *what kind* of model
capability is needed, then delegates to OmniRoute.

This is the bridge between core intelligence (context, intent, plan)
and the AI gateway (OmniRoute client).
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Optional

from ai.omniroute_client import omniroute_client
from ai.routing_policy import routing_policy, RoutingContext
from config.constants import IntentType, AGENT_DEFAULT_ROUTES, AgentType

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    MarkusModelRouter — decides which OmniRoute route to use based on
    task type, privacy, latency, and complexity, then calls OmniRoute.

    This is the single point through which all agent model calls flow:
    Agent → ModelRouter → OmniRoute → Provider
    """

    async def generate(
        self,
        messages: list[dict],
        task_type: str = "chat",
        privacy: str = "normal",
        latency: str = "balanced",
        complexity: str = "normal",
        agent_type: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Route a request through OmniRoute based on context.

        The routing priority (from §6a):
        1. Agent-specific override (if agent has a default route)
        2. Privacy == local → /offline
        3. Task type == coding → /coding
        4. Latency == fast → /fast
        5. Complexity == high → /smart
        6. Default → auto
        """
        route = self._resolve_route(task_type, privacy, latency, complexity, agent_type)

        logger.info(f"Model Router: route={route}, task={task_type}, agent={agent_type}")

        return await omniroute_client.generate(
            messages=messages,
            route=route,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )

    async def generate_stream(
        self,
        messages: list[dict],
        task_type: str = "chat",
        privacy: str = "normal",
        latency: str = "balanced",
        complexity: str = "normal",
        agent_type: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream a routed response from OmniRoute."""
        route = self._resolve_route(task_type, privacy, latency, complexity, agent_type)

        logger.info(f"Model Router (stream): route={route}, task={task_type}, agent={agent_type}")

        async for token in omniroute_client.generate_stream(
            messages=messages,
            route=route,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        ):
            yield token

    def _resolve_route(
        self,
        task_type: str,
        privacy: str,
        latency: str,
        complexity: str,
        agent_type: Optional[str],
    ) -> str:
        """Resolve the final OmniRoute route."""
        # Check agent-specific default first
        if agent_type:
            try:
                at = AgentType(agent_type)
                if at in AGENT_DEFAULT_ROUTES:
                    agent_route = AGENT_DEFAULT_ROUTES[at].value
                    logger.debug(f"Using agent default route: {agent_type} → {agent_route}")
                    # Agent default can be overridden by explicit context
                    if privacy == "local" or task_type in ("coding", "code") or \
                       latency == "fast" or complexity == "high":
                        pass  # Fall through to context-based routing
                    else:
                        return agent_route
            except ValueError:
                pass

        # Context-based routing
        context = RoutingContext(
            task_type=task_type,
            privacy=privacy,
            latency=latency,
            complexity=complexity,
            agent_type=agent_type,
        )
        return routing_policy.resolve_route(context)

    def resolve_routing_details(
        self,
        task_type: str = "chat",
        privacy: str = "normal",
        latency: str = "balanced",
        complexity: str = "normal",
        agent_type: Optional[str] = None,
    ) -> dict:
        """
        Resolve full routing decision details including route, rationale, and tier info.
        Does not invoke the backend model.
        """
        route = self._resolve_route(task_type, privacy, latency, complexity, agent_type)
        rationale = "default"
        if privacy == "local":
            rationale = "Privacy-first offline routing rule"
        elif task_type in ("coding", "code"):
            rationale = "Code generation & refactoring routing rule"
        elif latency == "fast":
            rationale = "Low-latency fast execution routing rule"
        elif complexity == "high":
            rationale = "High-complexity adaptive reasoning routing rule"
        elif agent_type:
            rationale = f"Agent default routing rule ({agent_type})"

        tier_info = "Tier A (General)" if route in ("auto", "/smart") else (
            "Tier B (Fast)" if route in ("/fast", "/cheap") else "Tier C (Local/Offline)"
        )

        return {
            "route": route,
            "rationale": rationale,
            "tier": tier_info,
            "context": {
                "task_type": task_type,
                "privacy": privacy,
                "latency": latency,
                "complexity": complexity,
                "agent_type": agent_type,
            }
        }

    async def check_gateway_status(self) -> dict:
        """Check OmniRoute gateway status and available models."""
        connected = await omniroute_client.check_connection()
        models = await omniroute_client.list_models() if connected else []

        return {
            "connected": connected,
            "gateway_url": omniroute_client._base_url,
            "available_models": models,
            "model_count": len(models),
        }


# Singleton
model_router = ModelRouter()

