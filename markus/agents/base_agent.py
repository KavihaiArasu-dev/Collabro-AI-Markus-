"""
Markus AI — Base Agent (§5)

Abstract base class for all specialized agents.
Every agent inherits from this and routes model calls through the ModelRouter → OmniRoute chain.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

from config.constants import AgentType, AgentStatus, RouteAlias, AGENT_DEFAULT_ROUTES
from core.model_router import model_router
from core.event_bus import event_bus

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """A task assigned to an agent."""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    description: str = ""
    input_data: Any = None
    result: Optional[str] = None
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class BaseAgent(ABC):
    """
    Abstract base agent.

    All specialized agents (Coder, Architect, Reviewer, etc.) inherit from this.
    Model calls go through: Agent → ModelRouter → OmniRoute → Provider

    Each agent has:
    - A type (from AgentType enum)
    - A default OmniRoute route (from AGENT_DEFAULT_ROUTES)
    - A system prompt defining its personality/capabilities
    - Task processing logic
    """

    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.status = AgentStatus.IDLE
        self.current_task: Optional[AgentTask] = None
        self.task_history: list[AgentTask] = []
        self.default_route = AGENT_DEFAULT_ROUTES.get(agent_type, RouteAlias.AUTO)
        self.created_at = datetime.now().isoformat()

        logger.info(f"Agent initialized: {agent_type.value} (route: {self.default_route.value})")

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The system prompt that defines this agent's personality and capabilities."""
        ...

    @property
    def name(self) -> str:
        return self.agent_type.value

    async def process(self, user_input: str, context: Optional[dict] = None) -> str:
        """
        Process a task/message and return a response.

        This is the main entry point for agent work. It:
        1. Creates a task record
        2. Sets the agent to ACTIVE
        3. Calls the LLM via ModelRouter
        4. Records the result
        5. Returns the agent to IDLE
        """
        task = AgentTask(
            description=user_input[:200],
            input_data=user_input,
            status="in_progress",
            started_at=datetime.now().isoformat(),
        )
        self.current_task = task
        self.status = AgentStatus.ACTIVE

        await event_bus.emit("agent_status_change", self.name, {
            "agent": self.name,
            "status": "active",
            "task": task.description,
        })

        try:
            messages = [{"role": "user", "content": user_input}]

            # Add any extra context
            if context:
                context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
                messages[0]["content"] = f"Context:\n{context_str}\n\nRequest: {user_input}"

            result = await model_router.generate(
                messages=messages,
                task_type=self._get_task_type(),
                agent_type=self.agent_type.value,
                system_prompt=self.system_prompt,
            )

            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now().isoformat()

            return result

        except Exception as e:
            task.status = "failed"
            task.result = str(e)
            logger.error(f"Agent {self.name} task failed: {e}")
            return f"Error: {e}"

        finally:
            self.status = AgentStatus.IDLE
            self.current_task = None
            self.task_history.append(task)

            await event_bus.emit("agent_status_change", self.name, {
                "agent": self.name,
                "status": "idle",
            })

    async def process_stream(self, user_input: str, context: Optional[dict] = None) -> AsyncGenerator[str, None]:
        """Process a task with streaming response."""
        self.status = AgentStatus.ACTIVE
        messages = [{"role": "user", "content": user_input}]

        if context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            messages[0]["content"] = f"Context:\n{context_str}\n\nRequest: {user_input}"

        try:
            async for token in model_router.generate_stream(
                messages=messages,
                task_type=self._get_task_type(),
                agent_type=self.agent_type.value,
                system_prompt=self.system_prompt,
            ):
                yield token
        finally:
            self.status = AgentStatus.IDLE

    def _get_task_type(self) -> str:
        """Map agent type to task type for routing."""
        mapping = {
            AgentType.CODER: "coding",
            AgentType.ARCHITECT: "architecture",
            AgentType.REVIEWER: "review",
            AgentType.DEBUGGER: "debug",
            AgentType.RESEARCHER: "research",
            AgentType.DOCUMENTATION: "documentation",
            AgentType.AUTOMATION: "automation",
        }
        return mapping.get(self.agent_type, "chat")

    def get_status(self) -> dict:
        """Get agent status for display."""
        return {
            "name": self.name,
            "type": self.agent_type.value,
            "status": self.status.value,
            "route": self.default_route.value,
            "current_task": self.current_task.description if self.current_task else None,
            "tasks_completed": len(self.task_history),
            "created_at": self.created_at,
        }
