"""
Markus AI — WebSocket Handler

Real-time communication for:
- Agent state updates
- Orb state changes
- Streaming responses
- Permission requests
- System metrics
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

from config.constants import AIState, WSEventType
from core.event_bus import event_bus, Event

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._current_state = AIState.IDLE

        # Subscribe to events
        event_bus.subscribe("agent_status_change", self._on_agent_status)
        event_bus.subscribe("task_routed", self._on_task_routed)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

        # Send initial state
        await self.send_personal(websocket, {
            "type": WSEventType.STATE_CHANGE.value,
            "state": self._current_state.value,
        })

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.active_connections.discard(websocket)

    async def set_state(self, state: AIState):
        """Update the AI state and broadcast to all clients."""
        self._current_state = state
        await self.broadcast({
            "type": WSEventType.STATE_CHANGE.value,
            "state": state.value,
        })

    async def _on_agent_status(self, event: Event):
        """Handle agent status change events."""
        await self.broadcast({
            "type": WSEventType.AGENT_UPDATE.value,
            "data": event.data,
        })

    async def _on_task_routed(self, event: Event):
        """Handle task routed events."""
        await self.broadcast({
            "type": WSEventType.AGENT_UPDATE.value,
            "data": event.data,
        })

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


# Singleton
ws_manager = ConnectionManager()
