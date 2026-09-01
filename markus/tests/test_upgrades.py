"""
Markus AI — Unit Tests for System Upgrades
"""

import pytest
from brain.perception import PerceptionManager, PerceptionContext
from core.model_router import model_router
from vision.screen import screen_perception, ScreenContext


def test_model_router_resolve_routing_details():
    details = model_router.resolve_routing_details(
        task_type="coding",
        privacy="normal",
        latency="balanced",
        complexity="normal",
    )
    assert details["route"] == "auto/coding"
    assert "Code generation" in details["rationale"]
    assert "Tier" in details["tier"]


def test_model_router_offline_privacy_details():
    details = model_router.resolve_routing_details(
        task_type="chat",
        privacy="local",
    )
    assert details["route"] == "auto/offline"
    assert "Privacy-first" in details["rationale"]



def test_screen_perception_context_integration():
    pm = PerceptionManager(screen_perception_enabled=True)
    pm.update_screen(
        active_app="VSCode Code Editor",
        window_title="App.tsx — Markus_AI",
        is_active=True,
        error_detected=True,
        visible_error="SyntaxError: Unexpected token",
    )
    ctx = pm.get_context()
    assert ctx.screen.active_app == "VSCode Code Editor"
    prompt_str = ctx.to_prompt_context()
    assert "[Screen Context:" in prompt_str
    assert "App.tsx — Markus_AI" in prompt_str
    assert "SyntaxError: Unexpected token" in prompt_str


def test_screen_perception_manager_direct():
    context = screen_perception.get_active_window_context()
    assert isinstance(context, ScreenContext)
    assert hasattr(context, "active_app")
    assert hasattr(context, "window_title")
