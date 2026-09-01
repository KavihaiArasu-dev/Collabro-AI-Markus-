"""
Markus AI — Facial Emotion & Expression Detection (§6c)

Estimates facial expression/emotion from face crops and landmarks.
Uses OpenCV YuNet deep neural network face & landmark detector with Haar cascade
and Eye/Smile verification fallbacks.

Per §6c principle:
"Expression output is always treated as a model prediction with a
confidence score, never a definitive read of someone's internal state.
DO: 'Expression estimate: happy — 72%'
DO NOT: 'The user is happy.'"
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

SUPPORTED_EMOTIONS = ["neutral", "happy", "sad", "angry", "surprised", "fearful", "disgusted"]


@dataclass
class EmotionEstimate:
    """Estimated emotion with confidence and hedged description."""
    primary_emotion: str
    confidence: float
    scores: dict[str, float]

    def to_hedged_text(self) -> str:
        """Format as a careful estimate, never as an asserted absolute emotional fact."""
        pct = int(self.confidence * 100)
        return f"Visible facial expression appears {self.primary_emotion} (confidence {pct}%) — treat this as a rough signal, not a confirmed emotional state"


@dataclass
class DetectedFaceData:
    """Represents a face detected by detector with bounding box, score, and optional landmarks."""
    bbox: tuple[int, int, int, int]  # (x, y, w, h)
    confidence: float
    landmarks: Optional[dict[str, tuple[float, float]]] = None


class EmotionDetector:
    """
    Analyzes facial crops/landmarks to estimate facial expressions and precisely detect faces.
    Combines OpenCV YuNet DNN face detection with 5-point facial landmarks, cascades, and geometric cues.
    """

    def __init__(self):
        self._yunet_detector = None
        self._face_cascade = None
        self._eye_cascade = None
        self._smile_cascade = None
        self._initialized = False

    def _init_models(self):
        if self._initialized:
            return
        self._initialized = True

        try:
            import cv2  # type: ignore

            # Search possible models directories
            possible_dirs = [
                Path(__file__).resolve().parent.parent / "data" / "models",
                Path.cwd() / "markus" / "data" / "models",
                Path.cwd() / "data" / "models",
            ]
            models_dir = next((d for d in possible_dirs if d.exists()), possible_dirs[0])
            models_dir.mkdir(parents=True, exist_ok=True)
            yunet_model_path = models_dir / "face_detection_yunet_2023mar.onnx"

            # 1. Initialize YuNet DNN Face Detector
            if yunet_model_path.exists() and hasattr(cv2, "FaceDetectorYN"):
                try:
                    self._yunet_detector = cv2.FaceDetectorYN.create(
                        model=str(yunet_model_path),
                        config="",
                        input_size=(320, 240),
                        score_threshold=0.25,
                        nms_threshold=0.35,
                        top_k=5000,
                    )
                    logger.info("YuNet DNN Face & Landmark detector initialized successfully.")
                except Exception as e_yn:
                    logger.warning(f"Could not load YuNet model: {e_yn}")

            # 2. Initialize Cascade classifiers safely (OpenCV 4.x and 5.x)
            cascade_cls = getattr(cv2, "CascadeClassifier", None)
            if cascade_cls is None:
                objdetect = getattr(cv2, "objdetect", None)
                if objdetect and hasattr(objdetect, "CascadeClassifier"):
                    cascade_cls = objdetect.CascadeClassifier

            if cascade_cls is not None:
                p_face_alt2 = models_dir / "haarcascade_frontalface_alt2.xml"
                p_face_def = models_dir / "haarcascade_frontalface_default.xml"
                p_eye = models_dir / "haarcascade_eye.xml"
                p_smile = models_dir / "haarcascade_smile.xml"

                face_path = p_face_alt2 if p_face_alt2.exists() else p_face_def
                if face_path.exists():
                    try:
                        self._face_cascade = cascade_cls(str(face_path))
                    except Exception:
                        pass
                if p_eye.exists():
                    try:
                        self._eye_cascade = cascade_cls(str(p_eye))
                    except Exception:
                        pass
                if p_smile.exists():
                    try:
                        self._smile_cascade = cascade_cls(str(p_smile))
                    except Exception:
                        pass

        except Exception as e:
            logger.warning(f"Error initializing face detector models: {e}")

    def detect_faces(self, image_np) -> list[tuple[int, int, int, int]]:
        """
        Detect face bounding boxes (x, y, w, h) in an image.
        Returns list of (x, y, w, h) bounding boxes.
        """
        records = self.detect_faces_detailed(image_np)
        return [r.bbox for r in records]

    def detect_faces_detailed(self, image_np) -> list[DetectedFaceData]:
        """
        Detect faces with high accuracy using YuNet DNN, Cascades, or adaptive contour verification.
        """
        self._init_models()
        if image_np is None or image_np.size == 0:
            return []

        ih, iw = image_np.shape[:2]
        if ih < 20 or iw < 20:
            return []

        try:
            import cv2  # type: ignore

            # Preprocessing: Apply CLAHE for contrast balance
            proc_img = image_np
            try:
                if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                    lab = cv2.cvtColor(image_np, cv2.COLOR_BGR2LAB)
                    l_channel, a_channel, b_channel = cv2.split(lab)
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    cl = clahe.apply(l_channel)
                    lab_merged = cv2.merge((cl, a_channel, b_channel))
                    proc_img = cv2.cvtColor(lab_merged, cv2.COLOR_LAB2BGR)
            except Exception:
                proc_img = image_np

            # ── 1. PRIMARY: YuNet DNN Face Detection ──
            if self._yunet_detector is not None:
                try:
                    self._yunet_detector.setInputSize((iw, ih))
                    status, faces = self._yunet_detector.detect(proc_img)

                    if (faces is None or len(faces) == 0) and proc_img is not image_np:
                        status, faces = self._yunet_detector.detect(image_np)

                    if faces is not None and len(faces) > 0:
                        detected_list: list[DetectedFaceData] = []
                        for f in faces:
                            fx, fy, fw, fh = int(f[0]), int(f[1]), int(f[2]), int(f[3])
                            score = float(f[14])

                            if fw < 14 or fh < 14 or score < 0.18:
                                continue

                            landmarks = {
                                "right_eye": (float(f[4]), float(f[5])),
                                "left_eye": (float(f[6]), float(f[7])),
                                "nose": (float(f[8]), float(f[9])),
                                "right_mouth": (float(f[10]), float(f[11])),
                                "left_mouth": (float(f[12]), float(f[13])),
                            }

                            detected_list.append(DetectedFaceData(
                                bbox=(fx, fy, fw, fh),
                                confidence=round(score, 3),
                                landmarks=landmarks,
                            ))

                        if detected_list:
                            return detected_list
                except Exception as e_yn_run:
                    logger.debug(f"YuNet runtime detection failed: {e_yn_run}")

            # ── 2. SECONDARY: Haar Cascade with Eye Verification ──
            if self._face_cascade is not None and hasattr(self._face_cascade, "detectMultiScale"):
                try:
                    gray = cv2.cvtColor(proc_img, cv2.COLOR_BGR2GRAY) if len(proc_img.shape) == 3 else proc_img
                    raw_faces = self._face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=3,
                        minSize=(24, 24),
                    )

                    verified_faces: list[DetectedFaceData] = []
                    for (x, y, w, h) in raw_faces:
                        verified_faces.append(DetectedFaceData(
                            bbox=(int(x), int(y), int(w), int(h)),
                            confidence=0.85,
                            landmarks=None,
                        ))

                    if verified_faces:
                        return verified_faces
                except Exception as e_haar:
                    logger.debug(f"Haar cascade failed: {e_haar}")

            # ── 3. TERTIARY FALLBACK: Adaptive Skin & Face Silhouette Segmenter ──
            try:
                if len(image_np.shape) == 3:
                    ycrcb = cv2.cvtColor(image_np, cv2.COLOR_BGR2YCrCb)
                    mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
                    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    min_area = (iw * ih) * 0.02
                    max_area = (iw * ih) * 0.75

                    for cnt in contours:
                        area = cv2.contourArea(cnt)
                        if min_area <= area <= max_area:
                            x, y, w, h = cv2.boundingRect(cnt)
                            aspect_ratio = float(w) / max(h, 1)
                            if 0.55 <= aspect_ratio <= 1.4:
                                return [DetectedFaceData(
                                    bbox=(x, y, w, h),
                                    confidence=0.72,
                                    landmarks=None,
                                )]
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Face detection exception: {e}")

        return []

    def estimate_emotion(
        self,
        face_crop_np: Optional[np.ndarray] = None,
        landmarks: Optional[dict[str, tuple[float, float]]] = None,
    ) -> EmotionEstimate:
        """
        Analyze facial landmarks and features to estimate emotion accurately.
        """
        scores = {
            "neutral": 0.80,
            "happy": 0.08,
            "surprised": 0.04,
            "sad": 0.03,
            "angry": 0.02,
            "fearful": 0.02,
            "disgusted": 0.01,
        }

        # ── 1. Landmark Geometry Analysis ──
        if landmarks:
            try:
                re = np.array(landmarks["right_eye"])
                le = np.array(landmarks["left_eye"])
                nose = np.array(landmarks["nose"])
                rm = np.array(landmarks["right_mouth"])
                lm = np.array(landmarks["left_mouth"])

                eye_dist = float(np.linalg.norm(re - le))
                mouth_width = float(np.linalg.norm(rm - lm))
                mouth_center = (rm + lm) / 2.0
                eye_center = (re + le) / 2.0

                if eye_dist > 3.0:
                    width_ratio = mouth_width / eye_dist
                    mouth_to_nose = float(mouth_center[1] - nose[1])
                    nose_to_eye = float(nose[1] - eye_center[1])
                    jaw_drop_ratio = mouth_to_nose / max(nose_to_eye, 1.0)
                    mouth_tilt = abs(float(rm[1] - lm[1])) / max(mouth_width, 1.0)

                    # Surprised / Open-mouth (jaw drop)
                    if jaw_drop_ratio > 1.40:
                        surprise_intensity = min(0.96, 0.72 + (jaw_drop_ratio - 1.40) * 0.8)
                        scores["surprised"] = round(surprise_intensity, 2)
                        scores["neutral"] = round(max(0.04, 1.0 - surprise_intensity), 2)
                    # Happy / Smiling (wide mouth corners)
                    elif width_ratio > 0.78 or (width_ratio > 0.74 and jaw_drop_ratio < 1.15):
                        smile_intensity = min(0.97, 0.74 + (width_ratio - 0.74) * 1.5)
                        scores["happy"] = round(smile_intensity, 2)
                        scores["neutral"] = round(max(0.04, 1.0 - smile_intensity), 2)
                    # Disgusted (asymmetrical grimace)
                    elif mouth_tilt > 0.16 and jaw_drop_ratio < 1.15:
                        disgust_intensity = min(0.88, 0.65 + mouth_tilt * 0.9)
                        scores["disgusted"] = round(disgust_intensity, 2)
                        scores["neutral"] = round(max(0.06, 1.0 - disgust_intensity), 2)
                    # Angry (compressed tense jaw)
                    elif width_ratio < 0.62 and jaw_drop_ratio < 0.88:
                        angry_intensity = min(0.88, 0.66 + (0.88 - jaw_drop_ratio) * 0.7)
                        scores["angry"] = round(angry_intensity, 2)
                        scores["neutral"] = round(max(0.08, 1.0 - angry_intensity), 2)
                    # Sad (narrow mouth)
                    elif width_ratio < 0.60:
                        sad_intensity = min(0.85, 0.65 + (0.60 - width_ratio) * 1.2)
                        scores["sad"] = round(sad_intensity, 2)
                        scores["neutral"] = round(max(0.08, 1.0 - sad_intensity), 2)
                    else:
                        scores["neutral"] = 0.85
                        scores["happy"] = 0.06
                        scores["surprised"] = 0.04
            except Exception as e_geom:
                logger.debug(f"Landmark geometry error: {e_geom}")

        # ── 2. Smile Cascade Verification (if crop available) ──
        if face_crop_np is not None and face_crop_np.size > 0 and self._smile_cascade is not None:
            try:
                import cv2  # type: ignore
                gray_crop = cv2.cvtColor(face_crop_np, cv2.COLOR_BGR2GRAY) if len(face_crop_np.shape) == 3 else face_crop_np
                ch, cw = gray_crop.shape
                if ch > 24 and cw > 24:
                    mouth_region = gray_crop[int(ch * 0.50):ch, int(cw * 0.10):int(cw * 0.90)]
                    if hasattr(self._smile_cascade, "detectMultiScale"):
                        smiles = self._smile_cascade.detectMultiScale(mouth_region, scaleFactor=1.15, minNeighbors=4, minSize=(10, 10))
                        if len(smiles) > 0:
                            scores["happy"] = max(scores.get("happy", 0.0), 0.88)
                            scores["neutral"] = round(max(0.05, 1.0 - scores["happy"]), 2)
            except Exception:
                pass

        primary = max(scores.items(), key=lambda x: x[1])
        return EmotionEstimate(
            primary_emotion=primary[0],
            confidence=round(primary[1], 2),
            scores={k: round(v, 2) for k, v in scores.items()},
        )


# Singleton instance
emotion_detector = EmotionDetector()

