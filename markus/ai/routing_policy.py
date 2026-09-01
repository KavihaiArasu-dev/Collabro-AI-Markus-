"""
Markus AI — Routing Policy (§6a)

Provider tier definitions and Markus-level routing policy that sits
on top of OmniRoute's own provider-level routing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from config.constants import RouteAlias, ProviderTier, IntentType

logger = logging.getLogger(__name__)


@dataclass
class RoutingContext:
    """Context that the routing policy uses to decide which route to use."""
    task_type: str = "chat"
    privacy: str = "normal"      # normal, local
    latency: str = "balanced"    # balanced, fast
    complexity: str = "normal"   # normal, high
    agent_type: Optional[str] = None


class RoutingPolicy:
    """
    Markus-level policy layer that decides *what kind* of model capability is needed.
    OmniRoute then decides *which actual provider* serves that request.

    This implements the MarkusModelRouter pattern from §6a:
    - privacy == "local" → /offline
    - task_type == "coding" → /coding
    - latency == "fast" → /fast
    - complexity == "high" → /smart
    - else → auto
    """

    # Provider tiers for informational purposes
    TIERS = {
        ProviderTier.TIER_A: {
            "name": "General Intelligence",
            "providers": ["Gemini", "Claude", "OpenAI", "DeepSeek", "Mistral", "Qwen"],
            "use_cases": "Complex reasoning, long context, architecture, hard coding, planning",
        },
        ProviderTier.TIER_B: {
            "name": "Fast Intelligence",
            "providers": ["Groq", "Cerebras"],
            "use_cases": "Short answers, intent classification, quick tool decisions, UI commands",
        },
        ProviderTier.TIER_C: {
            "name": "Local Intelligence",
            "providers": ["Ollama", "LM Studio", "vLLM"],
            "use_cases": "Private requests, offline operation, sensitive local context, dev/testing",
        },
    }

    # Intent → route mapping
    INTENT_ROUTES = {
        IntentType.CHAT: RouteAlias.AUTO,
        IntentType.QUESTION: RouteAlias.FAST,
        IntentType.SEARCH: RouteAlias.FAST,
        IntentType.CODE: RouteAlias.CODING,
        IntentType.DEBUG: RouteAlias.SMART,
        IntentType.FILE_OPERATION: RouteAlias.FAST,
        IntentType.APP_CONTROL: RouteAlias.FAST,
        IntentType.SYSTEM_CONTROL: RouteAlias.FAST,
        IntentType.BROWSER_AUTOMATION: RouteAlias.FAST,
        IntentType.RESEARCH: RouteAlias.AUTO,
        IntentType.AUTOMATION: RouteAlias.FAST,
        IntentType.REVIEW: RouteAlias.CODING,
        IntentType.ARCHITECTURE: RouteAlias.SMART,
        IntentType.DOCUMENTATION: RouteAlias.AUTO,
        IntentType.TASK_MANAGEMENT: RouteAlias.AUTO,
        IntentType.MULTI_STEP_ACTION: RouteAlias.SMART,
        IntentType.MEMORY: RouteAlias.FAST,
        IntentType.RAG: RouteAlias.AUTO,
        IntentType.SETTINGS: RouteAlias.FAST,
    }

    def resolve_route(self, context: RoutingContext) -> str:
        """
        Resolve the OmniRoute routing alias based on task context.

        Priority order (from spec §6a):
        1. Privacy == local → /offline
        2. Task type == coding → /coding
        3. Latency == fast → /fast
        4. Complexity == high → /smart
        5. Default → auto
        """
        # Rule 1: Privacy-first
        if context.privacy == "local":
            route = RouteAlias.OFFLINE
        # Rule 2: Coding tasks
        elif context.task_type in ("coding", "code"):
            route = RouteAlias.CODING
        # Rule 3: Low-latency needs
        elif context.latency == "fast":
            route = RouteAlias.FAST
        # Rule 4: High-complexity reasoning
        elif context.complexity == "high":
            route = RouteAlias.SMART
        # Rule 5: Default
        else:
            route = RouteAlias.AUTO

        logger.debug(
            f"Route resolved: {route.value} "
            f"(task={context.task_type}, privacy={context.privacy}, "
            f"latency={context.latency}, complexity={context.complexity})"
        )
        return route.value

    def resolve_for_intent(self, intent: IntentType) -> str:
        """Quick route resolution based on intent type alone."""
        route = self.INTENT_ROUTES.get(intent, RouteAlias.AUTO)
        return route.value

    def get_tier_info(self) -> dict:
        """Get provider tier information for display."""
        return {
            tier.value: info
            for tier, info in self.TIERS.items()
        }


# Singleton
routing_policy = RoutingPolicy()
