"""
Integration and Unit tests for Speech, Vision, and Context Manager
"""

import unittest
from speech.wakeword import WakeWordDetector
from speech.tts import TextToSpeech
from core.context_manager import ContextManager
from brain.perception import perception_manager


class TestSpeechAndVision(unittest.TestCase):

    def test_wake_word_detector(self):
        ww = WakeWordDetector(cooldown_seconds=1.0)

        # Trigger with command
        detected, cmd = ww.check_text_for_wake_word("Hey Markus what is the system status?", current_time=100.0)
        self.assertTrue(detected)
        self.assertIn("what is the system status", cmd)

        # Cooldown rejection
        detected2, _ = ww.check_text_for_wake_word("Hey Markus check CPU", current_time=100.5)
        self.assertFalse(detected2)

        # No wake word
        detected3, _ = ww.check_text_for_wake_word("Open Google Chrome", current_time=102.0)
        self.assertFalse(detected3)

    def test_tts_clean_text(self):
        tts = TextToSpeech()
        raw = "Here is the plan:\n```python\nprint('hello')\n```\nVisit https://example.com for *more* info."
        cleaned = tts.clean_text_for_speech(raw)

        self.assertNotIn("```", cleaned)
        self.assertNotIn("https://", cleaned)
        self.assertIn("Here is the plan:", cleaned)

    def test_context_manager_incorporates_perception(self):
        cm = ContextManager()
        perception_manager.update_audio(transcript="Hello Markus", wake_word_detected=True)
        perception_manager.update_vision(face_present=True, face_count=1, expression="happy", expression_confidence=0.89)

        ctx = cm.create_context("test-convo-1")
        cm.add_message("test-convo-1", "user", "Explain quantum computing")

        messages = cm.build_prompt_messages(ctx, system_prompt="You are Markus.")

        self.assertGreaterEqual(len(messages), 2)
        system_msg = messages[0]["content"]
        self.assertIn("Multimodal Perception Context", system_msg)
        self.assertIn("Visible facial expression appears happy", system_msg)

    def test_stt_transcribe_audio_empty_bytes(self):
        from speech.stt import stt_engine
        res = stt_engine.transcribe_audio_bytes(b"")
        self.assertEqual(res, "")

    def test_face_recognizer_hybrid_similarity(self):
        from vision.face_recognition import FaceRecognizer
        fr = FaceRecognizer()
        v1 = [0.1] * 100
        v2 = [0.1] * 100
        sim = fr.compute_similarity(v1, v2)
        self.assertGreater(sim, 0.95)

        # Orthogonal vectors should have low similarity
        v3 = [1.0 if i < 50 else 0.0 for i in range(100)]
        v4 = [0.0 if i < 50 else 1.0 for i in range(100)]
        sim_ortho = fr.compute_similarity(v3, v4)
        self.assertLess(sim_ortho, sim)


if __name__ == "__main__":
    unittest.main()
