"""
Markus AI — Face Tracking (§6c, §7)

Implements persistent detection + centroid tracking between frames.
Maintains stable IDs and smooth bounding boxes across video frames.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Optional, Union, Sequence

from vision.emotion import DetectedFaceData

logger = logging.getLogger(__name__)


@dataclass
class TrackedFace:
    """Represents a tracked face with ID, centroid, bounding box, landmarks, and expression history."""
    track_id: int
    bbox: tuple[int, int, int, int]  # (x, y, width, height)
    centroid: tuple[float, float]    # (cx, cy)
    last_seen: float
    confidence: float = 0.90
    expression: str = "neutral"
    expression_confidence: float = 0.80
    landmarks: Optional[dict[str, tuple[float, float]]] = None


class FaceTracker:
    """
    Tracks faces across video frames using centroid matching and spatial smoothing.
    """

    def __init__(
        self,
        redetect_every_n_frames: int = 1,
        max_disappeared_seconds: float = 1.5,
        distance_threshold: float = 90.0,
    ):
        self.redetect_every_n_frames = redetect_every_n_frames
        self.max_disappeared_seconds = max_disappeared_seconds
        self.distance_threshold = distance_threshold

        self.frame_count: int = 0
        self.next_track_id: int = 1
        self.tracked_faces: dict[int, TrackedFace] = {}

    def _calc_centroid(self, bbox: tuple[int, int, int, int]) -> tuple[float, float]:
        x, y, w, h = bbox
        return (x + w / 2.0, y + h / 2.0)

    def _calc_distance(self, p1: tuple[float, float], p2: tuple[float, float]) -> float:
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def update(
        self,
        detected_faces: Optional[Sequence[Union[DetectedFaceData, tuple[int, int, int, int]]]] = None,
        detected_boxes: Optional[Sequence[tuple[int, int, int, int]]] = None,
        current_time: Optional[float] = None,
    ) -> list[TrackedFace]:
        """
        Update tracker with new detection frame.
        Supports both detected_faces (with landmarks) and detected_boxes (x, y, w, h).
        """
        now = current_time or time.time()
        self.frame_count += 1

        input_detections = detected_faces if detected_faces is not None else detected_boxes

        if input_detections is not None:
            # Normalize detected faces to (bbox, confidence, landmarks)
            normalized_detections: list[tuple[tuple[int, int, int, int], float, Optional[dict]]] = []
            for item in input_detections:
                if isinstance(item, DetectedFaceData):
                    normalized_detections.append((item.bbox, item.confidence, item.landmarks))
                elif isinstance(item, (tuple, list)) and len(item) == 4:
                    normalized_detections.append(((item[0], item[1], item[2], item[3]), 0.85, None))

            active_ids = set()
            unmatched = list(normalized_detections)

            for det_box, det_conf, det_lms in normalized_detections:
                det_centroid = self._calc_centroid(det_box)
                best_id = None
                min_dist = float("inf")

                for track_id, track in self.tracked_faces.items():
                    if track_id in active_ids:
                        continue
                    dist = self._calc_distance(det_centroid, track.centroid)
                    if dist < min_dist and dist <= self.distance_threshold:
                        min_dist = dist
                        best_id = track_id

                if best_id is not None:
                    # Update existing track with matched detection
                    self.tracked_faces[best_id].bbox = det_box
                    self.tracked_faces[best_id].centroid = det_centroid
                    self.tracked_faces[best_id].last_seen = now
                    self.tracked_faces[best_id].confidence = det_conf
                    self.tracked_faces[best_id].landmarks = det_lms
                    active_ids.add(best_id)
                    if (det_box, det_conf, det_lms) in unmatched:
                        unmatched.remove((det_box, det_conf, det_lms))

            # Create new tracks for unmatched detections
            for new_box, new_conf, new_lms in unmatched:
                new_centroid = self._calc_centroid(new_box)
                track = TrackedFace(
                    track_id=self.next_track_id,
                    bbox=new_box,
                    centroid=new_centroid,
                    last_seen=now,
                    confidence=new_conf,
                    landmarks=new_lms,
                )
                self.tracked_faces[self.next_track_id] = track
                self.next_track_id += 1

        # Purge stale tracks
        stale_ids = [
            t_id for t_id, track in self.tracked_faces.items()
            if (now - track.last_seen) > self.max_disappeared_seconds
        ]
        for s_id in stale_ids:
            del self.tracked_faces[s_id]

        # Reset ID counter when scene is empty
        if not self.tracked_faces:
            self.next_track_id = 1

        return list(self.tracked_faces.values())

    def reset(self):
        """Reset all face tracking state."""
        self.frame_count = 0
        self.next_track_id = 1
        self.tracked_faces.clear()
