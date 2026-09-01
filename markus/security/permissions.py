"""
Markus AI — Permission Manager (§11a)

Architectural rule: an LLM response alone must never authorize a destructive action.
Chain: LLM → Planner → Permission Manager → Tool Router → OS
(Not: LLM → shell directly)

This module decides whether a tool action is allowed, needs confirmation,
or is blocked, based on the tool's risk level and the permission defaults.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from config.constants import (
    RiskLevel, PermissionDecision, PERMISSION_DEFAULTS,
)

logger = logging.getLogger(__name__)


@dataclass
class PermissionRequest:
    """A request for permission to execute an action."""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    action: str = ""
    tool_name: str = ""
    arguments: dict = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    description: str = ""
    requested_by: str = ""  # Which agent/component requested this
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    decision: Optional[PermissionDecision] = None
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None  # "auto" or "user"


class PermissionManager:
    """
    Gate-keeper that enforces the permission chain.

    Every tool execution must pass through here. Based on the tool's
    risk level and the configured permission defaults:
    - LOW risk: auto-allow
    - MEDIUM risk: auto-allow or ask depending on context
    - HIGH risk: always ask for user confirmation

    The permission request is stored and can be responded to via
    the WebSocket (for the frontend to show a confirmation dialog).
    """

    def __init__(self):
        self._pending_requests: dict[str, PermissionRequest] = {}
        self._audit_log: list[PermissionRequest] = []
        self._custom_overrides: dict[str, PermissionDecision] = {}
        logger.info("Permission Manager initialized")

    def check_permission(
        self,
        action: str,
        tool_name: str,
        arguments: dict,
        risk_level: RiskLevel,
        requested_by: str = "",
        description: str = "",
    ) -> PermissionRequest:
        """
        Check if an action is permitted.

        Returns a PermissionRequest with the decision set:
        - ALLOW: proceed immediately
        - ASK: need user confirmation (request is stored as pending)
        - BLOCK: action is not permitted at all

        Args:
            action: The action name (e.g., "delete_file", "execute_shell")
            tool_name: The tool that would execute this action
            arguments: The arguments to the tool
            risk_level: The risk level of the action
            requested_by: Which agent/component is requesting
            description: Human-readable description of what this action does
        """
        request = PermissionRequest(
            action=action,
            tool_name=tool_name,
            arguments=arguments,
            risk_level=risk_level,
            description=description,
            requested_by=requested_by,
        )

        # Check custom overrides first
        if action in self._custom_overrides:
            request.decision = self._custom_overrides[action]
            request.decided_at = datetime.now().isoformat()
            request.decided_by = "auto (custom override)"
            self._log_decision(request)
            return request

        # Check defaults
        default = PERMISSION_DEFAULTS.get(action)
        if default:
            if default == PermissionDecision.ALLOW:
                request.decision = PermissionDecision.ALLOW
                request.decided_at = datetime.now().isoformat()
                request.decided_by = "auto (default)"
                self._log_decision(request)
                return request
            elif default == PermissionDecision.BLOCK:
                request.decision = PermissionDecision.BLOCK
                request.decided_at = datetime.now().isoformat()
                request.decided_by = "auto (blocked)"
                self._log_decision(request)
                return request

        # Risk-based decision
        if risk_level == RiskLevel.LOW:
            request.decision = PermissionDecision.ALLOW
            request.decided_at = datetime.now().isoformat()
            request.decided_by = "auto (low risk)"
        elif risk_level == RiskLevel.HIGH:
            request.decision = PermissionDecision.ASK
            self._pending_requests[request.id] = request
            logger.info(f"Permission request pending: {request.id} — {action} (HIGH risk)")
        else:
            # MEDIUM — allow by default but log
            request.decision = PermissionDecision.ALLOW
            request.decided_at = datetime.now().isoformat()
            request.decided_by = "auto (medium risk)"

        self._log_decision(request)
        return request

    def approve(self, request_id: str, decided_by: str = "user") -> Optional[PermissionRequest]:
        """Approve a pending permission request."""
        request = self._pending_requests.pop(request_id, None)
        if request:
            request.decision = PermissionDecision.ALLOW
            request.decided_at = datetime.now().isoformat()
            request.decided_by = decided_by
            self._log_decision(request)
            logger.info(f"Permission approved: {request_id} — {request.action}")
        return request

    def deny(self, request_id: str, decided_by: str = "user") -> Optional[PermissionRequest]:
        """Deny a pending permission request."""
        request = self._pending_requests.pop(request_id, None)
        if request:
            request.decision = PermissionDecision.BLOCK
            request.decided_at = datetime.now().isoformat()
            request.decided_by = decided_by
            self._log_decision(request)
            logger.info(f"Permission denied: {request_id} — {request.action}")
        return request

    def get_pending_requests(self) -> list[PermissionRequest]:
        """Get all pending permission requests."""
        return list(self._pending_requests.values())

    def set_override(self, action: str, decision: PermissionDecision):
        """Set a custom override for an action."""
        self._custom_overrides[action] = decision
        logger.info(f"Permission override set: {action} → {decision.value}")

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """Get the audit log of all permission decisions."""
        return [
            {
                "id": r.id,
                "action": r.action,
                "tool_name": r.tool_name,
                "risk_level": r.risk_level.value,
                "decision": r.decision.value if r.decision else "pending",
                "decided_by": r.decided_by,
                "timestamp": r.timestamp,
            }
            for r in self._audit_log[-limit:]
        ]

    def _log_decision(self, request: PermissionRequest):
        """Add a decision to the audit log."""
        self._audit_log.append(request)
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]


# Singleton
permission_manager = PermissionManager()
