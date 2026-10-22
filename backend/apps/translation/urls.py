"""
URL configuration for Translation app.
"""

from django.urls import path

from apps.translation.api.views import (
    DirectTranslateView,
    MessageTranslationsView,
    RetryTranslationView,
    TranslationFeedbackView,
)

app_name = "translation"

urlpatterns = [
    path("translate/", DirectTranslateView.as_view(), name="direct_translate"),
    path(
        "message/<uuid:message_id>/", MessageTranslationsView.as_view(), name="message_translations"
    ),
    path(
        "message/<uuid:message_id>/retry/", RetryTranslationView.as_view(), name="retry_translation"
    ),
    path(
        "<uuid:translation_id>/feedback/",
        TranslationFeedbackView.as_view(),
        name="translation_feedback",
    ),
]
