"""
User management and profile URLs.
Mounted at /api/v1/users/
"""

from django.urls import path

from apps.accounts.api.views import UserMeUpdateView, UserSearchView

urlpatterns = [
    path("me/", UserMeUpdateView.as_view(), name="user_me_update"),
    path("search/", UserSearchView.as_view(), name="user_search"),
]
