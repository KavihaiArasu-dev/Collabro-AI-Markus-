"""
Unit tests for Multimodal Perception Manager & Fusion (§6c)
"""

import unittest
from brain.perception import PerceptionManager, PerceptionContext


class TestPerception(unittest.TestCase):

    def test_perception_fusion_and_prompt_rendering(self):
        pm = PerceptionManager(
            microphone_enabled=True,
            camera_enabled=True,
            emotion_detection_enabled=True,
        )

        pm.update_audio(
            transcript="How is the weather today?",
            speaking=False,
            wake_word_detected=True,
        )

        pm.update_vision(
            face_present=True,
            face_count=1,
            expression="surprised",
            expression_confidence=0.78,
        )

        ctx = pm.get_context()
        prompt_text = ctx.to_prompt_context()

        self.assertIn("Visible facial expression appears surprised (confidence 78%)", prompt_text)
        self.assertIn("treat this as a rough signal, not a confirmed emotional state", prompt_text)
        self.assertIn('User spoke with transcription: "How is the weather today?"', prompt_text)

    def test_privacy_gating_camera_disabled(self):
        pm = PerceptionManager(camera_enabled=False)

        pm.update_vision(
            face_present=True,
            face_count=1,
            expression="happy",
            expression_confidence=0.95,
        )

        ctx = pm.get_context()
        # When camera is disabled, vision update is dropped
        self.assertFalse(ctx.vision.face_present)
        self.assertEqual(ctx.vision.face_count, 0)

    def test_privacy_gating_emotion_disabled(self):
        pm = PerceptionManager(camera_enabled=True, emotion_detection_enabled=False)

        pm.update_vision(
            face_present=True,
            face_count=1,
            expression="angry",
            expression_confidence=0.91,
        )

        ctx = pm.get_context()
        # Face presence is known, but expression is scrubbed
        self.assertTrue(ctx.vision.face_present)
        self.assertEqual(ctx.vision.expression, "neutral")
        self.assertEqual(ctx.vision.expression_confidence, 0.0)

    def test_screen_perception_and_context_manager(self):
        from vision.screen import ScreenContext
        from core.context_manager import ContextManager

        cm = ContextManager()
        ctx = cm.create_context("test-screen-conv")
        ctx.screen = ScreenContext(
            active_app="VSCode Code Editor",
            window_title="main.py - Markus AI",
            is_active=True,
            error_detected=False,
        )

        messages = cm.build_prompt_messages(ctx, system_prompt="You are Markus AI.")
        self.assertTrue(len(messages) >= 1)
        system_content = messages[0]["content"]
        self.assertIn("Screen & Environment Context", system_content)
        self.assertIn("VSCode Code Editor", system_content)
        self.assertIn("main.py - Markus AI", system_content)


if __name__ == "__main__":
    unittest.main()
