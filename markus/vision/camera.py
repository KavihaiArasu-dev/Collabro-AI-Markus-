"""
Markus AI — Camera & Image Processing Utilities
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Camera:
    """Helper utilities for webcam image encoding and decoding."""

    @staticmethod
    def base64_to_cv2_image(base64_str: str) -> Optional[np.ndarray]:
        """Convert a base64-encoded image string to an OpenCV BGR numpy array."""
        try:
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            image_bytes = base64.b64decode(base64_str)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            image_np = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return image_np
        except Exception as e:
            logger.warning(f"Failed to decode base64 image: {e}")
            return None

    @staticmethod
    def cv2_image_to_base64(image_np: np.ndarray, quality: int = 80) -> str:
        """Convert an OpenCV image numpy array to a JPEG base64 string."""
        try:
            _, buffer = cv2.imencode(".jpg", image_np, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            encoded = base64.b64encode(buffer).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
        except Exception as e:
            logger.warning(f"Failed to encode image to base64: {e}")
            return ""
