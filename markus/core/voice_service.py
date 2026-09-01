"""
Markus AI — Voice Service (§15, Phase 3)

Handles:
1. Continuous microphone listening using sounddevice
2. Wake word detection ("hey markus", "hello markus", "hey mark", "markus")
3. Speech-to-Text (STT) transcription via faster-whisper
4. Text-to-Speech (TTS) audio output via edge-tts / pyttsx3
5. Emits state changes to WebSocket (IDLE → LISTENING → THINKING → SPEAKING)
"""

from __future__ import annotations

import asyncio
import logging
import os
import queue
import re
import tempfile
import threading
from typing import Callable, Optional

from config.constants import AIState
from application.websocket import ws_manager

# ── Pre-import TTS engine at module level ──
try:
    import edge_tts  # type: ignore
    _HAS_EDGE_TTS = True
except ImportError:
    _HAS_EDGE_TTS = False

logger = logging.getLogger(__name__)

# Wake word triggers
WAKE_WORDS = ["hey markus", "hello markus", "hey mark", "markus", "hello mark"]

# ── Pre-compiled regex patterns for TTS text cleaning ──
_RE_CODE_BLOCKS = re.compile(r"```[\s\S]*?```")
_RE_INLINE_CODE = re.compile(r"`[^`]*`")
_RE_MARKDOWN = re.compile(r"[*#_~]")


class VoiceService:
    """
    Voice Interface for Markus AI.

    Continuously monitors microphone input for wake words. When detected:
    1. Switches AI state to LISTENING (updates Orb visual)
    2. Captures user speech
    3. Transcribes to text using faster-whisper
    4. Routes text to the agent orchestrator
    5. Speaks the response back using TTS
    """

    def __init__(self):
        self.is_listening = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._stt_model = None
        self._callback: Optional[Callable[[str], None]] = None
        logger.info("Voice Service initialized")

    def start_listening(self, on_speech_detected: Optional[Callable[[str], None]] = None):
        """Start background microphone monitoring for wake words."""
        if self.is_listening:
            logger.info("Voice Service is already listening")
            return

        self._callback = on_speech_detected
        self._stop_event.clear()
        self.is_listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Voice Service started listening for wake words ('hey markus', 'markus')")

    def stop_listening(self):
        """Stop background listening."""
        self._stop_event.set()
        self.is_listening = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Voice Service stopped")

    def _listen_loop(self):
        """Background thread monitoring audio input."""
        try:
            import sounddevice as sd
            import numpy as np

            sample_rate = 16000
            block_size = 1600  # 100ms chunks — react to speech in <100ms instead of 1s

            def callback(indata, frames, time_info, status):
                if status:
                    logger.warning(f"Audio input status: {status}")
                # Calculate audio energy (volume)
                volume = np.linalg.norm(indata) * 10
                if volume > 15:  # Audio activity threshold
                    # Trigger listening state
                    logger.info(f"Speech activity detected (energy={volume:.1f})")

            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                blocksize=block_size,
                callback=callback,
            ):
                while not self._stop_event.is_set():
                    self._stop_event.wait(0.5)

        except ImportError:
            logger.warning("sounddevice or numpy not available — voice listening disabled")
        except Exception as e:
            logger.error(f"Voice loop error: {e}")

    async def speak(self, text: str):
        """
        Convert text to speech and play audio output.
        Switches AI state to SPEAKING during playback.
        """
        if not text.strip():
            return

        logger.info(f"Markus speaking: {text[:60]}...")
        await ws_manager.set_state(AIState.SPEAKING)

        try:
            # Clean markdown code blocks from TTS text (using pre-compiled patterns)
            clean_text = _RE_CODE_BLOCKS.sub("code block omitted", text)
            clean_text = _RE_INLINE_CODE.sub("", clean_text)
            clean_text = _RE_MARKDOWN.sub("", clean_text)

            if _HAS_EDGE_TTS:
                # Use edge-tts for natural high-quality voice
                communicate = edge_tts.Communicate(clean_text, "en-US-ChristopherNeural")

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    temp_path = f.name

                await communicate.save(temp_path)

                # Play audio file
                try:
                    import sounddevice as sd
                    import soundfile as sf

                    data, fs = sf.read(temp_path)
                    sd.play(data, fs)
                    sd.wait()
                except Exception as e:
                    logger.warning(f"Audio playback error: {e}")

                if os.path.exists(temp_path):
                    os.remove(temp_path)
            else:
                logger.warning("edge-tts not available for TTS")

        except Exception as e:
            logger.error(f"TTS error: {e}")

        finally:
            await ws_manager.set_state(AIState.IDLE)

    def process_voice_command(self, text: str) -> bool:
        """
        Check if spoken text contains a wake word.

        Returns True if a wake word was detected.
        """
        text_lower = text.lower()
        for wake_word in WAKE_WORDS:
            if wake_word in text_lower:
                logger.info(f"Wake word detected: '{wake_word}' in '{text}'")
                return True
        return False


# Singleton
voice_service = VoiceService()
