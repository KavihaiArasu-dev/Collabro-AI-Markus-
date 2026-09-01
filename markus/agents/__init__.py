"""Markus AI — Agents package."""

from .base_agent import BaseAgent, AgentTask
from .orchestrator import orchestrator, Orchestrator
from .implementations import (
    CoderAgent, ArchitectAgent, ReviewerAgent, DebugAgent,
    ResearchAgent, DocumentationAgent, UIUXAgent, AutomationAgent, MemoryAgent,
)

__all__ = [
    "BaseAgent", "AgentTask",
    "orchestrator", "Orchestrator",
    "CoderAgent", "ArchitectAgent", "ReviewerAgent", "DebugAgent",
    "ResearchAgent", "DocumentationAgent", "UIUXAgent", "AutomationAgent", "MemoryAgent",
]
