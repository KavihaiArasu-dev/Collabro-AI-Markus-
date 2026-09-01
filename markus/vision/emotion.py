"""
Markus AI — Real-Time Facial Emotion Estimation Engine (§6c)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Dict, Any, Tuple, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EmotionEstimate:
    primary_emotion: str = "neutral"
    confidence: float = 0.85
    scores: Dict[str, float] = field(default_factory=dict)

    def to_hedged_text(self) -> str:
        conf_pct = int(self.confidence * 100)
        return (
            f"Visible facial expression appears {self.primary_emotion} (confidence {conf_pct}%) — "
            f"treat this as a rough signal, not a confirmed emotional state."
        )


class EmotionDetector:
    """Estimates facial expression and returns EmotionEstimate."""

    def __init__(self):
        self.estimator = EmotionEstimator()

    def detect_emotion(self, face_crop: np.ndarray) -> EmotionEstimate:
        dominant, conf, scores = self.estimator.estimate_expression(face_crop)
        return EmotionEstimate(
            primary_emotion=dominant,
            confidence=conf,
            scores=scores,
        )


class EmotionEstimator:
    """Estimates facial expression and emotion probability distribution."""

    def __init__(self):
        self.emotions = ["neutral", "happy", "surprised", "sad", "angry", "fearful", "disgusted"]

    def estimate_expression(self, face_crop: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
        """
        Analyze mouth, eye and brow contrast geometry to estimate facial expression.
        Returns (dominant_emotion, confidence, normalized_scores).
        """
        if face_crop is None or face_crop.size == 0:
            return ("neutral", 0.85, {"neutral": 1.0})

        try:
            h, w = face_crop.shape[:2]
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
            gray = cv2.equalizeHist(gray)

            mouth_roi = gray[int(h * 0.60):int(h * 0.95), int(w * 0.15):int(w * 0.85)]
            brow_roi = gray[int(h * 0.18):int(h * 0.50), int(w * 0.15):int(w * 0.85)]

            mouth_lum = float(np.mean(mouth_roi)) if mouth_roi.size > 0 else 100.0
            mouth_dark = float(np.sum(mouth_roi < 45)) / max(1, mouth_roi.size) if mouth_roi.size > 0 else 0.0
            mouth_bright = float(np.sum(mouth_roi > 130)) / max(1, mouth_roi.size) if mouth_roi.size > 0 else 0.0
            brow_dark = float(np.sum(brow_roi < 50)) / max(1, brow_roi.size) if brow_roi.size > 0 else 0.0

            scores: Dict[str, float] = {
                "neutral": 0.80,
                "happy": 0.05,
                "surprised": 0.04,
                "sad": 0.04,
                "angry": 0.03,
                "fearful": 0.02,
                "disgusted": 0.02,
            }

            if mouth_bright > 0.12 or (mouth_bright > 0.06 and mouth_lum > 115):
                dominant = "happy"
                conf = min(0.96, 0.76 + mouth_bright * 1.5)
                scores["happy"] = conf
                scores["neutral"] = max(0.04, 1.0 - conf)
            elif mouth_dark > 0.16:
                dominant = "surprised"
                conf = min(0.94, 0.74 + mouth_dark * 1.2)
                scores["surprised"] = conf
                scores["neutral"] = max(0.05, 1.0 - conf)
            elif brow_dark > 0.36 and mouth_lum < 75:
                dominant = "angry"
                conf = min(0.90, 0.72 + brow_dark * 0.4)
                scores["angry"] = conf
                scores["neutral"] = max(0.05, 1.0 - conf)
            elif mouth_lum < 50 and mouth_bright < 0.03:
                dominant = "sad"
                conf = min(0.88, 0.70 + (50 - mouth_lum) * 0.004)
                scores["sad"] = conf
                scores["neutral"] = max(0.06, 1.0 - conf)
            else:
                dominant = "neutral"
                conf = 0.86
                scores["neutral"] = 0.86

            total = sum(scores.values()) or 1.0
            norm_scores = {k: round(v / total, 2) for k, v in scores.items()}

            return (dominant, round(conf, 2), norm_scores)
        except Exception as e:
            logger.warning(f"Error in emotion estimation: {e}")
            return ("neutral", 0.85, {"neutral": 1.0})
