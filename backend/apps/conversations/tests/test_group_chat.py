"""
Comprehensive unit and API tests for Group Chat management and role permissions.
Conforms strictly to Section 11 (Group Chat Roles & Permissions) and Section 46.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.conversations.models import ConversationMember, ConversationType, MemberRole
from apps.conversations.services import ConversationService


@pytest.mark.django_db
class TestGroupChat:
    @pytest.fixture
    def setup_users(self):
        owner = User.objects.create_user(
            username="owner_user",
            email="owner@example.com",
            password="Password123!",
            display_name="Owner User",
        )
        admin = User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="Password123!",
            display_name="Admin User",
        )
        member1 = User.objects.create_user(
            username="member_one",
            email="m1@example.com",
            password="Password123!",
            display_name="Member One",
        )
        member2 = User.objects.create_user(
            username="member_two",
            email="m2@example.com",
            password="Password123!",
            display_name="Member Two",
        )
        outsider = User.objects.create_user(
            username="outsider",
            email="out@example.com",
            password="Password123!",
            display_name="Outsider",
        )

        # Create group
        conv = ConversationService.create_group(
            creator=owner,
            group_name="Dev Team Alpha",
            member_ids=[admin.id, member1.id, member2.id],
        )

        # Promote admin_user to ADMIN
        admin_member = ConversationMember.objects.get(conversation=conv, user=admin)
        admin_member.role = MemberRole.ADMIN
        admin_member.save(update_fields=["role"])

        return {
            "owner": owner,
            "admin": admin,
            "member1": member1,
            "member2": member2,
            "outsider": outsider,
            "conv": conv,
        }

    def test_create_group_roles(self, setup_users):
        conv = setup_users["conv"]
        owner = setup_users["owner"]
        member1 = setup_users["member1"]

        assert conv.type == ConversationType.GROUP
        assert conv.group_name == "Dev Team Alpha"

        owner_mem = ConversationMember.objects.get(conversation=conv, user=owner)
        assert owner_mem.role == MemberRole.OWNER

        m1_mem = ConversationMember.objects.get(conversation=conv, user=member1)
        assert m1_mem.role == MemberRole.MEMBER

    def test_rename_group_permissions(self, setup_users):
        client = APIClient()
        conv = setup_users["conv"]

        # 1. Ordinary member cannot rename (403)
        client.force_authenticate(user=setup_users["member1"])
        res_mem = client.patch(
            f"/api/v1/conversations/{conv.id}/rename/",
            data={"group_name": "Hacked Name"},
            format="json",
        )
        assert res_mem.status_code == 403

        # 2. Admin can rename (200)
        client.force_authenticate(user=setup_users["admin"])
        res_admin = client.patch(
            f"/api/v1/conversations/{conv.id}/rename/",
            data={"group_name": "Renamed by Admin"},
            format="json",
        )
        assert res_admin.status_code == 200
        conv.refresh_from_db()
        assert conv.group_name == "Renamed by Admin"

        # 3. Owner can rename (200)
        client.force_authenticate(user=setup_users["owner"])
        res_owner = client.patch(
            f"/api/v1/conversations/{conv.id}/rename/",
            data={"group_name": "Final Team Name"},
            format="json",
        )
        assert res_owner.status_code == 200
        conv.refresh_from_db()
        assert conv.group_name == "Final Team Name"

    def test_add_and_remove_members_permissions(self, setup_users):
        client = APIClient()
        conv = setup_users["conv"]
        outsider = setup_users["outsider"]
        member2 = setup_users["member2"]
        admin = setup_users["admin"]
        owner = setup_users["owner"]

        # 1. Ordinary member cannot add (403)
        client.force_authenticate(user=setup_users["member1"])
        res_add_fail = client.post(
            f"/api/v1/conversations/{conv.id}/members/",
            data={"user_ids": [str(outsider.id)]},
            format="json",
        )
        assert res_add_fail.status_code == 403

        # 2. Admin can add outsider (200)
        client.force_authenticate(user=admin)
        res_add_ok = client.post(
            f"/api/v1/conversations/{conv.id}/members/",
            data={"user_ids": [str(outsider.id)]},
            format="json",
        )
        assert res_add_ok.status_code == 200
        assert ConversationMember.objects.filter(
            conversation=conv, user=outsider, left_at__isnull=True
        ).exists()

        # 3. Admin can remove ordinary member (200)
        res_remove_m2 = client.delete(f"/api/v1/conversations/{conv.id}/members/{member2.id}/")
        assert res_remove_m2.status_code == 200
        assert not ConversationMember.objects.filter(
            conversation=conv, user=member2, left_at__isnull=True
        ).exists()

        # 4. Admin CANNOT remove Owner (403)
        res_remove_owner = client.delete(f"/api/v1/conversations/{conv.id}/members/{owner.id}/")
        assert res_remove_owner.status_code == 403

        # 5. Owner can remove Admin (200)
        client.force_authenticate(user=owner)
        res_remove_admin = client.delete(f"/api/v1/conversations/{conv.id}/members/{admin.id}/")
        assert res_remove_admin.status_code == 200
        assert not ConversationMember.objects.filter(
            conversation=conv, user=admin, left_at__isnull=True
        ).exists()

    def test_promote_and_demote_admin(self, setup_users):
        client = APIClient()
        conv = setup_users["conv"]
        owner = setup_users["owner"]
        admin = setup_users["admin"]
        member1 = setup_users["member1"]

        # 1. Admin cannot promote member (403)
        client.force_authenticate(user=admin)
        res_promote_fail = client.post(
            f"/api/v1/conversations/{conv.id}/promote/",
            data={"user_id": str(member1.id)},
            format="json",
        )
        assert res_promote_fail.status_code == 403

        # 2. Owner can promote member to admin (200)
        client.force_authenticate(user=owner)
        res_promote_ok = client.post(
            f"/api/v1/conversations/{conv.id}/promote/",
            data={"user_id": str(member1.id)},
            format="json",
        )
        assert res_promote_ok.status_code == 200
        m1_mem = ConversationMember.objects.get(conversation=conv, user=member1)
        assert m1_mem.role == MemberRole.ADMIN

        # 3. Owner can demote admin back to member (200)
        res_demote_ok = client.post(
            f"/api/v1/conversations/{conv.id}/demote/",
            data={"user_id": str(member1.id)},
            format="json",
        )
        assert res_demote_ok.status_code == 200
        m1_mem.refresh_from_db()
        assert m1_mem.role == MemberRole.MEMBER

    def test_transfer_ownership(self, setup_users):
        client = APIClient()
        conv = setup_users["conv"]
        owner = setup_users["owner"]
        admin = setup_users["admin"]
        member1 = setup_users["member1"]

        # 1. Non-owner cannot transfer ownership (403)
        client.force_authenticate(user=admin)
        res_transfer_fail = client.post(
            f"/api/v1/conversations/{conv.id}/transfer-ownership/",
            data={"user_id": str(member1.id)},
            format="json",
        )
        assert res_transfer_fail.status_code == 403

        # 2. Owner transfers ownership to admin (200)
        client.force_authenticate(user=owner)
        res_transfer_ok = client.post(
            f"/api/v1/conversations/{conv.id}/transfer-ownership/",
            data={"user_id": str(admin.id)},
            format="json",
        )
        assert res_transfer_ok.status_code == 200

        # Verify roles flipped
        new_owner_mem = ConversationMember.objects.get(conversation=conv, user=admin)
        assert new_owner_mem.role == MemberRole.OWNER

        old_owner_mem = ConversationMember.objects.get(conversation=conv, user=owner)
        assert old_owner_mem.role == MemberRole.ADMIN

    def test_leave_group_rules(self, setup_users):
        client = APIClient()
        conv = setup_users["conv"]
        owner = setup_users["owner"]
        member1 = setup_users["member1"]

        # 1. Ordinary member leaves successfully (200)
        client.force_authenticate(user=member1)
        res_leave_m1 = client.post(f"/api/v1/conversations/{conv.id}/leave/")
        assert res_leave_m1.status_code == 200
        assert not ConversationMember.objects.filter(
            conversation=conv, user=member1, left_at__isnull=True
        ).exists()

        # 2. Owner cannot leave while other active members exist (409 Conflict)
        client.force_authenticate(user=owner)
        res_owner_leave = client.post(f"/api/v1/conversations/{conv.id}/leave/")
        assert res_owner_leave.status_code == 409
        assert "transfer ownership" in res_owner_leave.json()["error"]["message"].lower()

        # 3. If owner transfers ownership, previous owner (now admin) can leave (200)
        client.post(
            f"/api/v1/conversations/{conv.id}/transfer-ownership/",
            data={"user_id": str(setup_users["admin"].id)},
            format="json",
        )
        res_old_owner_leaves = client.post(f"/api/v1/conversations/{conv.id}/leave/")
        assert res_old_owner_leaves.status_code == 200
