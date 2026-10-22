"""
URLs for languages app.
"""

from django.urls import path

from apps.languages.api.views import LanguageListView

urlpatterns = [
    path("", LanguageListView.as_view(), name="language_list"),
]
