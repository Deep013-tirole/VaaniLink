"""
Privacy and Blocking Domain Service.
Conforms strictly to docs/PRIVACY.md:
- Centralized privacy evaluations for online status, last seen, read receipts, direct messaging, and group invites.
- Directional blocking architecture with shared group isolation.
"""

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError, ValidationError
from apps.conversations.models import Conversation, ConversationType
from apps.privacy.models import PrivacySetting, PrivacyVisibility, UserBlock


class PrivacyService:
    """
    Centralized service for evaluating privacy policies and managing user blocks.
    """

    @staticmethod
    def get_or_create_settings(user: User) -> PrivacySetting:
        """
        Retrieve existing privacy settings for user, or create with defaults.
        """
        settings, _ = PrivacySetting.objects.get_or_create(user=user)
        return settings

    @staticmethod
    def update_settings(user: User, data: dict) -> PrivacySetting:
        """
        Update privacy configuration for user.
        """
        settings = PrivacyService.get_or_create_settings(user)
        allowed_fields = [
            "last_seen_visibility",
            "online_status_visibility",
            "read_receipts_enabled",
            "who_can_message_me",
            "who_can_add_me_to_groups",
        ]
        for field in allowed_fields:
            if field in data:
                setattr(settings, field, data[field])
        settings.save()
        return settings

    @staticmethod
    def is_blocked_by(blocker: User, target: User) -> bool:
        """
        Check if `blocker` has placed an active block on `target`.
        """
        if not blocker or not target or blocker.id == target.id:
            return False
        return UserBlock.objects.filter(blocker=blocker, blocked=target).exists()

    @staticmethod
    def is_blocked_bidirectional(user_a: User, user_b: User) -> bool:
        """
        Check if either user has blocked the other.
        """
        if not user_a or not user_b or user_a.id == user_b.id:
            return False
        return (
            UserBlock.objects.filter(blocker=user_a, blocked=user_b).exists()
            or UserBlock.objects.filter(blocker=user_b, blocked=user_a).exists()
        )

    @staticmethod
    def is_contact(user_a: User, user_b: User) -> bool:
        """
        Check if user_a and user_b share an active direct conversation
        ('People I Chat With').
        """
        if not user_a or not user_b or user_a.id == user_b.id:
            return False
        return (
            Conversation.objects.filter(type=ConversationType.DIRECT)
            .filter(members__user=user_a, members__left_at__isnull=True)
            .filter(members__user=user_b, members__left_at__isnull=True)
            .exists()
        )

    @staticmethod
    def can_view_online_status(viewer: User, target: User) -> bool:
        """
        Determine if `viewer` can view `target`'s online presence.
        docs/PRIVACY.md:
        - Blocked users cannot view online status.
        - EVERYONE: all non-blocked users can view.
        - CONTACTS_ONLY: only mutual direct chat participants can view.
        - NOBODY: no one except self can view.
        """
        if viewer.id == target.id:
            return True

        if PrivacyService.is_blocked_bidirectional(viewer, target):
            return False

        target_settings = PrivacyService.get_or_create_settings(target)
        visibility = target_settings.online_status_visibility

        if visibility == PrivacyVisibility.EVERYONE:
            return True
        if visibility == PrivacyVisibility.CONTACTS_ONLY:
            return PrivacyService.is_contact(viewer, target)
        return False

    @staticmethod
    def can_view_last_seen(viewer: User, target: User) -> bool:
        """
        Determine if `viewer` can view `target`'s last seen timestamp.
        docs/PRIVACY.md:
        - Blocked users cannot view last seen.
        - EVERYONE: all non-blocked users can view.
        - CONTACTS_ONLY: only mutual direct chat participants can view.
        - NOBODY: no one except self can view.
        """
        if viewer.id == target.id:
            return True

        if PrivacyService.is_blocked_bidirectional(viewer, target):
            return False

        target_settings = PrivacyService.get_or_create_settings(target)
        visibility = target_settings.last_seen_visibility

        if visibility == PrivacyVisibility.EVERYONE:
            return True
        if visibility == PrivacyVisibility.CONTACTS_ONLY:
            return PrivacyService.is_contact(viewer, target)
        return False

    @staticmethod
    def should_emit_read_receipt(recipient: User, sender: User) -> bool:
        """
        Determine if recipient's read/seen action should emit a public SEEN receipt to sender.
        docs/PRIVACY.md:
        - If False, recipient sends DELIVERED but suppresses public SEEN.
        - Blocked users do not receive read receipts.
        """
        if recipient.id == sender.id:
            return True

        if PrivacyService.is_blocked_bidirectional(recipient, sender):
            return False

        recipient_settings = PrivacyService.get_or_create_settings(recipient)
        return recipient_settings.read_receipts_enabled

    @staticmethod
    def can_send_direct_message(sender: User, recipient: User) -> bool:
        """
        Determine if `sender` is permitted to send a direct message to `recipient`.
        docs/PRIVACY.md:
        - Blocked users cannot send direct messages.
        - EVERYONE: any user can message.
        - CONTACTS_ONLY: only existing contacts can message.
        - NOBODY: no one can message.
        """
        if sender.id == recipient.id:
            return False

        if PrivacyService.is_blocked_bidirectional(sender, recipient):
            return False

        recipient_settings = PrivacyService.get_or_create_settings(recipient)
        rule = recipient_settings.who_can_message_me

        if rule == PrivacyVisibility.EVERYONE:
            return True
        if rule == PrivacyVisibility.CONTACTS_ONLY:
            return PrivacyService.is_contact(sender, recipient)
        return False

    @staticmethod
    def can_add_to_group(inviter: User, target: User) -> bool:
        """
        Determine if `inviter` is permitted to add `target` to a group conversation.
        docs/PRIVACY.md:
        - Blocked users cannot add to groups.
        - EVERYONE: any user can add.
        - CONTACTS_ONLY: only existing contacts can add.
        - NOBODY: no one can add.
        """
        if inviter.id == target.id:
            return True

        if PrivacyService.is_blocked_bidirectional(inviter, target):
            return False

        target_settings = PrivacyService.get_or_create_settings(target)
        rule = target_settings.who_can_add_me_to_groups

        if rule == PrivacyVisibility.EVERYONE:
            return True
        if rule == PrivacyVisibility.CONTACTS_ONLY:
            return PrivacyService.is_contact(inviter, target)
        return False

    @staticmethod
    def block_user(blocker: User, target_user: User) -> UserBlock:
        """
        Block target_user on behalf of blocker.
        """
        if blocker.id == target_user.id:
            raise ValidationError(
                message="Cannot block yourself.",
                code="CANNOT_BLOCK_SELF",
            )

        block, _ = UserBlock.objects.get_or_create(
            blocker=blocker,
            blocked=target_user,
        )
        return block

    @staticmethod
    def unblock_user(blocker: User, target_user: User) -> bool:
        """
        Unblock target_user on behalf of blocker.
        """
        deleted, _ = UserBlock.objects.filter(
            blocker=blocker,
            blocked=target_user,
        ).delete()
        if not deleted:
            raise NotFoundError(
                message="User is not currently blocked.",
                code="USER_NOT_BLOCKED",
            )
        return True

    @staticmethod
    def get_blocked_users(blocker: User):
        """
        Return queryset of Users blocked by blocker.
        """
        return User.objects.filter(blocked_by_users__blocker=blocker).order_by(
            "-blocked_by_users__created_at"
        )
