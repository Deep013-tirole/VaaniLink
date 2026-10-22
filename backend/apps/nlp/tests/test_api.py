"""
Tests for NLP REST API endpoints.
"""

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestNLPAPI:
    def test_nlp_analyze_endpoint(self):
        client = APIClient()
        res = client.post(
            "/api/v1/nlp/analyze/",
            {"text": "me kal nahi aaunga 😊"},
            format="json",
        )
        assert res.status_code == 200
        data = res.data
        assert data["detected_primary_language"] == "hi"
        assert data["detected_script"] == "Latn"
        assert data["is_romanized"] is True
        assert data["language_confidence"] >= 0.70

    def test_nlp_transliterate_endpoint(self):
        client = APIClient()
        res = client.post(
            "/api/v1/nlp/transliterate/",
            {"text": "kal milte hain", "target_script": "Deva"},
            format="json",
        )
        assert res.status_code == 200
        assert res.data["transliterated_text"] == "कल मिलते हैं"
