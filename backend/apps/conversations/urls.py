"""
Conversations URL routing.
Mounted at /api/v1/conversations/
"""

from django.urls import path

from apps.conversations.api.views import (
    ConversationDetailView,
    ConversationListView,
    DirectConversationCreateView,
    GroupAddMembersView,
    GroupConversationCreateView,
    GroupDemoteAdminView,
    GroupLeaveView,
    GroupPromoteAdminView,
    GroupRemoveMemberView,
    GroupRenameView,
    GroupTransferOwnershipView,
)
from apps.messaging.api.views import (
    ConversationMessageListCreateView,
    ConversationSeenView,
)

urlpatterns = [
    path("", ConversationListView.as_view(), name="conversation_list"),
    path("direct/", DirectConversationCreateView.as_view(), name="conversation_direct_create"),
    path("group/", GroupConversationCreateView.as_view(), name="conversation_group_create"),
    path("<uuid:id>/", ConversationDetailView.as_view(), name="conversation_detail"),
    path("<uuid:id>/rename/", GroupRenameView.as_view(), name="conversation_group_rename"),
    path(
        "<uuid:id>/members/", GroupAddMembersView.as_view(), name="conversation_group_add_members"
    ),
    path(
        "<uuid:id>/members/<uuid:user_id>/",
        GroupRemoveMemberView.as_view(),
        name="conversation_group_remove_member",
    ),
    path(
        "<uuid:id>/promote/",
        GroupPromoteAdminView.as_view(),
        name="conversation_group_promote_admin",
    ),
    path(
        "<uuid:id>/demote/", GroupDemoteAdminView.as_view(), name="conversation_group_demote_admin"
    ),
    path(
        "<uuid:id>/transfer-ownership/",
        GroupTransferOwnershipView.as_view(),
        name="conversation_group_transfer_ownership",
    ),
    path("<uuid:id>/leave/", GroupLeaveView.as_view(), name="conversation_group_leave"),
    path(
        "<uuid:id>/messages/",
        ConversationMessageListCreateView.as_view(),
        name="conversation_messages",
    ),
    path(
        "<uuid:id>/seen/",
        ConversationSeenView.as_view(),
        name="conversation_seen",
    ),
]
