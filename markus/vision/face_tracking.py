"""
Markus AI — Face Tracking Subsystem (§6c)
Centroid-based multi-face tracking with distance thresholding and expiration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math


@dataclass
class TrackedFace:
    track_id: int
    bbox: Tuple[int, int, int, int]
    centroid: Tuple[float, float]
    last_seen: float


class FaceTracker:
    """Centroid-based persistent tracker for multiple faces."""

    def __init__(
        self,
        redetect_every_n_frames: int = 5,
        distance_threshold: float = 50.0,
        max_disappeared_seconds: float = 1.0,
    ):
        self.redetect_every_n_frames = redetect_every_n_frames
        self.distance_threshold = distance_threshold
        self.max_disappeared_seconds = max_disappeared_seconds
        self.next_track_id = 1
        self.tracked_faces: Dict[int, TrackedFace] = {}

    def _compute_centroid(self, box: Tuple[int, int, int, int]) -> Tuple[float, float]:
        x, y, w, h = box
        return (float(x + w / 2.0), float(y + h / 2.0))

    def update(
        self,
        detected_boxes: Optional[List[Tuple[int, int, int, int]]] = None,
        current_time: float = 0.0,
    ) -> List[TrackedFace]:
        """Update active face tracks with new bounding boxes."""
        # Purge stale tracks
        expired = [
            tid
            for tid, tf in self.tracked_faces.items()
            if (current_time - tf.last_seen) > self.max_disappeared_seconds
        ]
        for tid in expired:
            del self.tracked_faces[tid]

        if not detected_boxes:
            return list(self.tracked_faces.values())

        # Match detected boxes to existing tracks
        for box in detected_boxes:
            centroid = self._compute_centroid(box)
            matched_id = None
            min_dist = float("inf")

            for tid, tf in self.tracked_faces.items():
                dx = centroid[0] - tf.centroid[0]
                dy = centroid[1] - tf.centroid[1]
                dist = math.hypot(dx, dy)
                if dist < self.distance_threshold and dist < min_dist:
                    min_dist = dist
                    matched_id = tid

            if matched_id is not None:
                self.tracked_faces[matched_id] = TrackedFace(
                    track_id=matched_id,
                    bbox=box,
                    centroid=centroid,
                    last_seen=current_time,
                )
            else:
                tid = self.next_track_id
                self.next_track_id += 1
                self.tracked_faces[tid] = TrackedFace(
                    track_id=tid,
                    bbox=box,
                    centroid=centroid,
                    last_seen=current_time,
                )

        return list(self.tracked_faces.values())
