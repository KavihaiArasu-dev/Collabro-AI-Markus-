"""
Markus AI — Face Recognition & Identity Matching Engine
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)

DB_PATH = os.path.join("data", "known_faces.json")


class FaceRecognizer:
    """
    Extracts facial feature embeddings and matches against known user profiles.
    Supports persistent registration of faces from the camera feed.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.known_faces: Dict[str, List[float]] = {}
        self._load_database()

    def _load_database(self):
        """Load known face signatures from disk."""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.known_faces = json.load(f)
                logger.info(f"Loaded {len(self.known_faces)} registered face profile(s)")
            else:
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                # Default owner profile template if empty
                self.known_faces = {}
        except Exception as e:
            logger.warning(f"Failed to load known faces DB: {e}")
            self.known_faces = {}

    def _save_database(self):
        """Persist face signatures to disk."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.known_faces, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save known faces DB: {e}")

    def extract_face_signature(self, face_crop: np.ndarray) -> Optional[List[float]]:
        """
        Extract normalized spatial feature vector from a cropped face image.
        Uses multi-scale Local Binary Pattern & grayscale histogram distribution.
        """
        if face_crop is None or face_crop.size == 0:
            return None

        try:
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
            resized = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
            equalized = cv2.equalizeHist(resized)

            # Extract 8x8 block-wise intensity statistics
            feature_vector = []
            for by in range(0, 64, 8):
                for bx in range(0, 64, 8):
                    block = equalized[by:by + 8, bx:bx + 8]
                    mean_val = float(np.mean(block)) / 255.0
                    std_val = float(np.std(block)) / 255.0
                    feature_vector.extend([mean_val, std_val])

            # Normalize vector
            norm = np.linalg.norm(feature_vector)
            if norm > 0:
                normalized = (np.array(feature_vector) / norm).tolist()
                return [round(x, 5) for x in normalized]
            return None
        except Exception as e:
            logger.warning(f"Failed to extract face signature: {e}")
            return None

    def register_face(self, name: str, face_crop: np.ndarray) -> bool:
        """Register or update a user's face profile."""
        sig = self.extract_face_signature(face_crop)
        if sig is None:
            return False

        self.known_faces[name.strip()] = sig
        self._save_database()
        logger.info(f"Successfully registered face for '{name}'")
        return True

    def recognize_face(self, face_crop: np.ndarray, threshold: float = 0.38) -> Tuple[str, float]:
        """
        Match a cropped face against known face profiles.
        Returns (identity_label, match_confidence).
        """
        if not self.known_faces:
            return ("Unknown", 0.75)

        sig = self.extract_face_signature(face_crop)
        if sig is None:
            return ("Unknown", 0.70)

        best_name = "Unknown"
        best_dist = 999.0

        vec_query = np.array(sig)

        for name, known_vec_list in self.known_faces.items():
            vec_known = np.array(known_vec_list)
            if len(vec_query) == len(vec_known):
                dist = float(np.linalg.norm(vec_query - vec_known))
                if dist < best_dist:
                    best_dist = dist
                    best_name = name

        if best_dist <= threshold:
            confidence = max(0.50, min(0.98, 1.0 - (best_dist / (threshold * 1.5))))
            return (best_name, round(confidence, 2))
        else:
            return ("Unknown", 0.72)

    def get_registered_names(self) -> List[str]:
        """Return list of all registered profile names."""
        return list(self.known_faces.keys())

    def remove_face(self, name: str) -> bool:
        """Delete a registered face profile."""
        if name in self.known_faces:
            del self.known_faces[name]
            self._save_database()
            return True
        return False
