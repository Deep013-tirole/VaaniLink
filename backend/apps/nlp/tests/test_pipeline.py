"""
End-to-end tests for NLPPipeline.
"""

from apps.nlp.pipeline import NLPPipeline


class TestNLPPipeline:
    def test_pipeline_hinglish_with_emoji(self):
        text = "kal meeting hai kya? 😊"
        res = NLPPipeline.process(text)

        assert res.detected_primary_language == "hi"
        assert res.detected_script == "Latn"
        assert res.is_romanized is True
        assert res.transliterated_text == "कल meeting है क्या? 😊"

    def test_pipeline_native_devanagari(self):
        text = "मैं कल नहीं आऊँगा। ❤️"
        res = NLPPipeline.process(text)

        assert res.detected_primary_language == "hi"
        assert res.detected_script == "Deva"
        assert res.is_romanized is False

    def test_pipeline_native_gujarati(self):
        text = "હું કાલે નહીં આવીશ."
        res = NLPPipeline.process(text)

        assert res.detected_primary_language == "gu"
        assert res.detected_script == "Gujr"
        assert res.is_romanized is False

    def test_pipeline_code_mixed(self):
        text = "Bro kal meeting kitne baje hai?"
        res = NLPPipeline.process(text)

        assert res.is_mixed_language is True
        assert res.detected_script == "Latn"

    def test_pipeline_pure_english(self):
        text = "Are you coming tomorrow for the team dinner?"
        res = NLPPipeline.process(text)

        assert res.detected_primary_language == "en"
        assert res.detected_script == "Latn"
        assert res.is_romanized is False
        assert res.is_mixed_language is False
