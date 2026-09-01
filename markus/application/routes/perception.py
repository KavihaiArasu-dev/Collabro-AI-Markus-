"""
Markus AI — Multimodal Perception API Routes (§6c, §9)

Provides endpoints to query and update the fused multimodal state (audio + vision).
"""

from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from brain.perception import perception_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/perception", tags=["Perception"])


class AudioUpdatePayload(BaseModel):
    transcript: Optional[str] = None
    speaking: Optional[bool] = None
    wake_word_detected: Optional[bool] = None
    energy_level: Optional[float] = None


class VisionUpdatePayload(BaseModel):
    face_present: Optional[bool] = None
    face_count: Optional[int] = None
    expression: Optional[str] = None
    expression_confidence: Optional[float] = None


@router.get("/context")
async def get_perception_context():
    """Retrieve the current fused multimodal perception state."""
    ctx = perception_manager.get_context()
    return {
        "context": ctx.to_dict(),
        "prompt_context": ctx.to_prompt_context(),
    }


@router.post("/update/audio")
async def update_audio_perception(payload: AudioUpdatePayload):
    """Update audio perception channel."""
    ctx = perception_manager.update_audio(
        transcript=payload.transcript or "",
        speaking=payload.speaking or False,
        wake_word_detected=payload.wake_word_detected or False,
        energy_level=payload.energy_level or 0.0,
    )
    return {"status": "ok", "context": ctx.to_dict()}


@router.post("/update/vision")
async def update_vision_perception(payload: VisionUpdatePayload):
    """Update vision perception channel."""
    ctx = perception_manager.update_vision(
        face_present=payload.face_present if payload.face_present is not None else False,
        face_count=payload.face_count or 0,
        expression=payload.expression or "neutral",
        expression_confidence=payload.expression_confidence or 0.80,
    )
    return {"status": "ok", "context": ctx.to_dict()}
