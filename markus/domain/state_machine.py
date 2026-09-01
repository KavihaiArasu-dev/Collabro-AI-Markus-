"""
Markus AI — Conversation & Assistant State Machine (§2, §3)
"""

from __future__ import annotations

from enum import Enum
import logging
from typing import Set

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    IDLE = "idle"
    ACTIVATED = "activated"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class InvalidTransitionError(Exception):
    """Raised when an illegal state machine transition is attempted."""
    pass


class StateMachine:
    """Manages strictly validated state transitions for Markus Assistant."""

    VALID_TRANSITIONS: dict[ConversationState, Set[ConversationState]] = {
        ConversationState.IDLE: {ConversationState.ACTIVATED, ConversationState.LISTENING, ConversationState.ERROR},
        ConversationState.ACTIVATED: {ConversationState.LISTENING, ConversationState.IDLE, ConversationState.ERROR},
        ConversationState.LISTENING: {ConversationState.THINKING, ConversationState.IDLE, ConversationState.ERROR},
        ConversationState.THINKING: {ConversationState.SPEAKING, ConversationState.IDLE, ConversationState.ERROR},
        ConversationState.SPEAKING: {ConversationState.IDLE, ConversationState.LISTENING, ConversationState.ERROR},
        ConversationState.ERROR: {ConversationState.IDLE},
    }

    def __init__(self, initial_state: ConversationState = ConversationState.IDLE):
        self._current_state = initial_state

    @property
    def current_state(self) -> ConversationState:
        return self._current_state

    def transition_to(self, new_state: ConversationState) -> ConversationState:
        if new_state == self._current_state:
            return self._current_state

        allowed = self.VALID_TRANSITIONS.get(self._current_state, set())
        if new_state not in allowed:
            err_msg = f"Cannot transition from {self._current_state.value} to {new_state.value}. Valid: {[s.value for s in allowed]}"
            logger.warning(err_msg)
            raise InvalidTransitionError(err_msg)

        logger.debug(f"State transition: {self._current_state.value} -> {new_state.value}")
        self._current_state = new_state
        return self._current_state
