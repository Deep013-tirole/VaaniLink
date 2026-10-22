"""
Realtime presence API routing.
Mounted at /api/v1/presence/
"""

from django.urls import path

from apps.realtime.api.views import BulkUserPresenceView, UserPresenceView

urlpatterns = [
    path("users/", BulkUserPresenceView.as_view(), name="bulk_user_presence"),
    path("users/<uuid:id>/", UserPresenceView.as_view(), name="user_presence"),
]
