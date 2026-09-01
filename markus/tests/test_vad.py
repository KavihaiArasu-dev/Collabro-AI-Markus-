"""
Unit tests for Voice Activity Detection (VAD) (§6c)
"""

import unittest
from speech.vad import VoiceActivityDetector


class TestVAD(unittest.TestCase):

    def test_vad_silence_detection(self):
        vad = VoiceActivityDetector(silence_threshold=0.02)
        silence = [0.0] * 1600
        self.assertEqual(vad.calculate_rms(silence), 0.0)
        self.assertFalse(vad.is_speech(silence))

    def test_vad_speech_detection(self):
        vad = VoiceActivityDetector(silence_threshold=0.02)
        speech = [0.08] * 1600
        rms = vad.calculate_rms(speech)
        self.assertGreater(rms, 0.02)
        self.assertTrue(vad.is_speech(speech))

    def test_vad_utterance_lifecycle(self):
        vad = VoiceActivityDetector(
            silence_threshold=0.02,
            silence_timeout=0.5,
            min_speech_duration=0.2,
            max_recording_duration=5.0,
        )

        t0 = 1000.0
        speech_frame = [0.1] * 1600
        silence_frame = [0.0] * 1600

        # 1. Start speech
        has_speech, is_complete = vad.process_frame(speech_frame, current_time=t0)
        self.assertTrue(has_speech)
        self.assertFalse(is_complete)
        self.assertTrue(vad.is_speech_active)

        # 2. Continue speech
        has_speech, is_complete = vad.process_frame(speech_frame, current_time=t0 + 0.3)
        self.assertTrue(has_speech)
        self.assertFalse(is_complete)

        # 3. Silence begins
        has_speech, is_complete = vad.process_frame(silence_frame, current_time=t0 + 0.5)
        self.assertFalse(has_speech)
        self.assertFalse(is_complete)

        # 4. Silence timeout reached
        has_speech, is_complete = vad.process_frame(silence_frame, current_time=t0 + 1.1)
        self.assertTrue(is_complete)
        self.assertFalse(vad.is_speech_active)


if __name__ == "__main__":
    unittest.main()
