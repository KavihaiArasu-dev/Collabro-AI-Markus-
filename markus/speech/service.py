"""
Markus AI — Voice and Speech Service (§6c, §7, §8)

Full-featured Voice Service that coordinates:
- Voice Activity Detection (VAD)
- Conversation State Machine
- Wake Word Detection
- Speech to Text (STT)
- Text to Speech (TTS)
- Broadcasts real-time state changes to the Frontend & HUD
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
import time
from typing import Callable, Optional

# ── Pre-import heavy deps at module level ──
try:
    import numpy as np  # type: ignore
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    import soundfile as sf_mod  # type: ignore
    _HAS_SOUNDFILE = True
except ImportError:
    _HAS_SOUNDFILE = False

import io

from speech.vad import VoiceActivityDetector
from speech.conversation_state import ConversationStateMachine, ConversationState
from speech.stt import stt_engine
from speech.tts import tts_engine
from speech.wakeword import wakeword_detector
from application.websocket import ws_manager
from config.constants import AIState

logger = logging.getLogger(__name__)

# ── Shared thread pool for offloading blocking transcription work ──
_transcription_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="stt")


class VoiceService:
    """
    High-level speech manager for Markus AI.
    Runs continuous background audio processing, triggers wake words,
    processes speech, and provides natural voice responses.
    """

    def __init__(self):
        self.vad = VoiceActivityDetector()
        self.state_machine = ConversationStateMachine()
        self.stt = stt_engine
        self.tts = tts_engine
        self.wakeword = wakeword_detector

        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_transcript_callback: Optional[Callable[[str], None]] = None

    def start(self, on_transcript: Optional[Callable[[str], None]] = None):
        """Start background microphone monitoring."""
        if self.is_running:
            return
        self._on_transcript_callback = on_transcript
        self._stop_event.clear()
        self.is_running = True
        self._thread = threading.Thread(target=self._audio_loop, daemon=True)
        self._thread.start()
        logger.info("VoiceService started background listener")

    def stop(self):
        """Stop background microphone monitoring."""
        self._stop_event.set()
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.5)
        self.state_machine.reset()
        logger.info("VoiceService stopped")

    def _audio_loop(self):
        """Background audio capture and VAD loop."""
        try:
            import sounddevice as sd  # type: ignore

            sample_rate = 16000
            block_size = 800  # 50ms blocks — faster end-of-speech detection

            audio_buffer: list[float] = []

            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"Audio status: {status}")
                if self._stop_event.is_set():
                    return

                current_time = time.time()
                # ── Use numpy flatten directly (already imported at module level) ──
                if _HAS_NUMPY:
                    samples = indata.flatten().tolist()
                else:
                    samples = list(indata.flatten())
                has_speech, is_complete = self.vad.process_frame(samples, current_time)

                if has_speech or self.vad.is_speech_active:
                    audio_buffer.extend(samples)

                if is_complete and audio_buffer:
                    # An utterance finished — offload transcription to thread pool
                    recorded_audio = list(audio_buffer)
                    audio_buffer.clear()
                    _transcription_pool.submit(self._handle_completed_utterance, recorded_audio)

            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                blocksize=block_size,
                callback=audio_callback,
            ):
                while not self._stop_event.is_set():
                    self._stop_event.wait(0.2)

        except ImportError:
            logger.info("sounddevice/numpy not available. Audio hardware loop in standby.")
        except Exception as e:
            logger.error(f"VoiceService audio loop error: {e}")

    def _handle_completed_utterance(self, audio_samples: list[float]):
        """Transcribe and process speech from recorded audio samples."""
        try:
            # Convert to 16-bit PCM wav bytes using pre-imported modules
            if not _HAS_NUMPY or not _HAS_SOUNDFILE:
                logger.warning("numpy or soundfile not available for audio processing")
                return

            np_data = (np.array(audio_samples) * 32767).astype(np.int16)
            buffer = io.BytesIO()
            sf_mod.write(buffer, np_data, 16000, format='WAV', subtype='PCM_16')
            wav_bytes = buffer.getvalue()

            # State transition to transcribing
            if self.state_machine.can_transition_to(ConversationState.TRANSCRIBING):
                self.state_machine.transition_to(ConversationState.TRANSCRIBING)

            text = self.stt.transcribe_audio_bytes(wav_bytes)
            if not text:
                self.state_machine.reset()
                return

            # Check wake word
            detected, command = self.wakeword.check_text_for_wake_word(text)
            should_respond = detected or self.state_machine.should_continue_conversation()

            if should_respond:
                prompt = command if command else text
                logger.info(f"Voice recognized utterance: '{prompt}'")
                if self._on_transcript_callback:
                    self._on_transcript_callback(prompt)

            self.state_machine.reset()

        except Exception as e:
            logger.error(f"Error processing completed utterance: {e}")
            self.state_machine.reset()

    async def speak_response(self, text: str) -> bytes:
        """
        Generate TTS audio, broadcast SPEAKING state to UI Orb, and return audio bytes.
        """
        if not text.strip():
            return b""

        # Broadcast speaking state to Orb
        await ws_manager.set_state(AIState.SPEAKING)
        try:
            if self.state_machine.can_transition_to(ConversationState.SPEAKING):
                self.state_machine.transition_to(ConversationState.SPEAKING)
        except Exception:
            pass

        try:
            audio_bytes = await self.tts.generate_audio_bytes(text)
            return audio_bytes
        finally:
            self.state_machine.reset()
            await ws_manager.set_state(AIState.IDLE)


# Singleton instance
voice_service = VoiceService()
