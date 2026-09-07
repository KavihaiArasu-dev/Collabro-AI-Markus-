"""
Markus AI — Wake Word Detection (§6c, §7)

Detects wake phrases like "Hey Markus", "Hello Markus", "Markus".
Integrates with openWakeWord when available, with fallback to phrase recognition.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_WAKE_WORDS = [
    "hey markus",
    "hey marcus",
    "hey marcos",
    "hey markers",
    "hey makers",
    "hello markus",
    "hello marcus",
    "hello marcos",
    "hey makus",
    "hello makus",
    "hey make",
    "hello make",
    "hey mark",
    "hello mark",
    "hi markus",
    "hi marcus",
    "hi marcos",
    "hi makus",
    "hi make",
    "hi mark",
    "ok markus",
    "okay markus",
    "ok marcus",
    "okay marcus",
    "ok makus",
    "ok make",
    "ok mark",
    "okay make",
    "okay mark",
    "markus",
    "marcus",
    "marcos",
    "markers",
    "makers",
    "makus",
    "make",
    "mark",
    # Tamil phonetic variants
    "ஹேய் மார்கஸ்",
    "ஹே மார்கஸ்",
    "ஹேய் மார்க்",
    "ஹே மார்க்",
    "மார்கஸ்",
    "மார்க்கஸ்",
    "மார்க்",
    "வணக்கம் மார்கஸ்",
    "வணக்கம் மார்க்",
]



class WakeWordDetector:
    """
    Wake word detector with customizable trigger phrases,
    cooldown management, and threshold sensitivity.
    """

    def __init__(
        self,
        wake_words: Optional[list[str]] = None,
        cooldown_seconds: float = 0.8,
    ):
        self.wake_words = [w.lower() for w in (wake_words or DEFAULT_WAKE_WORDS)]
        self.cooldown_seconds = cooldown_seconds
        self.last_detection_time: float = 0.0
        # ── Pre-compile regex patterns (avoid recompiling on every check) ──
        self._compiled_patterns: list[tuple[str, re.Pattern]] = [
            (ww, re.compile(r'\b' + re.escape(ww) + r'\b'))
            for ww in self.wake_words
        ]

    def check_text_for_wake_word(self, text: str, current_time: Optional[float] = None) -> tuple[bool, str]:
        """
        Check if recognized transcript text contains any wake word.
        Returns: (detected: bool, stripped_command: str)
        """
        now = current_time or time.time()
        if now - self.last_detection_time < self.cooldown_seconds:
            return False, text

        normalized = text.lower().strip()
        for ww, pattern in self._compiled_patterns:
            match = pattern.search(normalized)
            if match:
                self.last_detection_time = now
                # Extract command after wake word
                start, end = match.span()
                remainder = (text[:start] + " " + text[end:]).strip()
                remainder = re.sub(r'^[,\s]+', '', remainder)
                logger.info(f"Wake word detected: '{ww}'. Command: '{remainder}'")
                return True, remainder

        return False, text

    def is_cooldown_active(self, current_time: Optional[float] = None) -> bool:
        now = current_time or time.time()
        return (now - self.last_detection_time) < self.cooldown_seconds


# Singleton instance
wakeword_detector = WakeWordDetector()
