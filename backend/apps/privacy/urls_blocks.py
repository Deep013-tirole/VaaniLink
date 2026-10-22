"""
User block URL routing.
Mounted at /api/v1/blocks/
"""

from django.urls import path

from apps.privacy.api.views import BlockedUserDeleteView, BlockedUserListCreateView

urlpatterns = [
    path("", BlockedUserListCreateView.as_view(), name="blocked_user_list_create"),
    path("<uuid:user_id>/", BlockedUserDeleteView.as_view(), name="blocked_user_delete"),
]
