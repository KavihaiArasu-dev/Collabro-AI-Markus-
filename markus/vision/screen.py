"""
Markus AI — Screen Perception Module (§6c)

Extracts lightweight active window title and application metadata
without capturing or transmitting raw video streams or screenshots to the LLM.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScreenContext:
    """Structured active screen context summary."""
    active_app: str = "Unknown"
    window_title: str = "Unknown"
    is_active: bool = False
    error_detected: bool = False
    visible_error: str = ""

    def to_dict(self) -> dict:
        return {
            "active_app": self.active_app,
            "window_title": self.window_title,
            "is_active": self.is_active,
            "error_detected": self.error_detected,
            "visible_error": self.visible_error,
        }

    def to_prompt_context(self) -> str:
        if not self.is_active:
            return ""
        ctx = f"Active Window: '{self.window_title}' ({self.active_app})"
        if self.error_detected and self.visible_error:
            ctx += f" — Potential Error Context: {self.visible_error}"
        return ctx


class ScreenPerceptionManager:
    """
    Monitors foreground active application without continuous video/camera recording.
    """

    def __init__(self):
        self._enabled = True

    def get_active_window_context(self) -> ScreenContext:
        """Fetch current foreground window title and app name."""
        if not self._enabled:
            return ScreenContext(is_active=False)

        try:
            if sys.platform == "win32":
                return self._get_windows_context()
            else:
                return ScreenContext(active_app="Desktop", window_title="System Workspace", is_active=True)
        except Exception as e:
            logger.debug(f"Screen context resolution fallback: {e}")
            return ScreenContext(active_app="Desktop", window_title="Workspace", is_active=True)

    def _get_windows_context(self) -> ScreenContext:
        """Fetch Windows foreground window info using win32 API via ctypes."""
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ScreenContext(is_active=False)

        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or "Desktop"

        # Determine app name heuristic from title
        app_name = "Application"
        if "VSCode" in title or "Visual Studio Code" in title or ".py" in title or ".tsx" in title:
            app_name = "VSCode Code Editor"
        elif "Chrome" in title or "Edge" in title or "Firefox" in title:
            app_name = "Web Browser"
        elif "Terminal" in title or "PowerShell" in title or "cmd" in title:
            app_name = "Terminal Shell"

        # Check for error heuristics in title
        has_error = any(err_word in title.lower() for err_word in ["error", "exception", "failed", "crash"])
        error_msg = f"App title indicates issue: {title}" if has_error else ""

        return ScreenContext(
            active_app=app_name,
            window_title=title,
            is_active=True,
            error_detected=has_error,
            visible_error=error_msg,
        )


# Singleton
screen_perception = ScreenPerceptionManager()
