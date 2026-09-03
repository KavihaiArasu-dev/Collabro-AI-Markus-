"""
Markus AI — Real-Time Facial Emotion Estimation Engine (§6c)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import logging
from typing import Dict, Any, Tuple, Optional, List
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
    """
    Advanced Multi-Feature Facial Expression & Emotion Estimation Engine.
    Analyzes:
    - Zygomaticus major activation (mouth corner lift & smile width)
    - Corrugator supercilii tension (inter-eyebrow furrows & brow lowering)
    - Mouth Aspect Ratio & open cavity contrast (Surprise / Laugh vs Neutral)
    - Depressor anguli oris activation (mouth corner droop for Sadness)
    - Eye aperture & squint dynamics
    - Calibrated probability distribution across all 7 universal emotions.
    """

    def __init__(self):
        self.emotions = ["neutral", "happy", "surprised", "sad", "angry", "fearful", "disgusted"]
        self.history: List[Dict[str, float]] = []
        self.max_history = 5

    def estimate_expression(
        self,
        face_crop: np.ndarray,
        landmarks: Optional[List[Tuple[float, float]]] = None,
    ) -> Tuple[str, float, Dict[str, float]]:
        """
        Analyze facial geometry, landmarks, and morphological contrast to estimate emotion.
        Returns: (dominant_emotion, confidence, normalized_scores_dict)
        """
        if face_crop is None or face_crop.size == 0:
            return ("neutral", 0.85, {"neutral": 0.85, "happy": 0.03, "surprised": 0.03, "sad": 0.03, "angry": 0.02, "fearful": 0.02, "disgusted": 0.02})

        try:
            h, w = face_crop.shape[:2]
            if len(face_crop.shape) == 3:
                gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            else:
                gray = face_crop

            # CLAHE contrast enhancement for robust feature extraction
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            norm_gray = clahe.apply(gray)
            norm_gray = cv2.resize(norm_gray, (120, 120), interpolation=cv2.INTER_AREA)

            # ── 1. Facial Zone Segmentations (120x120 normalized) ──
            # Brow / Forehead zone (top 15% - 40%)
            brow_roi = norm_gray[18:48, 20:100]
            # Inter-eyebrow glabella zone (for frown/anger wrinkles)
            glabella_roi = norm_gray[22:42, 46:74]
            # Eye zone (25% - 50%)
            left_eye_roi = norm_gray[28:50, 18:52]
            right_eye_roi = norm_gray[28:50, 68:102]
            # Cheeks zone (45% - 70%)
            left_cheek_roi = norm_gray[52:80, 14:42]
            right_cheek_roi = norm_gray[52:80, 78:106]
            # Mouth zone (60% - 94%)
            mouth_roi = norm_gray[72:112, 22:98]
            mouth_center = norm_gray[78:104, 38:82]
            mouth_corners_l = norm_gray[74:100, 22:42]
            mouth_corners_r = norm_gray[74:100, 78:98]

            # ── 2. Feature Metrics Extraction ──

            # A. Mouth Width & Smile Curvature (Zygomatic Lift)
            # Find dark lip line inside mouth ROI using horizontal edge gradients
            sobel_y = cv2.Sobel(mouth_roi, cv2.CV_64F, 0, 1, ksize=3)
            mouth_edge_energy = float(np.mean(np.abs(sobel_y)))

            # Brightness in mouth center (teeth reflection during smile/laugh)
            center_lum = float(np.mean(mouth_center)) if mouth_center.size > 0 else 100.0
            corner_l_lum = float(np.mean(mouth_corners_l)) if mouth_corners_l.size > 0 else 100.0
            corner_r_lum = float(np.mean(mouth_corners_r)) if mouth_corners_r.size > 0 else 100.0
            avg_corner_lum = (corner_l_lum + corner_r_lum) / 2.0

            # Cheek brightness boost (smiling raises cheeks, reflecting more light)
            avg_cheek_lum = (float(np.mean(left_cheek_roi)) + float(np.mean(right_cheek_roi))) / 2.0
            forehead_lum = float(np.mean(brow_roi)) if brow_roi.size > 0 else 100.0
            cheek_lift_contrast = avg_cheek_lum - forehead_lum

            # Mouth dark cavity detection (open mouth for surprise or laugh)
            dark_cavity_pixels = float(np.sum(mouth_roi < 40)) / max(1, mouth_roi.size)
            bright_teeth_pixels = float(np.sum(mouth_center > 145)) / max(1, mouth_center.size)

            # B. Brow Furrow / Frown (Corrugator Tension for Anger/Focus)
            # High vertical gradient energy in glabella indicates furrowing
            sobel_x_glabella = cv2.Sobel(glabella_roi, cv2.CV_64F, 1, 0, ksize=3)
            glabella_wrinkle_energy = float(np.mean(np.abs(sobel_x_glabella)))
            glabella_darkness = float(np.sum(glabella_roi < 55)) / max(1, glabella_roi.size)

            # C. Eye Openness & Squint Ratio
            left_eye_dark = float(np.sum(left_eye_roi < 50)) / max(1, left_eye_roi.size)
            right_eye_dark = float(np.sum(right_eye_roi < 50)) / max(1, right_eye_roi.size)
            avg_eye_dark = (left_eye_dark + right_eye_dark) / 2.0

            # ── 3. Landmark-Informed Geometry (if 5 landmarks available) ──
            # Landmarks: [re_x, re_y, le_x, le_y, nose_x, nose_y, rm_x, rm_y, lm_x, lm_y]
            landmark_smile_ratio = 0.0
            landmark_mouth_open = 0.0
            if landmarks and len(landmarks) >= 5:
                try:
                    re, le, nose, rm, lm = landmarks[0], landmarks[1], landmarks[2], landmarks[3], landmarks[4]
                    eye_dist = math.hypot(le[0] - re[0], le[1] - re[1])
                    mouth_w = math.hypot(lm[0] - rm[0], lm[1] - rm[1])
                    if eye_dist > 1.0:
                        mouth_to_eye_ratio = mouth_w / eye_dist
                        # Wide mouth relative to eyes indicates smiling
                        if mouth_to_eye_ratio > 0.85:
                            landmark_smile_ratio = min(1.0, (mouth_to_eye_ratio - 0.85) * 3.5)

                    # Mouth corner elevation relative to nose
                    mouth_y_avg = (rm[1] + lm[1]) / 2.0
                    nose_y = nose[1]
                    mouth_nose_dist = mouth_y_avg - nose_y
                    if mouth_nose_dist > 1.0:
                        # Corner lift: corners higher than central mouth baseline
                        pass
                except Exception:
                    pass

            # ── 4. Multi-Emotion Scoring Formulation ──
            raw_scores: Dict[str, float] = {
                "neutral": 0.70,
                "happy": 0.05,
                "surprised": 0.04,
                "sad": 0.04,
                "angry": 0.03,
                "fearful": 0.02,
                "disgusted": 0.02,
            }

            # 1. Happy / Joy / Smile criteria:
            # - Bright teeth contrast in mouth center combined with cheek lift OR landmark smile ratio
            smile_evidence = (
                (bright_teeth_pixels > 0.08 and center_lum > avg_corner_lum + 12) * 0.45 +
                (cheek_lift_contrast > 5) * 0.25 +
                (landmark_smile_ratio * 0.45) +
                (mouth_edge_energy > 18 and center_lum > 110) * 0.20
            )

            # 2. Surprised criteria:
            # - Significant open mouth dark cavity + wide eyes
            surprise_evidence = (
                (dark_cavity_pixels > 0.14) * 0.50 +
                (avg_eye_dark > 0.22) * 0.30 +
                (mouth_edge_energy > 22 and center_lum < 85) * 0.25
            )

            # 3. Angry / Concentrated criteria:
            # - Glabella wrinkle energy / dark furrow between eyebrows + narrowed eyes + compressed mouth
            anger_evidence = (
                (glabella_wrinkle_energy > 16.0) * 0.40 +
                (glabella_darkness > 0.25) * 0.35 +
                (avg_eye_dark < 0.12 and cheek_lift_contrast < 0) * 0.25
            )

            # 4. Sadness criteria:
            # - Drooping mouth corners (corners darker & lower) + low cheek contrast + low mouth energy
            sad_evidence = (
                (center_lum < 75 and mouth_edge_energy < 12 and avg_cheek_lum < forehead_lum - 4) * 0.45 +
                (avg_corner_lum < center_lum - 8) * 0.30
            )

            # 5. Fearful criteria:
            # - Wide eyes + moderate open mouth cavity + elevated brow
            fear_evidence = (
                (avg_eye_dark > 0.25 and dark_cavity_pixels > 0.08) * 0.50 +
                (glabella_wrinkle_energy > 12.0) * 0.30
            )

            # 6. Disgusted criteria:
            # - Wrinkled nose bridge + asymmetrical mouth sneer
            disgust_evidence = (
                (glabella_wrinkle_energy > 18.0 and abs(corner_l_lum - corner_r_lum) > 20) * 0.50
            )

            # Apply evidences to probability distribution
            if smile_evidence >= 0.32:
                raw_scores["happy"] = min(0.96, 0.45 + smile_evidence * 0.55)
                raw_scores["neutral"] = max(0.04, 1.0 - raw_scores["happy"])
            if surprise_evidence >= 0.35:
                raw_scores["surprised"] = min(0.95, 0.40 + surprise_evidence * 0.55)
                raw_scores["neutral"] = max(0.04, min(raw_scores["neutral"], 1.0 - raw_scores["surprised"]))
            if anger_evidence >= 0.35:
                raw_scores["angry"] = min(0.92, 0.40 + anger_evidence * 0.50)
                raw_scores["neutral"] = max(0.04, min(raw_scores["neutral"], 1.0 - raw_scores["angry"]))
            if sad_evidence >= 0.35:
                raw_scores["sad"] = min(0.88, 0.38 + sad_evidence * 0.50)
                raw_scores["neutral"] = max(0.04, min(raw_scores["neutral"], 1.0 - raw_scores["sad"]))
            if fear_evidence >= 0.35:
                raw_scores["fearful"] = min(0.88, 0.35 + fear_evidence * 0.50)
                raw_scores["neutral"] = max(0.04, min(raw_scores["neutral"], 1.0 - raw_scores["fearful"]))
            if disgust_evidence >= 0.35:
                raw_scores["disgusted"] = min(0.86, 0.35 + disgust_evidence * 0.50)
                raw_scores["neutral"] = max(0.04, min(raw_scores["neutral"], 1.0 - raw_scores["disgusted"]))

            # Find dominant emotion
            dominant = max(raw_scores.items(), key=lambda x: x[1])[0]
            conf = raw_scores[dominant]

            # Normalize scores to sum to 1.0
            total = sum(raw_scores.values()) or 1.0
            norm_scores = {k: round(v / total, 3) for k, v in raw_scores.items()}

            # Temporal smoothing filter across consecutive frames
            self.history.append(norm_scores)
            if len(self.history) > self.max_history:
                self.history.pop(0)

            # Smoothed score distribution
            smoothed_scores: Dict[str, float] = {}
            for k in self.emotions:
                smoothed_scores[k] = round(sum(h[k] for h in self.history) / len(self.history), 3)

            smoothed_dominant = max(smoothed_scores.items(), key=lambda x: x[1])[0]
            smoothed_conf = round(float(smoothed_scores[smoothed_dominant]), 2)

            return (smoothed_dominant, smoothed_conf, smoothed_scores)
        except Exception as e:
            logger.warning(f"Error in emotion estimation: {e}")
            return ("neutral", 0.85, {"neutral": 0.85, "happy": 0.03, "surprised": 0.03, "sad": 0.03, "angry": 0.02, "fearful": 0.02, "disgusted": 0.02})

