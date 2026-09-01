"""
Markus AI — Vision & Face Emotion API Routes (§6c, §7, §9)

Provides endpoints for:
- Frame analysis with face detection and emotion estimation (/api/vision/analyze-frame)
- Vision service status (/api/vision/status)
- Continuous tracking toggle (/api/vision/toggle)
"""

from __future__ import annotations

import base64
import logging
from typing import Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, Request
from pydantic import BaseModel

from vision.service import vision_service
from vision.camera import Camera
from brain.perception import perception_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vision", tags=["Vision"])


class FrameAnalysisRequest(BaseModel):
    image_base64: str


class ToggleCameraRequest(BaseModel):
    enabled: bool
    emotion_enabled: Optional[bool] = None


@router.post("/analyze-frame")
async def analyze_frame(
    request: Request,
):
    """
    Analyze image frame from webcam upload or base64 stream.
    Detects faces, updates centroid tracks, estimates emotion, and updates PerceptionManager.
    """
    image_np = None
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            image_base64 = body.get("image_base64") or body.get("image") or body.get("frame")
            if image_base64:
                image_np = Camera.base64_to_cv2_image(image_base64)
        except Exception as e:
            logger.warning(f"Error parsing JSON frame data: {e}")
    else:
        # Check form / multipart
        try:
            form = await request.form()
            file = form.get("file")
            if file and hasattr(file, "read"):
                file_bytes = await file.read()
                import cv2
                import numpy as np
                np_arr = np.frombuffer(file_bytes, np.uint8)
                image_np = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            else:
                image_base64 = form.get("image_base64")
                if image_base64:
                    image_np = Camera.base64_to_cv2_image(str(image_base64))
        except Exception as e:
            logger.warning(f"Error parsing form frame data: {e}")

    if image_np is None:
        raise HTTPException(status_code=400, detail="Invalid or missing image data")

    result = vision_service.analyze_frame_data(image_np)

    # Sync into multimodal PerceptionManager
    perception_manager.update_vision(
        face_present=result["face_present"],
        face_count=result["face_count"],
        expression=result["expression"],
        expression_confidence=result["expression_confidence"],
        faces=result["faces"],
    )

    return result


@router.get("/status")
async def vision_status():
    """Get current vision tracking and emotion status."""
    ctx = perception_manager.get_context()
    return {
        "camera_enabled": perception_manager.camera_enabled,
        "emotion_detection_enabled": perception_manager.emotion_detection_enabled,
        "is_tracking": vision_service.is_active,
        "face_present": ctx.vision.face_present,
        "face_count": ctx.vision.face_count,
        "expression": ctx.vision.expression,
        "expression_confidence": ctx.vision.expression_confidence,
        "hedged_description": ctx.to_prompt_context(),
    }


@router.post("/toggle")
async def toggle_vision(request: ToggleCameraRequest):
    """Toggle camera tracking and emotion detection privacy gates."""
    perception_manager.camera_enabled = request.enabled
    if request.emotion_enabled is not None:
        perception_manager.emotion_detection_enabled = request.emotion_enabled

    return {
        "camera_enabled": perception_manager.camera_enabled,
        "emotion_detection_enabled": perception_manager.emotion_detection_enabled,
        "is_tracking": perception_manager.camera_enabled,
    }


class RegisterFaceRequest(BaseModel):
    name: str
    image_base64: str


@router.post("/register-face")
async def register_face(request: RegisterFaceRequest):
    """Register a new face profile from camera image."""
    image_np = Camera.base64_to_cv2_image(request.image_base64)
    if image_np is None:
        raise HTTPException(status_code=400, detail="Invalid image data")

    success = vision_service.register_face(request.name, image_np)
    if not success:
        raise HTTPException(status_code=400, detail="No clear face detected to register")

    return {
        "status": "success",
        "name": request.name,
        "message": f"Successfully registered face profile for '{request.name}'",
        "known_faces": vision_service.get_known_faces(),
    }


@router.get("/known-faces")
async def get_known_faces():
    """List all registered face profiles."""
    return {"known_faces": vision_service.get_known_faces()}


@router.delete("/known-faces/{name}")
async def delete_face(name: str):
    """Delete a registered face profile."""
    success = vision_service.remove_face(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Face profile '{name}' not found")
    return {"status": "success", "message": f"Removed face profile '{name}'"}
