"""
Markus AI — Agent Orchestrator (§5)

Coordinates every agent. Routes tasks, manages workflows,
handles agent communication, and resolves conflicts.
Includes a voice-command fast path for instant tool execution.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Optional

from config.constants import AgentType, IntentType
from core.intent_classifier import intent_classifier
from core.event_bus import event_bus, Event
from core.voice_command_processor import voice_command_processor
from .base_agent import BaseAgent
from .implementations import (
    CoderAgent, ArchitectAgent, ReviewerAgent, DebugAgent,
    ResearchAgent, DocumentationAgent, UIUXAgent, AutomationAgent, MemoryAgent,
)

logger = logging.getLogger(__name__)

# Map intent types to agent types
INTENT_TO_AGENT: dict[IntentType, AgentType] = {
    IntentType.CODE: AgentType.CODER,
    IntentType.DEBUG: AgentType.DEBUGGER,
    IntentType.REVIEW: AgentType.REVIEWER,
    IntentType.ARCHITECTURE: AgentType.ARCHITECT,
    IntentType.RESEARCH: AgentType.RESEARCHER,
    IntentType.QUESTION: AgentType.RESEARCHER,
    IntentType.SEARCH: AgentType.RESEARCHER,
    IntentType.DOCUMENTATION: AgentType.DOCUMENTATION,
    IntentType.AUTOMATION: AgentType.AUTOMATION,
    IntentType.FILE_OPERATION: AgentType.AUTOMATION,
    IntentType.APP_CONTROL: AgentType.AUTOMATION,
    IntentType.BROWSER_AUTOMATION: AgentType.AUTOMATION,
    IntentType.YOUTUBE: AgentType.AUTOMATION,
    IntentType.VOICE_COMMAND: AgentType.AUTOMATION,
    IntentType.MULTI_STEP_ACTION: AgentType.ARCHITECT,
    IntentType.MEMORY: AgentType.MEMORY,
    IntentType.CHAT: AgentType.RESEARCHER,
}


class Orchestrator:
    """
    The central coordinator for all agents.

    Responsibilities:
    - Try voice-command fast path for instant tool execution
    - Classify user intent
    - Route tasks to the appropriate agent
    - Coordinate multi-agent workflows (e.g., Architect → Coder → Reviewer)
    - Manage agent lifecycle
    - Handle agent communication through the event bus
    """

    def __init__(self):
        # Initialize all agents
        self._agents: dict[AgentType, BaseAgent] = {
            AgentType.CODER: CoderAgent(),
            AgentType.ARCHITECT: ArchitectAgent(),
            AgentType.REVIEWER: ReviewerAgent(),
            AgentType.DEBUGGER: DebugAgent(),
            AgentType.RESEARCHER: ResearchAgent(),
            AgentType.DOCUMENTATION: DocumentationAgent(),
            AgentType.UI_UX: UIUXAgent(),
            AgentType.AUTOMATION: AutomationAgent(),
            AgentType.MEMORY: MemoryAgent(),
        }

        logger.info(f"Orchestrator initialized with {len(self._agents)} agents")

    def get_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get an agent by type."""
        return self._agents.get(agent_type)

    def _try_voice_command(self, user_input: str) -> Optional[str]:
        """
        Try to execute as a direct voice command (fast path).

        Returns the response string if it matched, or None if the
        input should be routed to an LLM agent instead.
        """
        result = voice_command_processor.try_execute(user_input)
        if result.matched:
            logger.info(f"Voice command fast path: {result.action} → {result.response[:80]}")
            return result.response
        return None

    async def route_and_process(
        self,
        user_input: str,
        agent_type: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> str:
        """
        Route a task to the appropriate agent and return the response.

        First tries the voice-command fast path for instant execution.
        If that doesn't match, classifies intent and routes to an agent.
        """
        # ── Fast path: direct voice command execution ──
        if not agent_type:
            fast_result = self._try_voice_command(user_input)
            if fast_result is not None:
                await event_bus.emit("voice_command_executed", "orchestrator", {
                    "input": user_input[:200],
                    "result": fast_result[:200],
                })
                return fast_result

        # ── Normal path: classify and route to agent ──
        if agent_type:
            try:
                target_agent_type = AgentType(agent_type)
            except ValueError:
                return f"Unknown agent type: {agent_type}"
        else:
            intent = intent_classifier.classify(user_input)
            target_agent_type = INTENT_TO_AGENT.get(intent)

        # If no specific agent matches, default to Researcher/General Assistant
        if not target_agent_type or target_agent_type not in self._agents:
            target_agent_type = AgentType.RESEARCHER

        agent = self._agents[target_agent_type]

        await event_bus.emit("task_routed", "orchestrator", {
            "agent": target_agent_type.value,
            "input": user_input[:200],
        })

        logger.info(f"Task routed to {target_agent_type.value}: {user_input[:80]}...")
        return await agent.process(user_input, context)

    async def route_and_stream(
        self,
        user_input: str,
        agent_type: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Route and stream the response.

        For voice commands, yields the full response at once.
        For LLM tasks, streams token by token.
        """
        # ── Fast path: direct voice command execution ──
        if not agent_type:
            fast_result = self._try_voice_command(user_input)
            if fast_result is not None:
                yield fast_result
                return

        # ── Normal path ──
        if agent_type:
            try:
                target_agent_type = AgentType(agent_type)
            except ValueError:
                yield f"Unknown agent type: {agent_type}"
                return
        else:
            intent = intent_classifier.classify(user_input)
            target_agent_type = INTENT_TO_AGENT.get(intent, AgentType.RESEARCHER)

        agent = self._agents.get(target_agent_type)
        if not agent:
            yield "No agent available for this task."
            return

        async for token in agent.process_stream(user_input, context):
            yield token

    def get_all_agent_statuses(self) -> list[dict]:
        """Get status of all agents for the dashboard."""
        return [agent.get_status() for agent in self._agents.values()]

    def get_agent_status(self, agent_type: str) -> Optional[dict]:
        """Get status of a specific agent."""
        try:
            at = AgentType(agent_type)
            agent = self._agents.get(at)
            return agent.get_status() if agent else None
        except ValueError:
            return None

    def list_agents(self) -> list[dict]:
        """List all available agents with their info."""
        return [
            {
                "type": agent.agent_type.value,
                "name": agent.name,
                "status": agent.status.value,
                "route": agent.default_route.value,
                "tasks_completed": len(agent.task_history),
            }
            for agent in self._agents.values()
        ]


# Singleton
orchestrator = Orchestrator()
