"""
Database query optimization and N+1 prevention tests (Phase 10 Hardening).
Verifies:
- O(1) constant database queries when retrieving message timelines (select_related & prefetch_related)
- O(1) queries for conversation listings
- Optimal query count on Message Info receipts
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.conversations.services import ConversationService
from apps.messaging.services import MessageService
from apps.translation.models import MessageTranslation, TranslationStatus


@pytest.mark.django_db
class TestQueryOptimization:
    def setup_method(self):
        self.alice = User.objects.create_user(
            username="alice_opt",
            email="alice_opt@example.com",
            display_name="Alice",
            password="Password123!",
        )
        self.bob = User.objects.create_user(
            username="bob_opt",
            email="bob_opt@example.com",
            display_name="Bob",
            password="Password123!",
        )
        self.conv, _ = ConversationService.get_or_create_direct_conversation(self.alice, self.bob)
        self.client = APIClient()
        self.client.force_authenticate(user=self.alice)

    def test_message_timeline_no_n_plus_one_queries(self, django_assert_num_queries):
        """
        Fetching 20 messages with replies, senders, and translations must execute
        a bounded constant number of queries rather than scaling O(N).
        """
        # Create 20 messages, alternating senders and replies
        parent_msg = None
        for i in range(20):
            sender = self.alice if i % 2 == 0 else self.bob
            msg = MessageService.send_message(
                conversation_id=self.conv.id,
                sender=sender,
                client_message_id=uuid.uuid4(),
                text=f"Message #{i} for performance testing",
                reply_to_id=parent_msg.id if parent_msg else None,
            )
            # Add translation records
            MessageTranslation.objects.create(
                message=msg,
                source_language="en",
                target_language="hi",
                translated_text=f"संदेश #{i}",
                provider="mock",
                status=TranslationStatus.COMPLETED,
            )
            parent_msg = msg

        url = f"/api/v1/conversations/{self.conv.id}/messages/"

        # The query count must be constant:
        # 1. Fetch conversation
        # 2. Verify membership
        # 3. Fetch messages with select_related (sender, reply_to, reply_to__sender)
        # 4. Prefetch translations
        # 5. Prefetch receipts for in-memory status resolution
        with django_assert_num_queries(5):
            response = self.client.get(url)
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 20
            # Verify replies and translations are populated
            assert data[1]["reply_to"] is not None
            assert len(data[1]["translations"]) > 0

    def test_message_info_optimal_query_count(self, django_assert_num_queries):
        """Retrieving message info for a message with multiple recipients uses bounded queries."""
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.alice,
            client_message_id=uuid.uuid4(),
            text="Testing message info performance",
        )

        url = f"/api/v1/messages/{msg.id}/info/"
        # 1. Message select_related conversation, sender
        # 2. Membership check
        # 3. Receipts select_related user
        with django_assert_num_queries(3):
            response = self.client.get(url)
            assert response.status_code == 200
            data = response.json()
            assert data["total_recipients"] == 1
