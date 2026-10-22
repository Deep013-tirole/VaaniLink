"""
Tests for RomanizationDetector (Section 15 requirements).
"""

from apps.nlp.romanization_detector import RomanizationDetector


class TestRomanizationDetector:
    def test_hinglish_detection_me_nahi_aaunga(self):
        text = "me nahi aaunga"
        res = RomanizationDetector.analyze(text)
        assert res.is_romanized is True
        assert res.detected_language == "hi"
        assert res.confidence >= 0.70

    def test_hinglish_detection_kal_meeting_hai_kya(self):
        text = "kal meeting hai kya?"
        res = RomanizationDetector.analyze(text)
        assert res.is_romanized is True
        assert res.detected_language == "hi"

    def test_hinglish_detection_mujhe_project_submit_karna_hai(self):
        text = "mujhe project submit karna hai"
        res = RomanizationDetector.analyze(text)
        assert res.is_romanized is True
        assert res.detected_language == "hi"

    def test_standard_english_not_romanized(self):
        text = "Are you coming tomorrow for the presentation?"
        res = RomanizationDetector.analyze(text)
        assert res.is_romanized is False
        assert res.detected_language == "en"
