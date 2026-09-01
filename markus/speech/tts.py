"""
Markus AI — Text to Speech (TTS) (§6c, §7)

Generates natural voice responses via edge-tts (ChristopherNeural) with pyttsx3 fallback.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import tempfile
from typing import Optional

# ── Pre-import TTS engine at module level (avoid per-call import overhead) ──
try:
    import edge_tts  # type: ignore
    _HAS_EDGE_TTS = True
except ImportError:
    _HAS_EDGE_TTS = False

# ── Pre-import audio playback deps ──
try:
    import sounddevice as sd  # type: ignore
    import soundfile as sf  # type: ignore
    _HAS_AUDIO_PLAYBACK = True
except ImportError:
    _HAS_AUDIO_PLAYBACK = False

# ── Pre-import pyttsx3 fallback ──
try:
    import pyttsx3  # type: ignore
    _HAS_PYTTSX3 = True
except ImportError:
    _HAS_PYTTSX3 = False

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "en-US-ChristopherNeural"

# ── Pre-compiled regex patterns (avoid recompiling on every TTS call) ──
_RE_CODE_BLOCK = re.compile(r"```[\w]*\n[\s\S]*?```")
_RE_INLINE_CODE = re.compile(r"`[^`]+`")
_RE_URL = re.compile(r"https?://\S+")
_RE_MARKDOWN_CHARS = re.compile(r"[*#_~>|]")
_RE_WHITESPACE = re.compile(r"\s+")


class TextToSpeech:
    """
    Converts assistant text response to high quality speech audio.
    Cleans markdown formatting and code blocks for smooth listening.
    """

    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice

    def clean_text_for_speech(self, text: str) -> str:
        """Strip markdown code fences, urls, and special formatting."""
        # Replace code blocks with descriptive text
        clean = _RE_CODE_BLOCK.sub("Here is the code block.", text)
        clean = _RE_INLINE_CODE.sub("", clean)
        clean = _RE_URL.sub("link", clean)
        clean = _RE_MARKDOWN_CHARS.sub("", clean)
        clean = _RE_WHITESPACE.sub(" ", clean).strip()
        return clean

    async def generate_audio_bytes(self, text: str, voice: Optional[str] = None) -> bytes:
        """Synthesize text into MP3 audio bytes."""
        clean_text = self.clean_text_for_speech(text)
        if not clean_text:
            return b""

        selected_voice = voice or self.voice

        if _HAS_EDGE_TTS:
            try:
                communicate = edge_tts.Communicate(clean_text, selected_voice)
                buffer = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buffer.write(chunk["data"])
                audio_bytes = buffer.getvalue()
                if audio_bytes:
                    logger.info(f"TTS generated {len(audio_bytes)} bytes using {selected_voice}")
                    return audio_bytes
            except Exception as e:
                logger.warning(f"Edge-TTS failed: {e}. Falling back to pyttsx3.")

        # Fallback using pyttsx3
        if _HAS_PYTTSX3:
            try:
                engine = pyttsx3.init()
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name
                engine.save_to_file(clean_text, temp_path)
                engine.runAndWait()
                with open(temp_path, "rb") as f:
                    data = f.read()
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return data
            except Exception as e2:
                logger.error(f"pyttsx3 fallback failed: {e2}")

        return b""

    async def speak_text(self, text: str, voice: Optional[str] = None) -> bool:
        """Generate speech and play it immediately through local speakers."""
        audio_bytes = await self.generate_audio_bytes(text, voice)
        if not audio_bytes:
            return False

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name
            f.write(audio_bytes)

        try:
            if not _HAS_AUDIO_PLAYBACK:
                logger.warning("Audio playback not available: sounddevice/soundfile not installed")
                return False
            data, fs = sf.read(temp_path)
            sd.play(data, fs)
            sd.wait()
            return True
        except Exception as e:
            logger.warning(f"Audio playback error: {e}")
            return False
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


# Singleton instance
tts_engine = TextToSpeech()
