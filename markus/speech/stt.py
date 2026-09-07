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

            # Dynamic GPU/CUDA detection
            use_cuda = False
            try:
                import torch
                use_cuda = torch.cuda.is_available()
            except ImportError:
                try:
                    import ctranslate2
                    use_cuda = "cuda" in ctranslate2.get_supported_devices()
                except Exception:
                    use_cuda = False

            target_device = "cuda" if (self.device == "cuda" or (self.device == "auto" and use_cuda)) else "cpu"
            target_compute = "float16" if target_device == "cuda" else "int8"

            try:
                self._whisper_model = WhisperModel(
                    self.model_size,
                    device=target_device,
                    compute_type=target_compute,
                )
                logger.info(f"Faster-Whisper model ({self.model_size}) initialized on {target_device} ({target_compute})")
            except Exception as device_err:
                if target_device == "cuda":
                    logger.warning(f"CUDA STT init failed ({device_err}), falling back to CPU/int8")
                    self._whisper_model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                    )
                    logger.info(f"Faster-Whisper model ({self.model_size}) initialized on CPU fallback")
                else:
                    raise device_err

            self._initialized = True
        except Exception as e:
            logger.warning(f"Could not load faster-whisper model: {e}. Falling back to SpeechRecognition.")
            self._initialized = True

    def transcribe_with_gemini(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """
        Transcribe audio bytes using Google Gemini Multimodal Audio API.
        Provides state-of-the-art accuracy for English, Tamil (தமிழ்), and Tanglish speech.
        """
        if not audio_bytes:
            return ""

        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not gemini_key:
            return ""

        import base64
        import httpx

        models = [
            os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
            "gemini-3.6-flash",
            "gemini-3.1-flash-lite",
            "gemini-flash-latest",
        ]

        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "You are the speech-to-text transcription engine for the Markus AI assistant. "
                                "Transcribe the spoken audio accurately into text. "
                                "Output ONLY the verbatim transcript in the spoken language "
                                "(Tamil தமிழ், English, or Tanglish code-mixed). "
                                "Do NOT translate, do NOT explain, and do NOT include quotation marks or markdown."
                            )
                        },
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_audio,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 300,
            },
        }

        # Deduplicate models preserving order
        seen = set()
        deduped_models = [m for m in models if m and not (m in seen or seen.add(m))]

        with httpx.Client(timeout=10.0) as client:
            for model in deduped_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                try:
                    res = client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            text = "".join(p.get("text", "") for p in parts).strip()
                            if text:
                                return text
                except Exception as e:
                    logger.debug(f"Gemini STT model {model} attempt failed: {e}")

        return ""

    def transcribe_audio_bytes(self, audio_bytes: bytes, format: str = "wav") -> str:
        """Transcribe raw audio bytes."""
        if not audio_bytes:
            return ""

        self._init_model()

        # ── In-memory transcription: skip temp-file disk I/O when possible ──
        if self._whisper_model and format == "wav":
            try:
                audio_stream = io.BytesIO(audio_bytes)
                segments, _ = self._whisper_model.transcribe(
                    audio_stream,
                    beam_size=1,
                    vad_filter=True,
                    initial_prompt="Markus AI assistant. தமிழ் (Tamil), English, Tanglish voice commands: வணக்கம், open, close, search, play."
                )
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
            return self.transcribe_file(temp_path, original_audio_bytes=audio_bytes)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def transcribe_file(self, file_path: str, original_audio_bytes: Optional[bytes] = None) -> str:
        """Transcribe an audio file from disk."""
        self._init_model()

        # 1. Try faster-whisper with VAD filtering and bilingual prompt
        if self._whisper_model:
            try:
                segments, _ = self._whisper_model.transcribe(
                    file_path,
                    beam_size=1,
                    vad_filter=True,
                    initial_prompt="Markus AI assistant. தமிழ் (Tamil), English, Tanglish voice commands: வணக்கம், open, close, search, play."
                )
                text = " ".join([seg.text for seg in segments]).strip()
                if text:
                    logger.info(f"STT Transcript (Whisper): '{text}'")
                    return text
            except Exception as e:
                logger.warning(f"Whisper transcription failed: {e}")

        # 2. Try Gemini Multimodal Audio API
        try:
            audio_data = original_audio_bytes
            if audio_data is None and os.path.exists(file_path):
                with open(file_path, "rb") as af:
                    audio_data = af.read()
            if audio_data:
                gemini_text = self.transcribe_with_gemini(audio_data)
                if gemini_text:
                    logger.info(f"STT Transcript (Gemini API): '{gemini_text}'")
                    return gemini_text
        except Exception as e:
            logger.debug(f"Gemini API audio transcription fallback: {e}")

        # 3. Try SpeechRecognition fallback
        try:
            import speech_recognition as sr  # type: ignore
            r = sr.Recognizer()
            with sr.AudioFile(file_path) as source:
                audio = r.record(source)
                text = r.recognize_google(audio)
                if text:
                    logger.info(f"STT Transcript (Google SR): '{text}'")
                    return text
        except Exception as e:
            logger.warning(f"SpeechRecognition fallback failed: {e}")

        return ""


# Singleton instance
stt_engine = SpeechToText()
