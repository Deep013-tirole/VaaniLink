"""
Tests for Custom User model and UserManager.
"""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from apps.accounts.models import User
from apps.languages.models import Language


@pytest.mark.django_db
class TestUserModel:
    def setup_method(self):
        self.hi = Language.objects.create(
            code="hi",
            name="Hindi",
            native_name="हिन्दी",
            script_code="Deva",
            sort_order=2,
        )
        self.en = Language.objects.create(
            code="en",
            name="English",
            native_name="English",
            script_code="Latn",
            sort_order=1,
        )

    def test_create_user_with_languages(self):
        user = User.objects.create_user(
            username="deepak",
            email="deepak@example.com",
            password="securePassword123!",
            display_name="Deepak Tirole",
            interface_language=self.en,
            preferred_chat_language=self.hi,
        )

        assert isinstance(user.id, uuid.UUID)
        assert user.username == "deepak"
        assert user.email == "deepak@example.com"
        assert user.display_name == "Deepak Tirole"
        assert user.interface_language.code == "en"
        assert user.preferred_chat_language.code == "hi"
        assert user.check_password("securePassword123!")
        assert not user.check_password("wrongPassword")
        assert user.is_active
        assert not user.is_staff

    def test_username_normalization(self):
        user = User.objects.create_user(
            username="  Deepak_Tirole  ",
            email="Deepak@Example.COM",
            password="securePassword123!",
            display_name="Deepak Tirole",
        )
        assert user.username == "deepak_tirole"
        assert user.email == "deepak@example.com"

    def test_unique_username_constraint(self):
        User.objects.create_user(
            username="deepak",
            email="deepak1@example.com",
            password="securePassword123!",
            display_name="Deepak One",
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username="deepak",
                email="deepak2@example.com",
                password="securePassword123!",
                display_name="Deepak Two",
            )

    def test_unique_email_constraint(self):
        User.objects.create_user(
            username="deepak1",
            email="deepak@example.com",
            password="securePassword123!",
            display_name="Deepak One",
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username="deepak2",
                email="deepak@example.com",
                password="securePassword123!",
                display_name="Deepak Two",
            )

    def test_create_user_missing_required_fields(self):
        with pytest.raises(ValidationError):
            User.objects.create_user(
                username="",
                email="test@example.com",
                password="password",
            )
        with pytest.raises(ValidationError):
            User.objects.create_user(
                username="test",
                email="",
                password="password",
            )
