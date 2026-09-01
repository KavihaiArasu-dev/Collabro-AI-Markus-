"""
Markus AI — Conversation State Machine (§6c, §8)

Manages conversation state transitions:
IDLE -> ACTIVATED -> LISTENING -> TRANSCRIBING -> PROCESSING -> RESPONDING -> SPEAKING -> IDLE
Includes wake-word cooldown and continuous-conversation mode.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from config.constants import AIState

logger = logging.getLogger(__name__)


class InvalidTransitionError(Exception):
    """Raised when an illegal state jump is attempted."""
    pass


class ConversationState:
    IDLE = "IDLE"
    ACTIVATED = "ACTIVATED"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    PROCESSING = "PROCESSING"
    RESPONDING = "RESPONDING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


VALID_TRANSITIONS: dict[str, set[str]] = {
    ConversationState.IDLE: {ConversationState.ACTIVATED, ConversationState.LISTENING, ConversationState.ERROR},
    ConversationState.ACTIVATED: {ConversationState.LISTENING, ConversationState.IDLE, ConversationState.ERROR},
    ConversationState.LISTENING: {ConversationState.TRANSCRIBING, ConversationState.IDLE, ConversationState.ERROR},
    ConversationState.TRANSCRIBING: {ConversationState.PROCESSING, ConversationState.IDLE, ConversationState.ERROR},
    ConversationState.PROCESSING: {ConversationState.RESPONDING, ConversationState.SPEAKING, ConversationState.ERROR},
    ConversationState.RESPONDING: {ConversationState.SPEAKING, ConversationState.IDLE, ConversationState.ERROR},
    ConversationState.SPEAKING: {ConversationState.IDLE, ConversationState.LISTENING, ConversationState.ERROR},
    ConversationState.ERROR: {ConversationState.IDLE, ConversationState.LISTENING},
}

STATE_TO_AISTATE: dict[str, AIState] = {
    ConversationState.IDLE: AIState.IDLE,
    ConversationState.ACTIVATED: AIState.LISTENING,
    ConversationState.LISTENING: AIState.LISTENING,
    ConversationState.TRANSCRIBING: AIState.THINKING,
    ConversationState.PROCESSING: AIState.THINKING,
    ConversationState.RESPONDING: AIState.SPEAKING,
    ConversationState.SPEAKING: AIState.SPEAKING,
    ConversationState.ERROR: AIState.ERROR,
}


class ConversationStateMachine:
    """
    Strict state machine for voice and multimodal conversation.
    Enforces valid transition paths and prevents illegal jumps.
    """

    def __init__(
        self,
        wake_word_cooldown: float = 0.8,
        continuous_conversation: bool = True,
        continuous_conversation_timeout: float = 12.0,
    ):
        self.current_state: str = ConversationState.IDLE
        self.wake_word_cooldown = wake_word_cooldown
        self.continuous_conversation = continuous_conversation
        self.continuous_conversation_timeout = continuous_conversation_timeout

        self.last_wake_word_time: float = 0.0
        self.last_speech_completed_time: float = 0.0
        self.history: list[tuple[str, float]] = [(ConversationState.IDLE, time.time())]

    @property
    def ai_state(self) -> AIState:
        """Map conversation state to UI AIState for Orb and HUD."""
        return STATE_TO_AISTATE.get(self.current_state, AIState.IDLE)

    def can_transition_to(self, next_state: str) -> bool:
        """Check if transition from current state to next state is allowed."""
        return next_state in VALID_TRANSITIONS.get(self.current_state, set())

    def transition_to(self, next_state: str, current_time: Optional[float] = None) -> str:
        """
        Transition to next state if valid, else raise InvalidTransitionError.
        """
        if not self.can_transition_to(next_state):
            msg = f"Cannot transition from {self.current_state} to {next_state}. Valid: {VALID_TRANSITIONS.get(self.current_state)}"
            logger.warning(msg)
            raise InvalidTransitionError(msg)

        now = current_time or time.time()
        prev_state = self.current_state
        self.current_state = next_state
        self.history.append((next_state, now))

        if next_state == ConversationState.ACTIVATED:
            self.last_wake_word_time = now
        elif next_state == ConversationState.IDLE and prev_state == ConversationState.SPEAKING:
            self.last_speech_completed_time = now

        logger.debug(f"ConversationState: {prev_state} -> {next_state}")
        return self.current_state

    def handle_wake_word(self, current_time: Optional[float] = None) -> bool:
        """
        Evaluate wake-word detection.
        Returns True if accepted and transitioned to ACTIVATED; False if in cooldown or illegal state.
        """
        now = current_time or time.time()
        if (now - self.last_wake_word_time) < self.wake_word_cooldown:
            logger.debug("Wake word ignored: Cooldown active")
            return False

        if self.current_state == ConversationState.IDLE:
            self.transition_to(ConversationState.ACTIVATED, current_time=now)
            return True
        return False

    def should_continue_conversation(self, current_time: Optional[float] = None) -> bool:
        """
        Check if continuous conversation mode is active and follow-up turn is within window.
        """
        if not self.continuous_conversation:
            return False
        now = current_time or time.time()
        elapsed = now - self.last_speech_completed_time
        return (
            self.current_state == ConversationState.IDLE
            and self.last_speech_completed_time > 0
            and elapsed <= self.continuous_conversation_timeout
        )

    def reset(self):
        """Force reset to IDLE."""
        self.current_state = ConversationState.IDLE
        self.history.append((ConversationState.IDLE, time.time()))
