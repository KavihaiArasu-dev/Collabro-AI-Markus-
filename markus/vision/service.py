"""
Markus AI — Vision Service Orchestrator
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
import numpy as np

from vision.face_tracker import FaceTracker
from vision.face_recognition import FaceRecognizer
from vision.emotion import EmotionEstimator

logger = logging.getLogger(__name__)


class VisionService:
    """
    Coordinates face tracking, identity recognition, and expression analysis.
    """

    def __init__(self):
        self.face_tracker = FaceTracker()
        self.face_recognizer = FaceRecognizer()
        self.emotion_estimator = EmotionEstimator()
        self.is_active = True

    def analyze_frame_data(self, image_np: np.ndarray) -> Dict[str, Any]:
        """
        Detect faces, recognize identity, and estimate emotional expressions.
        """
        if image_np is None or image_np.size == 0:
            return {
                "face_present": False,
                "face_count": 0,
                "expression": "neutral",
                "expression_confidence": 0.0,
                "faces": [],
                "hedged_description": "No face detected in camera frame.",
            }

        boxes = self.face_tracker.detect_faces(image_np)
        tracked_faces = self.face_tracker.track_and_normalize(image_np, boxes)

        faces_output: List[Dict[str, Any]] = []
        dominant_expression = "neutral"
        dominant_confidence = 0.85

        for idx, f in enumerate(tracked_faces):
            bbox = f["bbox"]
            x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
            face_crop = image_np[y:y + h, x:x + w]
            if face_crop.size == 0:
                face_crop = image_np

            # 1. Face Recognition / Identity Matching with landmarks alignment
            landmarks = f.get("landmarks")
            identity, id_conf = self.face_recognizer.recognize_face(
                image_np,
                bbox=(x, y, w, h),
                landmarks=landmarks,
            )
            label = f"{identity}" if identity != "Unknown" else "Unknown"

            # 2. Emotion Estimation
            expression, exp_conf, scores = self.emotion_estimator.estimate_expression(face_crop, landmarks=landmarks)

            if idx == 0:
                dominant_expression = expression
                dominant_confidence = exp_conf

            faces_output.append({
                "track_id": f["track_id"],
                "identity": identity,
                "label": label,
                "expression": expression,
                "expression_confidence": exp_conf,
                "emotion_scores": scores,
                "bbox": bbox,
                "normalized_bbox": f["normalized_bbox"],
            })

        face_count = len(faces_output)
        face_present = face_count > 0

        hedged_desc = (
            f"Detected {face_count} face(s). Primary expression appears {dominant_expression}."
            if face_present
            else "No face detected in camera view."
        )

        return {
            "face_present": face_present,
            "face_count": face_count,
            "expression": dominant_expression,
            "expression_confidence": dominant_confidence,
            "faces": faces_output,
            "hedged_description": hedged_desc,
        }

    def register_face(self, name: str, image_np: np.ndarray) -> bool:
        """Register a user's face from the camera image."""
        boxes = self.face_tracker.detect_faces(image_np)
        if not boxes:
            # Fallback: register center region if detector is uncertain
            h, w = image_np.shape[:2]
            return self.face_recognizer.register_face(name, image_np, bbox=(int(w * 0.2), int(h * 0.1), int(w * 0.6), int(h * 0.8)))

        det = boxes[0]
        bbox = det.get("bbox")
        landmarks = det.get("landmarks")
        return self.face_recognizer.register_face(name, image_np, bbox=bbox, landmarks=landmarks)

    def get_known_faces(self) -> List[str]:
        return self.face_recognizer.get_registered_names()

    def remove_face(self, name: str) -> bool:
        return self.face_recognizer.remove_face(name)


vision_service = VisionService()
