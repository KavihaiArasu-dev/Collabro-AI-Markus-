"""
Unit tests for Face Tracking and Emotion Detection (§6c)
"""

import unittest
from vision.face_tracking import FaceTracker
from vision.emotion import EmotionDetector, EmotionEstimate


class TestFaceTracking(unittest.TestCase):

    def test_face_tracker_tracks_and_centroids(self):
        tracker = FaceTracker(redetect_every_n_frames=5, distance_threshold=50.0)

        # Frame 1: detect 1 face at (100, 100, 50, 50)
        box1 = (100, 100, 50, 50)
        tracks = tracker.update(detected_boxes=[box1], current_time=100.0)

        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].track_id, 1)
        self.assertEqual(tracks[0].centroid, (125.0, 125.0))

        # Frame 2: minor movement (105, 102, 50, 50) - should retain track_id = 1
        box2 = (105, 102, 50, 50)
        tracks2 = tracker.update(detected_boxes=[box2], current_time=100.1)

        self.assertEqual(len(tracks2), 1)
        self.assertEqual(tracks2[0].track_id, 1)
        self.assertEqual(tracks2[0].centroid, (130.0, 127.0))

    def test_face_tracker_purges_disappeared_faces(self):
        tracker = FaceTracker(max_disappeared_seconds=1.0)
        box = (50, 50, 40, 40)

        tracker.update(detected_boxes=[box], current_time=100.0)
        self.assertEqual(len(tracker.tracked_faces), 1)

        # Time jumps by 2 seconds with no detections
        tracks = tracker.update(detected_boxes=None, current_time=102.5)
        self.assertEqual(len(tracks), 0)

    def test_emotion_detector_hedged_format(self):
        estimate = EmotionEstimate(
            primary_emotion="happy",
            confidence=0.84,
            scores={"happy": 0.84, "neutral": 0.16},
        )

        hedged = estimate.to_hedged_text()
        self.assertIn("Visible facial expression appears happy (confidence 84%)", hedged)
        self.assertIn("treat this as a rough signal, not a confirmed emotional state", hedged)
        # Ensure it never asserts emotion as hard fact
        self.assertNotIn("The user is happy", hedged)


if __name__ == "__main__":
    unittest.main()
