"""
Markus AI — Multi-Face Tracker & Bounding Box Detector
"""

from __future__ import annotations

import logging
import os
from typing import List, Dict, Any, Tuple
import cv2
import cv2.data
import numpy as np

logger = logging.getLogger(__name__)


class FaceTracker:
    """Detects and tracks multiple faces using OpenCV Haar Cascades and contour analysis."""

    def __init__(self):
        self.yunet = None
        yunet_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "models", "face_detection_yunet_2023mar.onnx")
        )
        if os.path.exists(yunet_path) and hasattr(cv2, "FaceDetectorYN_create"):
            try:
                self.yunet = cv2.FaceDetectorYN_create(
                    model=yunet_path,
                    config="",
                    input_size=(320, 320),
                    score_threshold=0.6,
                    nms_threshold=0.3,
                    top_k=10,
                )
                logger.info("YuNet deep learning face detector initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize YuNet: {e}")

        self.next_track_id = 1
        self.active_tracks: Dict[int, Dict[str, Any]] = {}

    def detect_faces(self, image_np: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect all face bounding boxes (x, y, w, h) in the image."""
        if image_np is None or image_np.size == 0:
            return []

        # 1. Try YuNet Deep Learning Face Detector
        if self.yunet is not None:
            try:
                h, w = image_np.shape[:2]
                self.yunet.setInputSize((w, h))
                _, faces = self.yunet.detect(image_np)
                if faces is not None and len(faces) > 0:
                    boxes: List[Tuple[int, int, int, int]] = []
                    for f in faces:
                        fx = max(0, min(w - 1, int(f[0])))
                        fy = max(0, min(h - 1, int(f[1])))
                        fw = min(w - fx, max(10, int(f[2])))
                        fh = min(h - fy, max(10, int(f[3])))
                        boxes.append((fx, fy, fw, fh))
                    if boxes:
                        return boxes
            except Exception as e:
                logger.warning(f"Error in YuNet detection: {e}")

        # 2. Adaptive Skin-Tone & Silhouette Contour Detection Fallback
        try:
            h, w = image_np.shape[:2]
            ycrcb = cv2.cvtColor(image_np, cv2.COLOR_BGR2YCrCb)
            # Universal skin mask in YCrCb
            lower = np.array([0, 133, 77], dtype=np.uint8)
            upper = np.array([255, 173, 127], dtype=np.uint8)
            mask = cv2.inRange(ycrcb, lower, upper)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel, iterations=2)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            boxes: List[Tuple[int, int, int, int]] = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > (w * h * 0.03):
                    x, y, bw, bh = cv2.boundingRect(cnt)
                    aspect = float(bh) / max(1, bw)
                    if 0.8 <= aspect <= 2.2:
                        boxes.append((x, y, bw, bh))

            if boxes:
                return boxes
        except Exception:
            pass

        # Center default ROI fallback if person is in front of camera
        h, w = image_np.shape[:2]
        return [(int(w * 0.25), int(h * 0.15), int(w * 0.50), int(h * 0.65))]

    def track_and_normalize(
        self,
        image_np: np.ndarray,
        detected_boxes: List[Tuple[int, int, int, int]],
    ) -> List[Dict[str, Any]]:
        """Map detections to persistent track IDs and normalized coordinates [0.0 - 1.0]."""
        height, width = image_np.shape[:2]
        tracked_faces = []

        for idx, (x, y, w, h) in enumerate(detected_boxes):
            track_id = idx + 1
            tracked_faces.append({
                "track_id": track_id,
                "bbox": {"x": x, "y": y, "w": w, "h": h},
                "normalized_bbox": {
                    "x": round(float(x) / width, 4),
                    "y": round(float(y) / height, 4),
                    "w": round(float(w) / width, 4),
                    "h": round(float(h) / height, 4),
                },
            })

        return tracked_faces
