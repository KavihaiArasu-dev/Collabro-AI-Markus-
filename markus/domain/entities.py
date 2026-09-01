"""
Markus AI — Domain Entities & Value Objects (§1, §2)
Clean Architecture domain models for Conversation, Perception, RAG, and Agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    role: MessageRole
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value if isinstance(self.role, MessageRole) else str(self.role),
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class FaceIdentity:
    track_id: int
    name: str = "Unknown"
    is_owner: bool = False
    confidence: float = 0.80
    expression: str = "neutral"
    expression_confidence: float = 0.85
    bbox: Dict[str, int] = field(default_factory=dict)
    normalized_bbox: Dict[str, float] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_name: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class RAGSearchResult:
    chunk: DocumentChunk
    similarity_score: float
    excerpt: str


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    BUILDING = "building"
    ERROR = "error"


@dataclass
class Project:
    name: str
    id: str = field(default_factory=lambda: str(datetime.now().timestamp()).replace(".", ""))
    description: str = ""
    path: str = "."
    language: str = "python"
    framework: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

