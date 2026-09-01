"""
Markus AI — Camera Capture (§6c, §7)

Handles local webcam frame capture, base64 conversions, and image preprocessing.
"""

from __future__ import annotations

import base64
import io
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class Camera:
    """
    Manages webcam capture and provides frame snapshots for face/emotion tracking.
    """

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self._cap = None
        self._is_running = False
        self._lock = threading.Lock()
        self._latest_frame = None

    def start(self) -> bool:
        """Initialize and start camera capture."""
        try:
            import cv2  # type: ignore
            with self._lock:
                if self._is_running:
                    return True
                self._cap = cv2.VideoCapture(self.camera_index)
                if not self._cap.isOpened():
                    logger.warning(f"Could not open camera index {self.camera_index}")
                    self._cap = None
                    return False
                self._is_running = True
                logger.info(f"Camera index {self.camera_index} started successfully")
                return True
        except Exception as e:
            logger.warning(f"Failed to start camera: {e}")
            return False

    def stop(self):
        """Release camera resources."""
        with self._lock:
            if self._cap:
                self._cap.release()
                self._cap = None
            self._is_running = False
            self._latest_frame = None
            logger.info("Camera stopped")

    def capture_frame(self):
        """Read latest frame from camera as numpy BGR array."""
        with self._lock:
            if not self._is_running or not self._cap:
                return None
            ret, frame = self._cap.read()
            if ret:
                self._latest_frame = frame
                return frame
            return None

    @staticmethod
    def base64_to_cv2_image(base64_str: str):
        """Convert a base64 encoded image string (data:image/jpeg;base64,...) to OpenCV numpy array."""
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            image_bytes = base64.b64decode(base64_str)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.warning(f"Failed to decode base64 image: {e}")
            return None

    @staticmethod
    def cv2_image_to_base64(frame_np, format: str = "jpeg") -> str:
        """Convert OpenCV numpy array to base64 JPEG string."""
        try:
            import cv2  # type: ignore
            ret, buffer = cv2.imencode(f".{format}", frame_np)
            if ret:
                return base64.b64encode(buffer).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to encode image to base64: {e}")
        return ""


# Singleton instance
camera_manager = Camera()
