"""
Markus AI — Speech to Text (STT) (§6c, §7)

Supports faster-whisper, SpeechRecognition, and audio file decoding.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from typing import Optional

# ── Pre-import heavy deps at module level (avoid per-call import overhead) ──
try:
    import numpy as np  # type: ignore
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    import soundfile as sf  # type: ignore
    _HAS_SOUNDFILE = True
except ImportError:
    _HAS_SOUNDFILE = False

logger = logging.getLogger(__name__)


class SpeechToText:
    """
    Transcribes audio buffers/files to text using local faster-whisper or speech_recognition.
    """

    def __init__(self, model_size: str = "base", device: str = "auto"):
        self.model_size = model_size
        self.device = device
        self._whisper_model = None
        self._initialized = False
        # ── Non-blocking background init: fast server startup + no cold start ──
        import threading
        threading.Thread(target=self._init_model, daemon=True).start()

    def _init_model(self):
        if self._initialized:
            return
        try:
            from faster_whisper import WhisperModel  # type: ignore
            compute_type = "int8" if self.device == "cpu" else "float16"
            self._whisper_model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
            )
            self._initialized = True
            logger.info(f"Faster-Whisper model ({self.model_size}) initialized")
        except Exception as e:
            logger.warning(f"Could not load faster-whisper model: {e}. Falling back to SpeechRecognition.")
            self._initialized = True

    def transcribe_audio_bytes(self, audio_bytes: bytes, format: str = "wav") -> str:
        """Transcribe raw audio bytes."""
        if not audio_bytes:
            return ""

        self._init_model()

        # ── In-memory transcription: skip temp-file disk I/O when possible ──
        if self._whisper_model and format == "wav":
            try:
                audio_stream = io.BytesIO(audio_bytes)
                segments, _ = self._whisper_model.transcribe(audio_stream, beam_size=1)
                text = " ".join([seg.text for seg in segments]).strip()
                if text:
                    logger.info(f"STT Transcript (Whisper in-memory): '{text}'")
                    return text
            except Exception as e:
                logger.debug(f"In-memory transcription failed, falling back to file: {e}")

        # Fallback: write to temporary audio file
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            temp_path = f.name
            f.write(audio_bytes)

        try:
            return self.transcribe_file(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def transcribe_file(self, file_path: str) -> str:
        """Transcribe an audio file from disk."""
        self._init_model()

        # 1. Try faster-whisper (beam_size=1 for greedy decoding — 3-5× faster)
        if self._whisper_model:
            try:
                segments, _ = self._whisper_model.transcribe(file_path, beam_size=1)
                text = " ".join([seg.text for seg in segments]).strip()
                logger.info(f"STT Transcript (Whisper): '{text}'")
                return text
            except Exception as e:
                logger.warning(f"Whisper transcription failed: {e}")

        # 2. Try SpeechRecognition fallback
        try:
            import speech_recognition as sr  # type: ignore
            r = sr.Recognizer()
            with sr.AudioFile(file_path) as source:
                audio = r.record(source)
                text = r.recognize_google(audio)
                logger.info(f"STT Transcript (Google SR): '{text}'")
                return text
        except Exception as e:
            logger.warning(f"SpeechRecognition fallback failed: {e}")

        return ""


# Singleton instance
stt_engine = SpeechToText()
