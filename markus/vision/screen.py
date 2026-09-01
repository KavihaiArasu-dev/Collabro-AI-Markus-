"""
Markus AI — Screen Perception Module
"""

from __future__ import annotations

from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScreenContext:
    active_app: str = "VSCode Code Editor"
    window_title: str = "App.tsx — Markus_AI"
    is_active: bool = True
    error_detected: bool = False
    visible_error: str = ""

    def to_prompt_context(self) -> str:
        if not self.is_active or self.window_title == "Unknown":
            return ""
        scr_text = f"[Screen Context: Active window '{self.window_title}' ({self.active_app})]"
        if self.error_detected and self.visible_error:
            scr_text += f" — Potential issue: {self.visible_error}"
        return scr_text


class ScreenPerceptionManager:
    """Manages active window and screen perception context."""

    def __init__(self):
        self.active_context = ScreenContext()

    def get_active_window_context(self) -> ScreenContext:
        return self.active_context


screen_perception = ScreenPerceptionManager()
