"""
Markus AI — Tool Contracts & Execution Result Models

Defines formal contracts for tool execution:
- PreCondition: Assertions checked prior to tool execution
- PostCondition: Assertions evaluated by the Verifier following execution
- ExecutionResult: Standardized outcome returned by ToolRouter
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class PreCondition:
    """A pre-condition that must evaluate to True before a tool is executed."""
    name: str
    check_fn: Callable[..., bool]
    failure_message: str


@dataclass
class PostCondition:
    """An assertion specification to be verified after tool execution."""
    assertion_type: str  # e.g., 'process_running', 'process_terminated', 'file_exists', 'file_deleted'
    target_param: str    # argument key whose value is passed to the verifier (e.g., 'app_name', 'path')
    timeout: float = 2.0


@dataclass
class ExecutionResult:
    """Standardized result returned by ToolRouter and tool handlers."""
    success: bool
    verified: bool = False
    data: Any = None
    verification_details: Optional[Any] = None  # VerificationResult instance
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    output_message: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "verified": self.verified,
            "data": self.data,
            "verification_details": (
                self.verification_details.to_dict()
                if hasattr(self.verification_details, "to_dict")
                else str(self.verification_details)
            ) if self.verification_details else None,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "error": self.error,
            "output_message": self.output_message,
        }
