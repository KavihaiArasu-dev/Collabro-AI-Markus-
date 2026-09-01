import unittest
from brain.perception import PerceptionManager, PerceptionContext
from core.model_router import model_router
from vision.screen import screen_perception, ScreenContext


class TestUpgrades(unittest.TestCase):
    def test_model_router_resolve_routing_details(self):
        details = model_router.resolve_routing_details(
            task_type="coding",
            privacy="normal",
            latency="balanced",
            complexity="normal",
        )
        self.assertEqual(details["route"], "auto/coding")
        self.assertIn("Code generation", details["rationale"])
        self.assertIn("Tier", details["tier"])

    def test_model_router_offline_privacy_details(self):
        details = model_router.resolve_routing_details(
            task_type="chat",
            privacy="local",
        )
        self.assertEqual(details["route"], "auto/offline")
        self.assertIn("Privacy-first", details["rationale"])

    def test_screen_perception_context_integration(self):
        pm = PerceptionManager(screen_perception_enabled=True)
        pm.update_screen(
            active_app="VSCode Code Editor",
            window_title="App.tsx — Markus_AI",
            is_active=True,
            error_detected=True,
            visible_error="SyntaxError: Unexpected token",
        )
        ctx = pm.get_context()
        self.assertEqual(ctx.screen.active_app, "VSCode Code Editor")
        prompt_str = ctx.to_prompt_context()
        self.assertIn("[Screen Context:", prompt_str)
        self.assertIn("App.tsx — Markus_AI", prompt_str)
        self.assertIn("SyntaxError: Unexpected token", prompt_str)

    def test_screen_perception_manager_direct(self):
        context = screen_perception.get_active_window_context()
        self.assertIsInstance(context, ScreenContext)
        self.assertTrue(hasattr(context, "active_app"))
        self.assertTrue(hasattr(context, "window_title"))
