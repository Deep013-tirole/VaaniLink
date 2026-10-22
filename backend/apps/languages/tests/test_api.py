"""
Tests for Language API endpoints.
"""

import pytest
from rest_framework.test import APIClient

from apps.languages.models import Language


@pytest.mark.django_db
class TestLanguageAPI:
    def setup_method(self):
        self.client = APIClient()
        Language.objects.create(
            code="hi",
            name="Hindi",
            native_name="हिन्दी",
            script_code="Deva",
            is_rtl=False,
            is_active=True,
            sort_order=2,
        )
        Language.objects.create(
            code="en",
            name="English",
            native_name="English",
            script_code="Latn",
            is_rtl=False,
            is_active=True,
            sort_order=1,
        )
        Language.objects.create(
            code="archived",
            name="Archived Language",
            native_name="Archived",
            script_code="Latn",
            is_rtl=False,
            is_active=False,
            sort_order=99,
        )

    def test_list_active_languages(self):
        response = self.client.get("/api/v1/languages/")
        assert response.status_code == 200
        codes = [item["code"] for item in response.data]
        assert "en" in codes
        assert "hi" in codes
        assert "archived" not in codes

    def test_search_languages(self):
        response = self.client.get("/api/v1/languages/?q=hin")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["code"] == "hi"

    def test_list_all_including_inactive(self):
        response = self.client.get("/api/v1/languages/?active_only=false")
        assert response.status_code == 200
        codes = [item["code"] for item in response.data]
        assert "archived" in codes
