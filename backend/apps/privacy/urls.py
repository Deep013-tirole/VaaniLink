"""
Privacy settings URL routing.
Mounted at /api/v1/privacy/
"""

from django.urls import path

from apps.privacy.api.views import PrivacySettingView

urlpatterns = [
    path("", PrivacySettingView.as_view(), name="privacy_settings"),
]
