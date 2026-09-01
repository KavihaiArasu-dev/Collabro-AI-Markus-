"""
Markus AI — Workflow Engine & Builder (§8, §14)
Visual automation, task chains, triggers, and conditional execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    EVENT = "event"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    agent: str = "orchestrator"
    tool: Optional[str] = None
    arguments: dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None


@dataclass
class Workflow:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    description: str = ""
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_config: dict[str, Any] = field(default_factory=dict)
    steps: list[WorkflowStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True


class WorkflowEngine:
    """Coordinates and executes structured multi-step automated workflows."""

    def __init__(self):
        self._workflows: dict[str, Workflow] = {}
        self._execution_history: list[dict[str, Any]] = []
        self._seed_default_workflows()
        logger.info("Workflow Engine initialized")

    def _seed_default_workflows(self):
        """Seed starter workflows."""
        ci_workflow = Workflow(
            name="CI/CD Review & Test",
            description="Runs code review, checks git status, and runs unit tests",
            trigger_type=TriggerType.MANUAL,
            steps=[
                WorkflowStep(name="Git Status Check", agent="automation", tool="git_status"),
                WorkflowStep(name="Code Review", agent="reviewer"),
            ]
        )
        self._workflows[ci_workflow.id] = ci_workflow

    def create_workflow(self, name: str, description: str, steps: list[dict[str, Any]], trigger_type: str = "manual") -> Workflow:
        """Create and register a new workflow."""
        parsed_steps = [
            WorkflowStep(
                name=s.get("name", "Unnamed Step"),
                agent=s.get("agent", "orchestrator"),
                tool=s.get("tool"),
                arguments=s.get("arguments", {}),
                condition=s.get("condition"),
            )
            for s in steps
        ]
        wf = Workflow(
            name=name,
            description=description,
            trigger_type=TriggerType(trigger_type),
            steps=parsed_steps,
        )
        self._workflows[wf.id] = wf
        logger.info(f"Workflow created: {wf.name} ({wf.id})")
        return wf

    def list_workflows(self) -> list[dict[str, Any]]:
        """List all workflows."""
        return [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "trigger_type": w.trigger_type.value,
                "steps_count": len(w.steps),
                "created_at": w.created_at,
                "is_active": w.is_active,
            }
            for w in self._workflows.values()
        ]

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID."""
        return self._workflows.get(workflow_id)


# Singleton
workflow_engine = WorkflowEngine()
