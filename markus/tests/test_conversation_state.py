"""
Unit tests for Conversation State Machine (§6c)
"""

import unittest
from speech.conversation_state import (
    ConversationStateMachine,
    ConversationState,
    InvalidTransitionError,
)
from config.constants import AIState


class TestConversationState(unittest.TestCase):

    def test_valid_conversation_flow(self):
        sm = ConversationStateMachine(wake_word_cooldown=1.0)
        self.assertEqual(sm.current_state, ConversationState.IDLE)
        self.assertEqual(sm.ai_state, AIState.IDLE)

        # IDLE -> ACTIVATED -> LISTENING -> TRANSCRIBING -> PROCESSING -> RESPONDING -> SPEAKING -> IDLE
        self.assertEqual(sm.transition_to(ConversationState.ACTIVATED), ConversationState.ACTIVATED)
        self.assertEqual(sm.ai_state, AIState.LISTENING)

        self.assertEqual(sm.transition_to(ConversationState.LISTENING), ConversationState.LISTENING)
        self.assertEqual(sm.transition_to(ConversationState.TRANSCRIBING), ConversationState.TRANSCRIBING)
        self.assertEqual(sm.ai_state, AIState.THINKING)

        self.assertEqual(sm.transition_to(ConversationState.PROCESSING), ConversationState.PROCESSING)
        self.assertEqual(sm.transition_to(ConversationState.RESPONDING), ConversationState.RESPONDING)
        self.assertEqual(sm.transition_to(ConversationState.SPEAKING), ConversationState.SPEAKING)
        self.assertEqual(sm.ai_state, AIState.SPEAKING)

        self.assertEqual(sm.transition_to(ConversationState.IDLE), ConversationState.IDLE)
        self.assertEqual(sm.ai_state, AIState.IDLE)

    def test_illegal_transition_raises_error(self):
        sm = ConversationStateMachine()
        # Illegal jump: IDLE directly to SPEAKING
        with self.assertRaises(InvalidTransitionError):
            sm.transition_to(ConversationState.SPEAKING)

    def test_wake_word_cooldown(self):
        sm = ConversationStateMachine(wake_word_cooldown=2.0)
        t0 = 1000.0

        # First wake word
        self.assertTrue(sm.handle_wake_word(current_time=t0))
        self.assertEqual(sm.current_state, ConversationState.ACTIVATED)

        # Reset to IDLE
        sm.reset()

        # Second wake word inside cooldown window should be rejected
        self.assertFalse(sm.handle_wake_word(current_time=t0 + 0.5))

        # After cooldown expires
        self.assertTrue(sm.handle_wake_word(current_time=t0 + 2.5))

    def test_continuous_conversation_mode(self):
        sm = ConversationStateMachine(
            continuous_conversation=True,
            continuous_conversation_timeout=5.0,
        )

        t0 = 1000.0
        # Simulate turn ending
        sm.transition_to(ConversationState.ACTIVATED)
        sm.transition_to(ConversationState.LISTENING)
        sm.transition_to(ConversationState.TRANSCRIBING)
        sm.transition_to(ConversationState.PROCESSING)
        sm.transition_to(ConversationState.SPEAKING)
        sm.transition_to(ConversationState.IDLE, current_time=t0)

        # Within 5s window
        self.assertTrue(sm.should_continue_conversation(current_time=t0 + 2.0))
        # After 5s window
        self.assertFalse(sm.should_continue_conversation(current_time=t0 + 6.0))


if __name__ == "__main__":
    unittest.main()
