"""
Markus AI — Vision Service (§6c, §7)

Coordinates camera feed, face detection, face tracking, and emotion recognition.
Emits structured vision summaries instead of streaming raw video to LLMs.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

from vision.camera import camera_manager, Camera
from vision.face_tracking import FaceTracker, TrackedFace
from vision.emotion import emotion_detector, EmotionEstimate

logger = logging.getLogger(__name__)


class VisionService:
    """
    Unified vision perception manager for Markus AI.
    Processes webcam frames or uploaded image frames to detect faces and analyze emotion.
    """

    def __init__(self):
        self.camera = camera_manager
        self.tracker = FaceTracker()
        self.emotion = emotion_detector

        self.is_active = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.latest_face_count: int = 0
        self.latest_faces: list[TrackedFace] = []
        self.latest_primary_emotion: str = "neutral"
        self.latest_emotion_confidence: float = 0.80

    def analyze_frame_data(self, image_np) -> dict:
        """
        Analyze a single image/frame for accurate face detection, tracking, and emotion estimation.
        """
        if image_np is None:
            return {
                "face_present": False,
                "face_count": 0,
                "expression": "neutral",
                "expression_confidence": 0.0,
                "faces": [],
                "hedged_description": "No camera feed or face detected.",
            }

        # 1. Detect genuine faces with YuNet DNN or verified cascades
        detected_faces = self.emotion.detect_faces_detailed(image_np)

        # 2. Update tracking
        tracked_faces = self.tracker.update(detected_faces=detected_faces)

        ih, iw = image_np.shape[:2]
        primary_emotion = "neutral"
        emotion_conf = 0.80
        faces_data = []

        if tracked_faces:
            for f in tracked_faces:
                fx, fy, fw, fh = f.bbox
                x1, y1 = max(0, fx), max(0, fy)
                x2, y2 = min(iw, fx + fw), min(ih, fy + fh)

                crop = None
                if x2 > x1 and y2 > y1:
                    crop = image_np[y1:y2, x1:x2]

                estimate = self.emotion.estimate_emotion(crop, landmarks=f.landmarks)
                f.expression = estimate.primary_emotion
                f.expression_confidence = estimate.confidence

                faces_data.append({
                    "track_id": f.track_id,
                    "identity": f"TARGET #{f.track_id}",
                    "bbox": [fx, fy, fw, fh],
                    "box": {"x": fx, "y": fy, "w": fw, "h": fh},
                    "normalized_bbox": {
                        "x": round(fx / max(iw, 1), 4),
                        "y": round(fy / max(ih, 1), 4),
                        "w": round(fw / max(iw, 1), 4),
                        "h": round(fh / max(ih, 1), 4),
                    },
                    "expression": f.expression,
                    "confidence": f.expression_confidence,
                })

            primary_emotion = tracked_faces[0].expression
            emotion_conf = tracked_faces[0].expression_confidence

        self.latest_face_count = len(tracked_faces)
        self.latest_faces = tracked_faces
        self.latest_primary_emotion = primary_emotion
        self.latest_emotion_confidence = emotion_conf

        hedged_desc = (
            f"Visible facial expression appears {primary_emotion} (confidence {int(emotion_conf * 100)}%) — treat this as a rough signal, not a confirmed emotional state"
            if tracked_faces else "No face detected in view."
        )

        return {
            "face_present": len(tracked_faces) > 0,
            "face_count": len(tracked_faces),
            "expression": primary_emotion,
            "expression_confidence": emotion_conf,
            "faces": faces_data,
            "hedged_description": hedged_desc,
        }

    def start_camera_tracking(self):
        """Start background camera capture and face tracking loop."""
        if self.is_active:
            return
        if not self.camera.start():
            logger.warning("Could not start camera for continuous tracking.")
            return

        self._stop_event.clear()
        self.is_active = True
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()
        logger.info("VisionService started continuous camera face tracking")

    def stop_camera_tracking(self):
        """Stop background camera tracking loop."""
        self._stop_event.set()
        self.is_active = False
        if self._thread:
            self._thread.join(timeout=1.5)
        self.camera.stop()
        self.tracker.reset()
        logger.info("VisionService stopped camera tracking")

    def _tracking_loop(self):
        """Background continuous tracking loop."""
        while not self._stop_event.is_set():
            frame = self.camera.capture_frame()
            if frame is not None:
                self.analyze_frame_data(frame)
            time.sleep(0.1)


# Singleton instance
vision_service = VisionService()
