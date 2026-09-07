"""
Tests for Markus AI Multilingual NLP & Intent Understanding Engine
"""

import os
import sys
import unittest

# Ensure markus package root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.constants import IntentType
from core.nlp_processor import nlp_processor
from core.intent_classifier import intent_classifier
from core.voice_command_processor import voice_command_processor


class TestNLPProcessor(unittest.TestCase):

    def test_language_detection(self):
        self.assertEqual(nlp_processor.detect_language("Open Google Chrome"), "en")
        self.assertEqual(nlp_processor.detect_language("குரோமை திறக்கவும்"), "ta")
        self.assertEqual(nlp_processor.detect_language("ஸ்கிரீன்ஷாட் எடு"), "ta")
        self.assertEqual(nlp_processor.detect_language("chrome-ஐ திறக்கவும்"), "mixed")
        self.assertEqual(nlp_processor.detect_language("Chrome open pannu"), "mixed")

    def test_tamil_morphology_stripping(self):
        # Accusative -ஐ
        self.assertEqual(nlp_processor.strip_tamil_morphology("chrome-ஐ"), "chrome")
        # Locative -இல் / -ல
        self.assertEqual(nlp_processor.strip_tamil_morphology("youtube-இல்"), "youtube")
        self.assertEqual(nlp_processor.strip_tamil_morphology("youtube-ல"), "youtube")
        # Dative -க்கு
        self.assertEqual(nlp_processor.strip_tamil_morphology("system-க்கு"), "system")

    def test_app_target_extraction(self):
        self.assertEqual(nlp_processor.extract_app_target("குரோம் திற"), "chrome")
        self.assertEqual(nlp_processor.extract_app_target("chrome-ஐ திற"), "chrome")
        self.assertEqual(nlp_processor.extract_app_target("விஸ்கோடு திற"), "code")
        self.assertEqual(nlp_processor.extract_app_target("open notepad please"), "notepad")
        self.assertEqual(nlp_processor.extract_app_target("calculator மூடு"), "calc")

    def test_screenshot_parsing(self):
        tamil_intent = nlp_processor.parse_intent("ஸ்கிரீன்ஷாட் எடு")
        self.assertEqual(tamil_intent.action, "screenshot")
        self.assertEqual(tamil_intent.intent, IntentType.SYSTEM_CONTROL)
        self.assertGreaterEqual(tamil_intent.confidence, 0.9)

        english_intent = nlp_processor.parse_intent("capture screen snap")
        self.assertEqual(english_intent.action, "screenshot")
        self.assertEqual(english_intent.intent, IntentType.SYSTEM_CONTROL)

    def test_volume_controls(self):
        # Mute
        mute_res = nlp_processor.parse_intent("சத்தம் மியூட் செய்")
        self.assertEqual(mute_res.action, "volume_mute")

        # Volume Down
        down_res = nlp_processor.parse_intent("வால்யூம் குறை")
        self.assertEqual(down_res.action, "volume_down")

        # Volume Up
        up_res = nlp_processor.parse_intent("வால்யூம் கூட்டு")
        self.assertEqual(up_res.action, "volume_up")

        # Volume Set
        set_res = nlp_processor.parse_intent("வால்யூம் 70")
        self.assertEqual(set_res.action, "volume_set")
        self.assertEqual(set_res.slots.get("level"), 70)

    def test_app_open_and_close(self):
        open_res = nlp_processor.parse_intent("chrome-ஐ திற")
        self.assertEqual(open_res.action, "open_app")
        self.assertEqual(open_res.target, "chrome")

        close_res = nlp_processor.parse_intent("குரோம் மூடு")
        self.assertEqual(close_res.action, "close_app")
        self.assertEqual(close_res.target, "chrome")

    def test_youtube_intent(self):
        yt_res = nlp_processor.parse_intent("youtube-ல இளையராஜா பாட்டு போடு")
        self.assertEqual(yt_res.action, "youtube_play")
        self.assertEqual(yt_res.intent, IntentType.YOUTUBE)
        self.assertIn("இளையராஜா", yt_res.target)

    def test_intent_classifier_multilingual(self):
        self.assertEqual(intent_classifier.classify("chrome-ஐ திற"), IntentType.APP_CONTROL)
        self.assertEqual(intent_classifier.classify("ஸ்கிரீன்ஷாட் எடு"), IntentType.SYSTEM_CONTROL)
        self.assertEqual(intent_classifier.classify("youtube-ல இளையராஜா பாட்டு போடு"), IntentType.YOUTUBE)

    def test_voice_command_processor_multilingual_fallback(self):
        # Test recognition through try_execute
        res = voice_command_processor.try_execute("வால்யூம் குறை")
        self.assertTrue(res.matched)
        self.assertEqual(res.action, "volume_down")

    def test_web_target_and_youtube_open(self):
        from actions.app_controller import app_controller, get_web_target_url
        from core.verifier import verifier

        # 1. Verify web target detection
        self.assertTrue(app_controller.is_web_target("youtube"))
        self.assertTrue(app_controller.is_web_target("github"))
        self.assertEqual(get_web_target_url("youtube"), "https://www.youtube.com")

        # 2. Verify target candidate processes map to browsers instead of youtube.exe
        candidates = verifier._get_target_process_names("youtube")
        self.assertIn("chrome.exe", candidates)
        self.assertNotIn("youtube.exe", candidates)

        # 3. Verify try_execute recognizes open youtube cleanly
        res = voice_command_processor.try_execute("open youtube")
        self.assertTrue(res.matched)
        self.assertNotIn("youtube.exe", res.response)


if __name__ == "__main__":
    unittest.main()
