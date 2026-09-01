"""
Markus AI — Speech API Routes (§6c, §7, §9)

Provides endpoints for:
- Audio file / buffer Speech-to-Text transcription (/api/speech/transcribe)
- Text-to-Speech audio streaming (/api/speech/tts)
- Server-side speech playback (/api/speech/speak)
- Voice service status (/api/speech/status)
"""

from __future__ import annotations

import base64
import logging
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from speech.stt import stt_engine
from speech.tts import tts_engine
from speech.service import voice_service
from speech.conversation_state import ConversationState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/speech", tags=["Speech"])


class TranscribeRequest(BaseModel):
    audio_base64: str
    format: str = "wav"


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None


@router.post("/transcribe")
async def transcribe_audio(
    file: Optional[UploadFile] = File(None),
    payload: Optional[TranscribeRequest] = None,
):
    """Transcribe speech audio from file upload or base64 payload."""
    audio_bytes = None
    fmt = "wav"

    if file:
        audio_bytes = await file.read()
        if file.filename:
            fmt = file.filename.split(".")[-1]
    elif payload and payload.audio_base64:
        b64_data = payload.audio_base64
        if "," in b64_data:
            b64_data = b64_data.split(",")[1]
        audio_bytes = base64.b64decode(b64_data)
        fmt = payload.format

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio data provided")

    transcript = stt_engine.transcribe_audio_bytes(audio_bytes, format=fmt)
    return {
        "transcript": transcript,
        "length_bytes": len(audio_bytes),
    }


@router.post("/tts")
async def generate_tts(request: TTSRequest):
    """Convert text into MP3 audio stream."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    audio_bytes = await tts_engine.generate_audio_bytes(request.text, voice=request.voice)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Failed to synthesize speech audio")

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )


@router.post("/speak")
async def speak_response(request: SpeakRequest):
    """Synthesize text into speech, broadcast SPEAKING state to UI Orb, and return audio."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    audio_bytes = await voice_service.speak_response(request.text)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Failed to generate speech")

    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    return {
        "status": "success",
        "audio_base64": f"data:audio/mp3;base64,{b64_audio}",
    }


@router.post("/stop")
async def stop_voice_service():
    """Explicitly stop background voice listening loop."""
    voice_service.stop()
    return {"status": "stopped", "is_listening": False}


@router.post("/start")
async def start_voice_service():
    """Explicitly start background voice listening loop."""
    voice_service.start()
    return {"status": "started", "is_listening": True}


@router.get("/status")
async def speech_status():
    """Get status of voice and conversation state machine."""
    return {
        "is_listening": voice_service.is_running,
        "conversation_state": voice_service.state_machine.current_state,
        "ai_state": voice_service.state_machine.ai_state.value,
        "continuous_conversation": voice_service.state_machine.continuous_conversation,
    }
