"""
Markus AI — Multimodal Perception Context & Fusion (§6c, §7)

Fuses audio (speech, wake word, VAD) and vision (face presence, tracking, facial emotion)
into a unified PerceptionContext for prompt injection.
Enforces privacy gating:
- Disabling MICROPHONE_ENABLED drops audio updates.
- Disabling CAMERA_ENABLED drops vision updates.
- Disabling EMOTION_DETECTION_ENABLED clears expression fields even when faces are present.
- Expression output is always formatted as a hedged estimate, never an asserted emotional fact.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AudioPerception:
    wake_word_detected: bool = False
    speaking: bool = False
    transcript: str = ""
    energy_level: float = 0.0


@dataclass
class VisionPerception:
    face_present: bool = False
    face_count: int = 0
    expression: str = "neutral"
    expression_confidence: float = 0.80
    faces: list[dict] = field(default_factory=list)


@dataclass
class ScreenPerception:
    active_app: str = "Unknown"
    window_title: str = "Unknown"
    is_active: bool = False
    error_detected: bool = False
    visible_error: str = ""


@dataclass
class PerceptionContext:
    """Unified multimodal perception state."""
    audio: AudioPerception = field(default_factory=AudioPerception)
    vision: VisionPerception = field(default_factory=VisionPerception)
    screen: ScreenPerception = field(default_factory=ScreenPerception)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_prompt_context(self) -> str:
        """
        Render hedged perception context for system prompt injection.
        """
        parts = []

        if self.vision.face_present:
            conf_pct = int(self.vision.expression_confidence * 100)
            parts.append(
                f"[Visual Context: {self.vision.face_count} face(s) in view. "
                f"Visible facial expression appears {self.vision.expression} (confidence {conf_pct}%) — "
                f"treat this as a rough signal, not a confirmed emotional state.]"
            )

        if self.audio.transcript:
            parts.append(f"[Voice Context: User spoke with transcription: \"{self.audio.transcript}\"]")

        if self.screen.is_active and self.screen.window_title != "Unknown":
            scr_text = f"[Screen Context: Active window '{self.screen.window_title}' ({self.screen.active_app})]"
            if self.screen.error_detected and self.screen.visible_error:
                scr_text += f" — Potential issue: {self.screen.visible_error}"
            parts.append(scr_text)

        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "audio": {
                "wakeWordDetected": self.audio.wake_word_detected,
                "speaking": self.audio.speaking,
                "transcript": self.audio.transcript,
                "energyLevel": self.audio.energy_level,
            },
            "vision": {
                "facePresent": self.vision.face_present,
                "faceCount": self.vision.face_count,
                "expression": self.vision.expression,
                "expressionConfidence": self.vision.expression_confidence,
                "faces": self.vision.faces,
            },
            "screen": {
                "activeApp": self.screen.active_app,
                "windowTitle": self.screen.window_title,
                "isActive": self.screen.is_active,
                "errorDetected": self.screen.error_detected,
                "visibleError": self.screen.visible_error,
            },
            "timestamp": self.timestamp,
        }


class PerceptionManager:
    """
    Manages real-time perception state with strict privacy controls.
    """

    def __init__(
        self,
        microphone_enabled: bool = True,
        camera_enabled: bool = True,
        emotion_detection_enabled: bool = True,
        screen_perception_enabled: bool = True,
        local_processing_only: bool = True,
    ):
        self.microphone_enabled = microphone_enabled
        self.camera_enabled = camera_enabled
        self.emotion_detection_enabled = emotion_detection_enabled
        self.screen_perception_enabled = screen_perception_enabled
        self.local_processing_only = local_processing_only

        self._current_context = PerceptionContext()
        logger.info("PerceptionManager initialized with privacy controls active")

    def update_audio(
        self,
        transcript: str = "",
        speaking: bool = False,
        wake_word_detected: bool = False,
        energy_level: float = 0.0,
    ) -> PerceptionContext:
        """Update audio perception channel if microphone is enabled."""
        if not self.microphone_enabled:
            logger.debug("Audio update ignored: MICROPHONE_ENABLED is false")
            return self._current_context

        self._current_context.audio = AudioPerception(
            wake_word_detected=wake_word_detected,
            speaking=speaking,
            transcript=transcript,
            energy_level=energy_level,
        )
        self._current_context.timestamp = datetime.now().isoformat()
        return self._current_context

    def update_vision(
        self,
        face_present: bool = False,
        face_count: int = 0,
        expression: str = "neutral",
        expression_confidence: float = 0.80,
        faces: Optional[list[dict]] = None,
    ) -> PerceptionContext:
        """Update vision perception channel with emotion gating."""
        if not self.camera_enabled:
            logger.debug("Vision update ignored: CAMERA_ENABLED is false")
            return self._current_context

        # If emotion detection is disabled, zero out emotion data even if face is present
        effective_expression = expression if self.emotion_detection_enabled else "neutral"
        effective_conf = expression_confidence if self.emotion_detection_enabled else 0.0

        self._current_context.vision = VisionPerception(
            face_present=face_present,
            face_count=face_count,
            expression=effective_expression,
            expression_confidence=effective_conf,
            faces=faces or [],
        )
        self._current_context.timestamp = datetime.now().isoformat()
        return self._current_context

    def update_screen(
        self,
        active_app: str = "Unknown",
        window_title: str = "Unknown",
        is_active: bool = True,
        error_detected: bool = False,
        visible_error: str = "",
    ) -> PerceptionContext:
        """Update screen perception channel."""
        if not self.screen_perception_enabled:
            return self._current_context

        self._current_context.screen = ScreenPerception(
            active_app=active_app,
            window_title=window_title,
            is_active=is_active,
            error_detected=error_detected,
            visible_error=visible_error,
        )
        self._current_context.timestamp = datetime.now().isoformat()
        return self._current_context

    def get_context(self) -> PerceptionContext:
        """Retrieve current multimodal perception context."""
        return self._current_context


# Singleton instance
perception_manager = PerceptionManager()

