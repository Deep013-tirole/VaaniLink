"""
Tests for CodeMixedDetector (Section 16 requirements).
"""

from apps.nlp.code_mixed_detector import CodeMixedDetector


class TestCodeMixedDetector:
    def test_code_mixed_bro_kal_meeting_kitne_baje_hai(self):
        text = "Bro kal meeting kitne baje hai?"
        tokens, is_mixed, langs = CodeMixedDetector.analyze(text)
        assert is_mixed is True
        assert "hi" in langs
        assert "en" in langs

    def test_code_mixed_cancel_the_plan(self):
        text = "I think we should cancel the plan, kya bolte ho?"
        tokens, is_mixed, langs = CodeMixedDetector.analyze(text)
        assert is_mixed is True
        assert "hi" in langs
        assert "en" in langs

    def test_pure_english_not_code_mixed(self):
        text = "The quick brown fox jumps over the lazy dog."
        tokens, is_mixed, langs = CodeMixedDetector.analyze(text)
        assert is_mixed is False
        assert langs == ["en"]
