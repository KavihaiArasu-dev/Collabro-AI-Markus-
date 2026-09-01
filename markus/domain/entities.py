"""
Markus AI — Domain Entities & Core Business Objects (§7, §8)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Project:
    """Project domain entity."""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    description: str = ""
    path: str = ""
    language: str = "python"
    framework: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Task domain entity."""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    title: str = ""
    description: str = ""
    project_id: Optional[str] = None
    assigned_agent: str = "orchestrator"
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class Conversation:
    """Conversation domain entity."""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    title: str = "New Conversation"
    agent_type: str = "orchestrator"
    project_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    messages: list[dict[str, Any]] = field(default_factory=list)
