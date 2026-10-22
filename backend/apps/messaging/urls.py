"""
Messaging URL configuration.
Mounted at /api/v1/messages/
"""

from django.urls import path

from apps.messaging.api.views import (
    ConversationMessageListCreateView,
    MessageDeliveredView,
    MessageDetailView,
    MessageInfoView,
)

urlpatterns = [
    path("delivered/", MessageDeliveredView.as_view(), name="messages_delivered"),
    path(
        "conversation/<uuid:id>/",
        ConversationMessageListCreateView.as_view(),
        name="conv_messages",
    ),
    path(
        "<uuid:id>/info/",
        MessageInfoView.as_view(),
        name="message_info",
    ),
    path(
        "<uuid:id>/",
        MessageDetailView.as_view(),
        name="message_detail",
    ),
]
