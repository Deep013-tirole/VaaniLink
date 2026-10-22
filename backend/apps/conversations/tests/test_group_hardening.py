"""
Group chat role enforcement and lifecycle hardening tests (Phase 10 Hardening).
Verifies:
- Group name validation
- OWNER, ADMIN, MEMBER capability boundaries
- Demoted admin permission revocation
- Owner transfer requirement before leaving
- Section 43 error envelope on permission violations
"""

import pytest

from apps.accounts.models import User
from apps.common.exceptions import ConflictError, PermissionDeniedError
from apps.common.exceptions import ValidationError as AppValidationError
from apps.conversations.models import MemberRole
from apps.conversations.services import ConversationService


@pytest.mark.django_db
class TestGroupHardening:
    def setup_method(self):
        self.owner = User.objects.create_user(
            username="owner_user",
            email="owner@example.com",
            display_name="Owner",
            password="Password123!",
        )
        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            display_name="Admin",
            password="Password123!",
        )
        self.member = User.objects.create_user(
            username="member_user",
            email="member@example.com",
            display_name="Member",
            password="Password123!",
        )
        self.outsider = User.objects.create_user(
            username="outsider_user",
            email="outsider@example.com",
            display_name="Outsider",
            password="Password123!",
        )

        self.group = ConversationService.create_group(
            creator=self.owner,
            group_name="Hardened Test Group",
            member_ids=[self.admin.id, self.member.id],
        )
        # Promote admin_user to ADMIN
        ConversationService.promote_to_admin(self.group.id, self.owner, self.admin.id)

    def test_group_name_validation(self):
        """Creating group with whitespace or exceeding 255 chars is rejected."""
        with pytest.raises(AppValidationError) as exc:
            ConversationService.create_group(creator=self.owner, group_name="   ", member_ids=[])
        assert exc.value.code == "GROUP_NAME_EMPTY"

        with pytest.raises(AppValidationError) as exc2:
            ConversationService.create_group(
                creator=self.owner, group_name="A" * 256, member_ids=[]
            )
        assert exc2.value.code == "GROUP_NAME_TOO_LONG"

    def test_member_cannot_rename_group(self):
        """Ordinary member cannot rename group."""
        with pytest.raises(PermissionDeniedError) as exc:
            ConversationService.rename_group(self.group.id, self.member, "Unauthorized Rename")
        assert exc.value.code == "ADMIN_PRIVILEGE_REQUIRED"

    def test_member_cannot_remove_other_members(self):
        """Ordinary member cannot remove other members."""
        with pytest.raises(PermissionDeniedError) as exc:
            ConversationService.remove_member(self.group.id, self.member, self.admin.id)
        assert exc.value.code == "PERMISSION_DENIED"

    def test_admin_cannot_remove_owner(self):
        """Admin cannot remove the group owner."""
        with pytest.raises(PermissionDeniedError) as exc:
            ConversationService.remove_member(self.group.id, self.admin, self.owner.id)
        assert exc.value.code == "ADMIN_PRIVILEGE_REQUIRED"

    def test_admin_cannot_remove_another_admin(self):
        """Admin cannot remove another admin; only owner can."""
        # Create second admin
        user_admin2 = User.objects.create_user(
            username="admin2",
            email="admin2@example.com",
            display_name="Admin 2",
            password="Password123!",
        )
        ConversationService.add_members(self.group.id, self.owner, [user_admin2.id])
        ConversationService.promote_to_admin(self.group.id, self.owner, user_admin2.id)

        with pytest.raises(PermissionDeniedError) as exc:
            ConversationService.remove_member(self.group.id, self.admin, user_admin2.id)
        assert exc.value.code == "ADMIN_PRIVILEGE_REQUIRED"

    def test_owner_cannot_leave_without_transferring_ownership(self):
        """Owner cannot leave group without designating a successor owner."""
        with pytest.raises(ConflictError) as exc:
            ConversationService.leave_group(self.group.id, self.owner)
        assert exc.value.code == "OWNER_CANNOT_LEAVE_WITHOUT_TRANSFER"

    def test_owner_transfer_and_subsequent_leave(self):
        """Ownership transfer elevates admin to OWNER and demotes former owner to ADMIN, who can then leave."""
        ConversationService.transfer_ownership(self.group.id, self.owner, self.admin.id)

        # Verify new roles
        members = {m.user_id: m.role for m in self.group.members.filter(left_at__isnull=True)}
        assert members[self.admin.id] == MemberRole.OWNER
        assert members[self.owner.id] == MemberRole.ADMIN

        # Former owner (now admin) can now leave
        ConversationService.leave_group(self.group.id, self.owner)
        assert not self.group.members.filter(user=self.owner, left_at__isnull=True).exists()

    def test_demoting_admin_revokes_admin_capabilities(self):
        """Demoted admin becomes ordinary member and cannot add members."""
        ConversationService.demote_from_admin(self.group.id, self.owner, self.admin.id)

        with pytest.raises(PermissionDeniedError) as exc:
            ConversationService.add_members(self.group.id, self.admin, [self.outsider.id])
        assert exc.value.code == "ADMIN_PRIVILEGE_REQUIRED"

    def test_cannot_demote_owner(self):
        """Owner cannot be demoted."""
        with pytest.raises(PermissionDeniedError) as exc:
            ConversationService.demote_from_admin(self.group.id, self.owner, self.owner.id)
        assert exc.value.code == "CANNOT_DEMOTE_OWNER"
