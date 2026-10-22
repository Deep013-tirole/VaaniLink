"""
Service layer for conversations.
Handles deterministic 1-to-1 conversation generation, group creation,
role-based permissions, membership management, and real-time event broadcasting.
Conforms strictly to Section 10, Section 11, Section 46, and Section 47.
"""

import uuid

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from apps.common.exceptions import ValidationError as AppValidationError
from apps.conversations.models import Conversation, ConversationMember, ConversationType, MemberRole
from apps.privacy.services import PrivacyService
from apps.realtime.services import RealtimeNotifier


class ConversationService:
    @staticmethod
    def get_or_create_direct_conversation(
        user1: User,
        user2: User,
    ) -> tuple[Conversation, bool]:
        """
        Retrieve or create a unique direct conversation between two users.
        Uses deterministic direct_key = sorted(user1_uuid, user2_uuid).
        """
        if user1.id == user2.id:
            raise ConflictError(
                message="Cannot create a direct conversation with yourself.",
                code="SELF_CONVERSATION_NOT_ALLOWED",
            )

        from apps.privacy.services import PrivacyService

        if PrivacyService.is_blocked_bidirectional(user1, user2):
            raise PermissionDeniedError(
                message="Cannot initiate a direct chat with a blocked user.",
                code="USER_BLOCKED",
            )

        direct_key = Conversation.generate_direct_key(user1.id, user2.id)

        # If conversation does not exist, verify sender is allowed to message target
        existing = Conversation.objects.filter(direct_key=direct_key).first()
        if not existing:
            if not PrivacyService.can_send_direct_message(user1, user2):
                raise PermissionDeniedError(
                    message="This user does not accept direct messages based on their privacy settings.",
                    code="DIRECT_MESSAGES_RESTRICTED",
                )

        with transaction.atomic():
            conversation, created = Conversation.objects.get_or_create(
                type=ConversationType.DIRECT,
                direct_key=direct_key,
                defaults={"created_by": user1},
            )

            if created:
                ConversationMember.objects.create(
                    conversation=conversation,
                    user=user1,
                    role=MemberRole.MEMBER,
                )
                ConversationMember.objects.create(
                    conversation=conversation,
                    user=user2,
                    role=MemberRole.MEMBER,
                )

            return conversation, created

    @staticmethod
    def create_group(
        creator: User,
        group_name: str,
        member_ids: list[uuid.UUID | str] | None = None,
    ) -> Conversation:
        """
        Create a new group conversation with creator as OWNER.
        Optionally adds initial members as ordinary MEMBERS.
        """
        cleaned_name = group_name.strip()
        if not cleaned_name:
            raise AppValidationError(
                message="Group name cannot be empty.",
                code="GROUP_NAME_EMPTY",
                fields={"group_name": ["Group name cannot be empty."]},
            )
        if len(cleaned_name) > 150:
            raise AppValidationError(
                message="Group name cannot exceed 150 characters.",
                code="GROUP_NAME_TOO_LONG",
                fields={"group_name": ["Group name cannot exceed 150 characters."]},
            )

        with transaction.atomic():
            conversation = Conversation.objects.create(
                type=ConversationType.GROUP,
                group_name=cleaned_name,
                created_by=creator,
            )

            # Creator is OWNER
            ConversationMember.objects.create(
                conversation=conversation,
                user=creator,
                role=MemberRole.OWNER,
            )

            # Add initial members
            if member_ids:
                distinct_ids = {str(uid) for uid in member_ids if str(uid) != str(creator.id)}
                users = User.objects.filter(id__in=distinct_ids, is_active=True)
                for user in users:
                    if not PrivacyService.can_add_to_group(creator, user):
                        raise PermissionDeniedError(
                            message=f"Cannot add {user.display_name} to this group due to privacy settings or block restrictions.",
                            code="GROUP_INVITE_RESTRICTED",
                        )
                members_to_create = [
                    ConversationMember(
                        conversation=conversation,
                        user=user,
                        role=MemberRole.MEMBER,
                    )
                    for user in users
                ]
                if members_to_create:
                    ConversationMember.objects.bulk_create(members_to_create)

        return conversation

    @staticmethod
    def rename_group(
        conversation_id: uuid.UUID | str,
        requester: User,
        new_name: str,
    ) -> Conversation:
        """
        Rename group. Allowed only for OWNER or ADMIN roles.
        """
        cleaned_name = new_name.strip()
        if not cleaned_name:
            raise AppValidationError(
                message="Group name cannot be empty.",
                code="GROUP_NAME_EMPTY",
                fields={"group_name": ["Group name cannot be empty."]},
            )
        if len(cleaned_name) > 150:
            raise AppValidationError(
                message="Group name cannot exceed 150 characters.",
                code="GROUP_NAME_TOO_LONG",
                fields={"group_name": ["Group name cannot exceed 150 characters."]},
            )

        conversation = ConversationService.get_conversation_for_user(conversation_id, requester)
        if conversation.type != ConversationType.GROUP:
            raise AppValidationError(
                message="Only group conversations can be renamed.",
                code="NOT_A_GROUP_CONVERSATION",
            )

        requester_member = ConversationMember.objects.filter(
            conversation=conversation,
            user=requester,
            left_at__isnull=True,
        ).first()

        if not requester_member or requester_member.role not in [
            MemberRole.OWNER,
            MemberRole.ADMIN,
        ]:
            raise PermissionDeniedError(
                message="Only group owners or admins can rename the group.",
                code="ADMIN_PRIVILEGE_REQUIRED",
            )

        conversation.group_name = cleaned_name
        conversation.save(update_fields=["group_name", "updated_at"])

        RealtimeNotifier.send_to_conversation(
            conversation.id,
            "conversation.renamed",
            {
                "conversation_id": str(conversation.id),
                "group_name": conversation.group_name,
                "renamed_by": {
                    "id": str(requester.id),
                    "username": requester.username,
                    "display_name": requester.display_name,
                },
            },
        )
        return conversation

    @staticmethod
    def add_members(
        conversation_id: uuid.UUID | str,
        requester: User,
        user_ids: list[uuid.UUID | str],
    ) -> list[ConversationMember]:
        """
        Add members to group. Allowed for OWNER or ADMIN.
        """
        conversation = ConversationService.get_conversation_for_user(conversation_id, requester)
        if conversation.type != ConversationType.GROUP:
            raise AppValidationError(
                message="Members can only be added to group conversations.",
                code="NOT_A_GROUP_CONVERSATION",
            )

        requester_member = ConversationMember.objects.filter(
            conversation=conversation,
            user=requester,
            left_at__isnull=True,
        ).first()

        if not requester_member or requester_member.role not in [
            MemberRole.OWNER,
            MemberRole.ADMIN,
        ]:
            raise PermissionDeniedError(
                message="Only group owners or admins can add members.",
                code="ADMIN_PRIVILEGE_REQUIRED",
            )

        distinct_ids = {str(uid) for uid in user_ids}
        users = User.objects.filter(id__in=distinct_ids, is_active=True)
        if not users.exists():
            raise NotFoundError(
                message="No valid users found to add.",
                code="USERS_NOT_FOUND",
            )

        added_members: list[ConversationMember] = []
        with transaction.atomic():
            for user in users:
                if not PrivacyService.can_add_to_group(requester, user):
                    raise PermissionDeniedError(
                        message=f"Cannot add {user.display_name} to this group due to privacy settings or block restrictions.",
                        code="GROUP_INVITE_RESTRICTED",
                    )
                member = ConversationMember.objects.filter(
                    conversation=conversation,
                    user=user,
                ).first()
                if member:
                    if member.left_at is not None:
                        member.left_at = None
                        member.joined_at = timezone.now()
                        member.role = MemberRole.MEMBER
                        member.save(update_fields=["left_at", "joined_at", "role"])
                        added_members.append(member)
                else:
                    new_member = ConversationMember.objects.create(
                        conversation=conversation,
                        user=user,
                        role=MemberRole.MEMBER,
                    )
                    added_members.append(new_member)

        if added_members:
            RealtimeNotifier.send_to_conversation(
                conversation.id,
                "conversation.member_joined",
                {
                    "conversation_id": str(conversation.id),
                    "added_members": [
                        {
                            "id": str(m.id),
                            "user_id": str(m.user.id),
                            "username": m.user.username,
                            "display_name": m.user.display_name,
                            "role": m.role,
                        }
                        for m in added_members
                    ],
                    "added_by": {
                        "id": str(requester.id),
                        "username": requester.username,
                        "display_name": requester.display_name,
                    },
                },
            )

        return added_members

    @staticmethod
    def remove_member(
        conversation_id: uuid.UUID | str,
        requester: User,
        target_user_id: uuid.UUID | str,
    ) -> None:
        """
        Remove a member from the group.
        Owner can remove any member or admin.
        Admin can remove only ordinary members.
        Ordinary members cannot remove anyone.
        """
        conversation = ConversationService.get_conversation_for_user(conversation_id, requester)
        if conversation.type != ConversationType.GROUP:
            raise AppValidationError(
                message="Members can only be removed from group conversations.",
                code="NOT_A_GROUP_CONVERSATION",
            )

        requester_member = ConversationMember.objects.filter(
            conversation=conversation,
            user=requester,
            left_at__isnull=True,
        ).first()

        target_member = (
            ConversationMember.objects.filter(
                conversation=conversation,
                user_id=target_user_id,
                left_at__isnull=True,
            )
            .select_related("user")
            .first()
        )

        if not target_member:
            raise NotFoundError(
                message="Target member not found in this group.",
                code="MEMBER_NOT_FOUND",
            )

        if str(requester.id) == str(target_user_id):
            raise ConflictError(
                message="Cannot remove yourself. Use leave group instead.",
                code="SELF_REMOVAL_NOT_ALLOWED",
            )

        # Role checks (Section 11)
        if requester_member.role == MemberRole.MEMBER:
            raise PermissionDeniedError(
                message="Ordinary members cannot remove other members.",
                code="PERMISSION_DENIED",
            )

        if requester_member.role == MemberRole.ADMIN:
            if target_member.role in [MemberRole.OWNER, MemberRole.ADMIN]:
                raise PermissionDeniedError(
                    message="Admins cannot remove group owners or other admins.",
                    code="ADMIN_PRIVILEGE_REQUIRED",
                )

        target_member.left_at = timezone.now()
        target_member.save(update_fields=["left_at"])

        RealtimeNotifier.send_to_conversation(
            conversation.id,
            "conversation.member_removed",
            {
                "conversation_id": str(conversation.id),
                "removed_user": {
                    "id": str(target_member.user.id),
                    "username": target_member.user.username,
                    "display_name": target_member.user.display_name,
                },
                "removed_by": {
                    "id": str(requester.id),
                    "username": requester.username,
                    "display_name": requester.display_name,
                },
            },
        )

    @staticmethod
    def promote_to_admin(
        conversation_id: uuid.UUID | str,
        requester: User,
        target_user_id: uuid.UUID | str,
    ) -> ConversationMember:
        """Promote a member to admin. Only allowed for OWNER."""
        conversation = ConversationService.get_conversation_for_user(conversation_id, requester)
        requester_member = ConversationMember.objects.filter(
            conversation=conversation,
            user=requester,
            left_at__isnull=True,
        ).first()

        if not requester_member or requester_member.role != MemberRole.OWNER:
            raise PermissionDeniedError(
                message="Only the group owner can promote members to admin.",
                code="OWNER_PRIVILEGE_REQUIRED",
            )

        target_member = (
            ConversationMember.objects.filter(
                conversation=conversation,
                user_id=target_user_id,
                left_at__isnull=True,
            )
            .select_related("user")
            .first()
        )

        if not target_member:
            raise NotFoundError(message="Target member not found.", code="MEMBER_NOT_FOUND")

        if target_member.role == MemberRole.OWNER:
            raise PermissionDeniedError(
                message="The group owner is already the highest authority.",
                code="CANNOT_PROMOTE_OWNER",
            )

        if target_member.role == MemberRole.ADMIN:
            return target_member

        target_member.role = MemberRole.ADMIN
        target_member.save(update_fields=["role"])

        RealtimeNotifier.send_to_conversation(
            conversation.id,
            "conversation.role_updated",
            {
                "conversation_id": str(conversation.id),
                "user_id": str(target_member.user.id),
                "username": target_member.user.username,
                "new_role": MemberRole.ADMIN,
                "updated_by": str(requester.id),
            },
        )
        return target_member

    @staticmethod
    def demote_from_admin(
        conversation_id: uuid.UUID | str,
        requester: User,
        target_user_id: uuid.UUID | str,
    ) -> ConversationMember:
        """Demote an admin to member. Only allowed for OWNER."""
        conversation = ConversationService.get_conversation_for_user(conversation_id, requester)
        requester_member = ConversationMember.objects.filter(
            conversation=conversation,
            user=requester,
            left_at__isnull=True,
        ).first()

        if not requester_member or requester_member.role != MemberRole.OWNER:
            raise PermissionDeniedError(
                message="Only the group owner can demote admins.",
                code="OWNER_PRIVILEGE_REQUIRED",
            )

        target_member = (
            ConversationMember.objects.filter(
                conversation=conversation,
                user_id=target_user_id,
                left_at__isnull=True,
            )
            .select_related("user")
            .first()
        )

        if not target_member:
            raise NotFoundError(message="Target member not found.", code="MEMBER_NOT_FOUND")

        if target_member.role == MemberRole.OWNER:
            raise PermissionDeniedError(
                message="Cannot demote the group owner. Transfer ownership first.",
                code="CANNOT_DEMOTE_OWNER",
            )

        if target_member.role == MemberRole.MEMBER:
            return target_member

        target_member.role = MemberRole.MEMBER
        target_member.save(update_fields=["role"])

        RealtimeNotifier.send_to_conversation(
            conversation.id,
            "conversation.role_updated",
            {
                "conversation_id": str(conversation.id),
                "user_id": str(target_member.user.id),
                "username": target_member.user.username,
                "new_role": MemberRole.MEMBER,
                "updated_by": str(requester.id),
            },
        )
        return target_member

    @staticmethod
    def transfer_ownership(
        conversation_id: uuid.UUID | str,
        requester: User,
        target_user_id: uuid.UUID | str,
    ) -> Conversation:
        """Transfer group ownership to another member. Requester becomes ADMIN."""
        conversation = ConversationService.get_conversation_for_user(conversation_id, requester)
        requester_member = ConversationMember.objects.filter(
            conversation=conversation,
            user=requester,
            left_at__isnull=True,
        ).first()

        if not requester_member or requester_member.role != MemberRole.OWNER:
            raise PermissionDeniedError(
                message="Only the current group owner can transfer ownership.",
                code="OWNER_PRIVILEGE_REQUIRED",
            )

        target_member = (
            ConversationMember.objects.filter(
                conversation=conversation,
                user_id=target_user_id,
                left_at__isnull=True,
            )
            .select_related("user")
            .first()
        )

        if not target_member:
            raise NotFoundError(
                message="Target member not found in this group.", code="MEMBER_NOT_FOUND"
            )

        if str(requester.id) == str(target_user_id):
            raise ConflictError(message="You are already the group owner.", code="ALREADY_OWNER")

        with transaction.atomic():
            requester_member.role = MemberRole.ADMIN
            requester_member.save(update_fields=["role"])

            target_member.role = MemberRole.OWNER
            target_member.save(update_fields=["role"])

            conversation.created_by = target_member.user
            conversation.save(update_fields=["created_by", "updated_at"])

        RealtimeNotifier.send_to_conversation(
            conversation.id,
            "conversation.ownership_transferred",
            {
                "conversation_id": str(conversation.id),
                "previous_owner_id": str(requester.id),
                "new_owner": {
                    "id": str(target_member.user.id),
                    "username": target_member.user.username,
                    "display_name": target_member.user.display_name,
                },
            },
        )
        return conversation

    @staticmethod
    def leave_group(
        conversation_id: uuid.UUID | str,
        requester: User,
    ) -> None:
        """
        Active member leaves group.
        If owner, must transfer ownership first if other active members exist.
        """
        conversation = ConversationService.get_conversation_for_user(conversation_id, requester)
        if conversation.type != ConversationType.GROUP:
            raise AppValidationError(
                message="Only group conversations can be left.",
                code="NOT_A_GROUP_CONVERSATION",
            )

        requester_member = ConversationMember.objects.filter(
            conversation=conversation,
            user=requester,
            left_at__isnull=True,
        ).first()

        if not requester_member:
            raise NotFoundError(message="Active membership not found.", code="MEMBER_NOT_FOUND")

        # If requester is OWNER, verify whether other members exist
        if requester_member.role == MemberRole.OWNER:
            other_members_exist = (
                ConversationMember.objects.filter(
                    conversation=conversation,
                    left_at__isnull=True,
                )
                .exclude(user=requester)
                .exists()
            )

            if other_members_exist:
                raise ConflictError(
                    message="Group owner cannot leave without transferring ownership first. Please transfer ownership before leaving.",
                    code="OWNER_CANNOT_LEAVE_WITHOUT_TRANSFER",
                )

        requester_member.left_at = timezone.now()
        requester_member.save(update_fields=["left_at"])

        RealtimeNotifier.send_to_conversation(
            conversation.id,
            "conversation.member_left",
            {
                "conversation_id": str(conversation.id),
                "user": {
                    "id": str(requester.id),
                    "username": requester.username,
                    "display_name": requester.display_name,
                },
            },
        )

    @staticmethod
    def get_user_conversations(user: User):
        """
        List all active conversations for a given user, ordered by most recent activity.
        """
        return (
            Conversation.objects.filter(
                members__user=user,
                members__left_at__isnull=True,
            )
            .prefetch_related("members__user", "messages__sender")
            .distinct()
            .order_by("-last_message_at", "-created_at")
        )

    @staticmethod
    def get_conversation_for_user(conversation_id: uuid.UUID | str, user: User) -> Conversation:
        """
        Get a specific conversation and verify that user is an active member.
        """
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist as exc:
            raise NotFoundError(
                message="Conversation not found.",
                code="CONVERSATION_NOT_FOUND",
            ) from exc

        is_member = ConversationMember.objects.filter(
            conversation=conversation,
            user=user,
            left_at__isnull=True,
        ).exists()

        if not is_member:
            raise PermissionDeniedError(
                message="You are not an active member of this conversation.",
                code="NOT_A_CONVERSATION_MEMBER",
            )

        return conversation
