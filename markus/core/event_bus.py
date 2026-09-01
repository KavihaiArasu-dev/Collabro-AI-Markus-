"""
Markus AI — Event Bus (§10)

Internal pub/sub event bus for agent communication and system-wide notifications.
Agents communicate using structured messages through this bus.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """A structured event message."""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    type: str = ""
    source: str = ""
    target: Optional[str] = None  # None = broadcast
    data: Any = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# Event handler type
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Async pub/sub event bus for inter-agent and system communication.

    Agents publish events (e.g., "task completed", "need code review")
    and other agents or system components subscribe to event types
    they care about.
    """

    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._event_history: list[Event] = []
        self._max_history = 1000
        logger.info("Event Bus initialized")

    def subscribe(self, event_type: str, handler: EventHandler):
        """Subscribe a handler to an event type."""
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to '{event_type}': {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: EventHandler):
        """Unsubscribe a handler from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    async def publish(self, event: Event):
        """Publish an event to all subscribers of its type."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        handlers = self._subscribers.get(event.type, [])
        wildcard_handlers = self._subscribers.get("*", [])  # Catch-all subscribers

        all_handlers = handlers + wildcard_handlers

        if not all_handlers:
            logger.debug(f"Event '{event.type}' published with no subscribers")
            return

        # Fire all handlers concurrently
        tasks = [asyncio.create_task(handler(event)) for handler in all_handlers]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Event handler error for '{event.type}': {result}")

    async def emit(self, event_type: str, source: str, data: Any = None, target: Optional[str] = None):
        """Convenience method to create and publish an event."""
        event = Event(type=event_type, source=source, data=data, target=target)
        await self.publish(event)

    def get_history(self, event_type: Optional[str] = None, limit: int = 50) -> list[Event]:
        """Get recent event history, optionally filtered by type."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]


# Singleton
event_bus = EventBus()
