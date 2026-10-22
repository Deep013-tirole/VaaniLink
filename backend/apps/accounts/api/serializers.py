"""
Serializers for accounts and authentication.
Conforms strictly to Section 43 error code and field contracts.
"""

import re

from django.contrib.auth import authenticate
from rest_framework import serializers

from apps.accounts.models import User
from apps.common.exceptions import AuthenticationError, ConflictError
from apps.common.exceptions import ValidationError as AppValidationError
from apps.languages.api.serializers import LanguageSerializer
from apps.languages.models import Language


class UserSerializer(serializers.ModelSerializer):
    """
    Detailed public user representation.
    Decouples interface language from preferred chat language.
    Does NOT expose password or private token data.
    """

    interface_language = LanguageSerializer(read_only=True)
    preferred_chat_language = LanguageSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "display_name",
            "email",
            "interface_language",
            "preferred_chat_language",
            "is_active",
            "last_seen_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserSearchSerializer(serializers.ModelSerializer):
    """
    Sanitized user representation for search results conforming to Section 38:
    Must not expose email, private language settings, last seen, or private metadata.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "display_name",
        ]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    """
    Serializer for user registration.
    """

    username = serializers.CharField(max_length=50, min_length=3)
    email = serializers.EmailField(max_length=254)
    display_name = serializers.CharField(max_length=100, min_length=1)
    password = serializers.CharField(write_only=True, min_length=8)
    interface_language = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Language.objects.all(),
        required=False,
        allow_null=True,
    )
    preferred_chat_language = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Language.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate_username(self, value: str) -> str:
        cleaned = value.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_]+$", cleaned):
            raise AppValidationError(
                message="Username may only contain letters, numbers, and underscores.",
                code="INVALID_USERNAME_FORMAT",
                fields={
                    "username": [
                        "Username may only contain alphanumeric characters and underscores."
                    ]
                },
            )

        if User.objects.filter(username=cleaned).exists():
            raise ConflictError(
                message="This username is already in use.",
                code="USERNAME_ALREADY_EXISTS",
                fields={"username": ["This username is already in use."]},
            )
        return cleaned

    def validate_email(self, value: str) -> str:
        cleaned = value.strip().lower()
        if User.objects.filter(email=cleaned).exists():
            raise ConflictError(
                message="An account with this email address already exists.",
                code="EMAIL_ALREADY_EXISTS",
                fields={"email": ["An account with this email address already exists."]},
            )
        return cleaned

    def validate_display_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise AppValidationError(
                message="Display name cannot be blank.",
                code="DISPLAY_NAME_REQUIRED",
                fields={"display_name": ["Display name cannot be blank."]},
            )
        return cleaned

    def create(self, validated_data: dict) -> User:
        # Default interface and chat languages if omitted
        if not validated_data.get("interface_language"):
            validated_data["interface_language"] = Language.objects.filter(code="en").first()
        if not validated_data.get("preferred_chat_language"):
            validated_data["preferred_chat_language"] = Language.objects.filter(code="en").first()

        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for username/password authentication.
    Supports login via username or email.
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        identifier = attrs.get("username", "").strip().lower()
        password = attrs.get("password", "")

        # Try authenticating directly by username
        user = authenticate(username=identifier, password=password)

        # If not authenticated, check if identifier is an email address
        if not user and "@" in identifier:
            user_obj = User.objects.filter(email=identifier).first()
            if user_obj:
                user = authenticate(username=user_obj.username, password=password)

        if not user:
            raise AuthenticationError(
                message="Invalid username or password.",
                code="INVALID_CREDENTIALS",
            )

        if not user.is_active:
            raise AuthenticationError(
                message="This user account is inactive.",
                code="ACCOUNT_INACTIVE",
            )

        attrs["user"] = user
        return attrs


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile settings (PATCH /api/v1/users/me/).
    """

    interface_language = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Language.objects.all(),
        required=False,
    )
    preferred_chat_language = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Language.objects.all(),
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "display_name",
            "interface_language",
            "preferred_chat_language",
        ]

    def validate_display_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise AppValidationError(
                message="Display name cannot be blank.",
                code="DISPLAY_NAME_REQUIRED",
                fields={"display_name": ["Display name cannot be blank."]},
            )
        return cleaned
