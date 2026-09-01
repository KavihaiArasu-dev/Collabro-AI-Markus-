"""
Markus AI — Voice Activity Detection (VAD) (§6c, §7)

Standalone voice activity detector using audio energy (RMS) calculation.
Discards silence, clicks, and noise, and enforces max recording duration.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

# ── Pre-import numpy for vectorized RMS (avoid Python-loop overhead) ──
try:
    import numpy as np  # type: ignore
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

logger = logging.getLogger(__name__)


class VoiceActivityDetector:
    """
    Detects presence of speech in audio blocks based on Root Mean Square (RMS) energy.
    
    Configurable parameters:
    - silence_threshold: RMS energy threshold below which audio is considered silence.
    - silence_timeout: Duration of continuous silence (seconds) to consider an utterance ended.
    - min_speech_duration: Minimum duration of speech (seconds) to discard clicks/pops.
    - max_recording_duration: Hard cap (seconds) to prevent stuck-open recording.
    """

    def __init__(
        self,
        silence_threshold: float = 0.015,
        silence_timeout: float = 0.8,
        min_speech_duration: float = 0.15,
        max_recording_duration: float = 30.0,
    ):
        self.silence_threshold = silence_threshold
        self.silence_timeout = silence_timeout
        self.min_speech_duration = min_speech_duration
        self.max_recording_duration = max_recording_duration

        self.is_speech_active = False
        self.speech_start_time: Optional[float] = None
        self.last_speech_time: Optional[float] = None
        self.total_speech_duration: float = 0.0

    def calculate_rms(self, audio_data: list[float] | bytes) -> float:
        """Calculate Root Mean Square (RMS) of audio sample sequence."""
        if not audio_data:
            return 0.0

        if isinstance(audio_data, bytes):
            # 16-bit PCM conversion
            import array
            samples = array.array('h')
            samples.frombytes(audio_data)
            if not samples:
                return 0.0
            # ── Vectorized path: numpy is ~10× faster than Python loop ──
            if _HAS_NUMPY:
                arr = np.array(samples, dtype=np.float32) / 32768.0
                return float(np.sqrt(np.mean(np.square(arr))))
            sum_squares = sum((s / 32768.0) ** 2 for s in samples)
            return math.sqrt(sum_squares / len(samples))
        else:
            # ── Vectorized path for float arrays ──
            if _HAS_NUMPY:
                arr = np.array(audio_data, dtype=np.float32)
                return float(np.sqrt(np.mean(np.square(arr))))
            sum_squares = sum(s ** 2 for s in audio_data)
            return math.sqrt(sum_squares / len(audio_data))

    def is_speech(self, audio_data: list[float] | bytes) -> bool:
        """Returns True if the audio block energy exceeds the silence threshold."""
        rms = self.calculate_rms(audio_data)
        return rms >= self.silence_threshold

    def process_frame(
        self,
        audio_data: list[float] | bytes,
        current_time: float,
    ) -> tuple[bool, bool]:
        """
        Process an incoming audio frame.
        
        Returns:
            (has_speech: bool, is_utterance_complete: bool)
        """
        has_speech = self.is_speech(audio_data)

        if has_speech:
            if not self.is_speech_active:
                self.is_speech_active = True
                self.speech_start_time = current_time
            self.last_speech_time = current_time

            # Check max recording duration
            if self.speech_start_time and (current_time - self.speech_start_time) >= self.max_recording_duration:
                return True, True
            return True, False
        else:
            if self.is_speech_active and self.last_speech_time:
                silence_elapsed = current_time - self.last_speech_time
                if silence_elapsed >= self.silence_timeout:
                    speech_duration = self.last_speech_time - (self.speech_start_time or self.last_speech_time)
                    self.reset()
                    # Discard if shorter than min speech duration
                    if speech_duration >= self.min_speech_duration:
                        return False, True
                    return False, False

            return False, False

    def reset(self):
        """Reset internal state."""
        self.is_speech_active = False
        self.speech_start_time = None
        self.last_speech_time = None
        self.total_speech_duration = 0.0
