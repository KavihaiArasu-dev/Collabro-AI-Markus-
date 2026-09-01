"""
Markus AI — Planner (§10, §11a)

Breaks complex requests into step-by-step plans before execution.
Every plan step goes through the Permission Manager before the Tool Router
can execute it: LLM → Planner → Permission Manager → Tool Router → OS
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    agent_type: str = "orchestrator"
    tool_name: Optional[str] = None
    tool_arguments: dict = field(default_factory=dict)
    risk_level: str = "low"
    status: PlanStepStatus = PlanStepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class ExecutionPlan:
    """A complete execution plan with ordered steps."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    steps: list[PlanStep] = field(default_factory=list)
    status: str = "created"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    current_step_index: int = 0

    @property
    def current_step(self) -> Optional[PlanStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == PlanStepStatus.COMPLETED)
        return completed / len(self.steps)

    @property
    def is_complete(self) -> bool:
        return all(s.status in (PlanStepStatus.COMPLETED, PlanStepStatus.SKIPPED) for s in self.steps)


class Planner:
    """
    Plans multi-step executions for complex requests.

    For simple chat messages, no plan is needed — the request goes
    directly to the LLM. For complex requests (system control,
    multi-agent workflows, automation), the planner breaks the task
    into discrete steps, each with a clear agent assignment and risk level.
    """

    def __init__(self):
        self._active_plans: dict[str, ExecutionPlan] = {}
        logger.info("Planner initialized")

    def create_plan(self, goal: str, steps: list[dict]) -> ExecutionPlan:
        """
        Create an execution plan from a list of step descriptions.

        Args:
            goal: High-level description of what we're trying to accomplish.
            steps: List of dicts with keys: description, agent_type, tool_name,
                   tool_arguments, risk_level.
        """
        plan_steps = []
        for step_data in steps:
            plan_steps.append(PlanStep(
                description=step_data.get("description", ""),
                agent_type=step_data.get("agent_type", "orchestrator"),
                tool_name=step_data.get("tool_name"),
                tool_arguments=step_data.get("tool_arguments", {}),
                risk_level=step_data.get("risk_level", "low"),
            ))

        plan = ExecutionPlan(goal=goal, steps=plan_steps)
        self._active_plans[plan.id] = plan
        logger.info(f"Plan created: {plan.id} — {goal} ({len(plan_steps)} steps)")
        return plan

    def create_simple_plan(self, goal: str, agent_type: str = "orchestrator") -> ExecutionPlan:
        """Create a single-step plan for simple requests."""
        return self.create_plan(goal, [{
            "description": goal,
            "agent_type": agent_type,
            "risk_level": "low",
        }])

    def advance_step(self, plan_id: str, result: Optional[str] = None) -> Optional[PlanStep]:
        """Mark the current step as completed and advance to the next."""
        plan = self._active_plans.get(plan_id)
        if not plan or not plan.current_step:
            return None

        current = plan.current_step
        current.status = PlanStepStatus.COMPLETED
        current.result = result
        current.completed_at = datetime.now().isoformat()

        plan.current_step_index += 1

        if plan.is_complete:
            plan.status = "completed"
            plan.completed_at = datetime.now().isoformat()
            logger.info(f"Plan {plan_id} completed")
            return None

        next_step = plan.current_step
        if next_step:
            next_step.status = PlanStepStatus.IN_PROGRESS
            next_step.started_at = datetime.now().isoformat()

        return next_step

    def fail_step(self, plan_id: str, error: str) -> None:
        """Mark the current step as failed."""
        plan = self._active_plans.get(plan_id)
        if plan and plan.current_step:
            plan.current_step.status = PlanStepStatus.FAILED
            plan.current_step.error = error
            plan.status = "failed"
            logger.error(f"Plan {plan_id} step failed: {error}")

    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get an active plan by ID."""
        return self._active_plans.get(plan_id)

    def list_active_plans(self) -> list[ExecutionPlan]:
        """List all active plans."""
        return [p for p in self._active_plans.values() if p.status not in ("completed", "failed")]

    def cleanup_completed(self, max_age_hours: int = 24):
        """Remove old completed/failed plans."""
        to_remove = []
        for pid, plan in self._active_plans.items():
            if plan.status in ("completed", "failed"):
                to_remove.append(pid)
        for pid in to_remove:
            del self._active_plans[pid]


# Singleton
planner = Planner()
