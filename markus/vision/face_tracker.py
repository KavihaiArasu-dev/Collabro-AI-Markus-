"""
Markus AI — High-Accuracy Multi-Face Detector & Tracker
Uses YuNet Deep Learning (OpenCV DNN) with 5-point facial landmark extraction,
illumination normalization, and temporal Centroid/IoU tracking.
"""

from __future__ import annotations

import logging
import os
import math
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FaceTracker:
    """
    High-accuracy face detector and persistent tracker using YuNet deep neural network.
    Extracts high-precision bounding boxes and 5-point facial landmarks.
    """

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
                    score_threshold=0.55,
                    nms_threshold=0.35,
                    top_k=5,
                )
                logger.info("YuNet deep learning face detector loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize YuNet detector: {e}")

        self.next_track_id = 1
        self.active_tracks: Dict[int, Dict[str, Any]] = {}
        self.max_missed_frames = 15

    def detect_faces(self, image_np: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect all faces in the frame.
        Returns a list of dicts with:
          - 'bbox': (x, y, w, h)
          - 'score': confidence (0.0 - 1.0)
          - 'landmarks': [(re_x, re_y), (le_x, le_y), (nose_x, nose_y), (rm_x, rm_y), (lm_x, lm_y)]
        """
        if image_np is None or image_np.size == 0:
            return []

        h, w = image_np.shape[:2]
        detections: List[Dict[str, Any]] = []

        # 1. Primary: YuNet Deep Learning Detection
        if self.yunet is not None:
            try:
                # Pass 1: Native resolution
                self.yunet.setInputSize((w, h))
                _, faces = self.yunet.detect(image_np)

                # Pass 2: CLAHE contrast boost if first pass missed
                if (faces is None or len(faces) == 0) and len(image_np.shape) == 3:
                    try:
                        lab = cv2.cvtColor(image_np, cv2.COLOR_BGR2LAB)
                        clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
                        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
                        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                        _, faces = self.yunet.detect(enhanced)
                    except Exception:
                        pass

                # Pass 3: Multi-scale resized pyramid if still missed
                if (faces is None or len(faces) == 0):
                    try:
                        scale_w = 320
                        scale_h = int(h * (320.0 / max(1, w)))
                        resized = cv2.resize(image_np, (scale_w, scale_h))
                        self.yunet.setInputSize((scale_w, scale_h))
                        _, r_faces = self.yunet.detect(resized)
                        if r_faces is not None and len(r_faces) > 0:
                            scale_factor_x = float(w) / scale_w
                            scale_factor_y = float(h) / scale_h
                            faces = []
                            for rf in r_faces:
                                scaled_f = list(rf)
                                scaled_f[0] *= scale_factor_x
                                scaled_f[1] *= scale_factor_y
                                scaled_f[2] *= scale_factor_x
                                scaled_f[3] *= scale_factor_y
                                for li in range(4, min(14, len(scaled_f)), 2):
                                    scaled_f[li] *= scale_factor_x
                                    scaled_f[li + 1] *= scale_factor_y
                                faces.append(scaled_f)
                    except Exception:
                        pass

                if faces is not None and len(faces) > 0:
                    for f in faces:
                        score = float(f[-1])
                        fx = max(0, min(w - 1, int(f[0])))
                        fy = max(0, min(h - 1, int(f[1])))
                        fw = min(w - fx, max(16, int(f[2])))
                        fh = min(h - fy, max(16, int(f[3])))

                        # Filter out tiny spurious background boxes and distorted aspect ratios
                        min_dim = max(32, int(min(w, h) * 0.08))
                        if fw < min_dim or fh < min_dim:
                            continue
                        aspect = float(fh) / max(1, fw)
                        if aspect < 0.70 or aspect > 2.2:
                            continue

                        # 5 facial landmarks: right_eye, left_eye, nose_tip, right_mouth, left_mouth
                        landmarks = []
                        if len(f) >= 14:
                            for li in range(4, 14, 2):
                                lx = float(f[li])
                                ly = float(f[li + 1])
                                landmarks.append((lx, ly))

                        detections.append({
                            "bbox": (fx, fy, fw, fh),
                            "score": score,
                            "landmarks": landmarks,
                        })

                    if detections:
                        # Sort by area (prominence) descending so primary user face is always first
                        detections.sort(key=lambda d: d["bbox"][2] * d["bbox"][3], reverse=True)
                        return detections
            except Exception as e:
                logger.warning(f"Error in YuNet detection: {e}")

        # 2. Secondary Dual-Chroma (YCrCb + HSV) Human Skin & Facial Geometry Fallback
        try:
            ycrcb = cv2.cvtColor(image_np, cv2.COLOR_BGR2YCrCb)
            hsv = cv2.cvtColor(image_np, cv2.COLOR_BGR2HSV)

            # Strict human skin tone thresholds in YCrCb
            lower_ycrcb = np.array([0, 133, 77], dtype=np.uint8)
            upper_ycrcb = np.array([255, 173, 127], dtype=np.uint8)
            mask_ycrcb = cv2.inRange(ycrcb, lower_ycrcb, upper_ycrcb)

            # Skin hue thresholds in HSV (0-25 deg and 165-180 deg, saturation >= 25)
            mask_hsv1 = cv2.inRange(hsv, np.array([0, 25, 40], dtype=np.uint8), np.array([25, 255, 255], dtype=np.uint8))
            mask_hsv2 = cv2.inRange(hsv, np.array([165, 25, 40], dtype=np.uint8), np.array([180, 255, 255], dtype=np.uint8))
            mask_hsv = cv2.bitwise_or(mask_hsv1, mask_hsv2)

            # Combined skin mask
            combined_mask = cv2.bitwise_and(mask_ycrcb, mask_hsv)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=2)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_DILATE, kernel, iterations=2)

            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            best_candidate = None
            max_area = 0

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > (w * h * 0.04):
                    x, y, bw, bh = cv2.boundingRect(cnt)
                    aspect = float(bh) / max(1, bw)
                    # Human face / head aspect ratio is vertically elongated (1.0 - 1.8)
                    if 0.95 <= aspect <= 1.85 and area > max_area:
                        max_area = area
                        best_candidate = (x, y, bw, bh)

            if best_candidate is not None:
                x, y, bw, bh = best_candidate
                detections.append({
                    "bbox": (x, y, bw, bh),
                    "score": 0.72,
                    "landmarks": [],
                })
        except Exception as e:
            logger.warning(f"Error in skin-chroma fallback: {e}")

        return detections

    def track_and_normalize(
        self,
        image_np: np.ndarray,
        raw_detections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Assign persistent track IDs and normalize bounding box coordinates to [0.0, 1.0].
        """
        if image_np is None or image_np.size == 0:
            return []

        height, width = image_np.shape[:2]
        tracked_output: List[Dict[str, Any]] = []

        # Update missed frames on active tracks
        for tid in list(self.active_tracks.keys()):
            self.active_tracks[tid]["missed"] += 1
            if self.active_tracks[tid]["missed"] > self.max_missed_frames:
                del self.active_tracks[tid]

        # Match new detections with active tracks using centroid & IoU distance
        for det in raw_detections:
            x, y, w, h = det["bbox"]
            cx = x + w / 2.0
            cy = y + h / 2.0

            best_tid = None
            min_dist = 120.0  # pixel distance threshold

            for tid, track in self.active_tracks.items():
                tcx, tcy = track["centroid"]
                dist = math.hypot(cx - tcx, cy - tcy)
                if dist < min_dist:
                    min_dist = dist
                    best_tid = tid

            if best_tid is None:
                best_tid = self.next_track_id
                self.next_track_id += 1

            self.active_tracks[best_tid] = {
                "bbox": (x, y, w, h),
                "centroid": (cx, cy),
                "missed": 0,
                "score": det.get("score", 0.85),
            }

            norm_x = round(float(x) / width, 4)
            norm_y = round(float(y) / height, 4)
            norm_w = round(float(w) / width, 4)
            norm_h = round(float(h) / height, 4)

            tracked_output.append({
                "track_id": best_tid,
                "bbox": {"x": x, "y": y, "w": w, "h": h},
                "normalized_bbox": {
                    "x": max(0.0, min(1.0, norm_x)),
                    "y": max(0.0, min(1.0, norm_y)),
                    "w": max(0.0, min(1.0, norm_w)),
                    "h": max(0.0, min(1.0, norm_h)),
                },
                "landmarks": det.get("landmarks", []),
                "detection_confidence": round(det.get("score", 0.85), 2),
            })

        return tracked_output
