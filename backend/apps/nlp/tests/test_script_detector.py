"""
Tests for ScriptDetector.
"""

from apps.nlp.script_detector import ScriptDetector


class TestScriptDetector:
    def test_devanagari_detection(self):
        text = "मैं कल नहीं आऊँगा।"
        assert ScriptDetector.detect_primary_script(text) == "Deva"

    def test_gujarati_detection(self):
        text = "હું કાલે નહીં આવીશ."
        assert ScriptDetector.detect_primary_script(text) == "Gujr"

    def test_bengali_detection(self):
        text = "আমি কাল আসব না।"
        assert ScriptDetector.detect_primary_script(text) == "Beng"

    def test_arabic_detection(self):
        text = "مرحبا كيف حالك"
        assert ScriptDetector.detect_primary_script(text) == "Arab"

    def test_latin_detection(self):
        text = "Are you coming tomorrow?"
        assert ScriptDetector.detect_primary_script(text) == "Latn"

    def test_gurmukhi_detection(self):
        text = "ਮੈਂ ਕੱਲ੍ਹ ਨਹੀਂ ਆਵਾਂਗਾ।"
        assert ScriptDetector.detect_primary_script(text) == "Guru"

    def test_mixed_scripts_distribution(self):
        text = "Hello हिन्दी"
        dist = ScriptDetector.detect_scripts(text)
        assert "Latn" in dist
        assert "Deva" in dist
