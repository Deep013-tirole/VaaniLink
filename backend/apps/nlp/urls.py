"""
URL routing for NLP services.
Mounted at /api/v1/nlp/
"""

from django.urls import path

from apps.nlp.api.views import NLPAnalyzeView, NLPTransliterateView

urlpatterns = [
    path("analyze/", NLPAnalyzeView.as_view(), name="nlp_analyze"),
    path("transliterate/", NLPTransliterateView.as_view(), name="nlp_transliterate"),
]
