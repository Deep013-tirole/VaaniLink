"""
Authentication and User Account API views.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.api.serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSearchSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.accounts.models import User
from apps.common.exceptions import AuthenticationError


class RegisterView(APIView):
    """
    Register a new user account.
    POST /api/v1/auth/register/
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT access and refresh tokens
        refresh = RefreshToken.for_user(user)

        response_data = {
            "user": UserSerializer(user).data,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Authenticate user and issue JWT tokens.
    POST /api/v1/auth/login/
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)

        response_data = {
            "user": UserSerializer(user).data,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }
        return Response(response_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    Revoke/blacklist refresh token on logout.
    POST /api/v1/auth/logout/
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except AttributeError:
                # Blacklist app might not be installed if using token rotation only
                pass
            except TokenError:
                pass

        return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)


class MeView(APIView):
    """
    Retrieve current authenticated user profile.
    GET /api/v1/auth/me/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response({"user": serializer.data}, status=status.HTTP_200_OK)


class UserMeUpdateView(APIView):
    """
    Update current user profile settings (display name, interface & chat languages).
    PATCH /api/v1/users/me/
    """

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({"user": UserSerializer(user).data}, status=status.HTTP_200_OK)


class UserSearchView(APIView):
    """
    Search users by username or display name conforming to Section 38.
    GET /api/v1/users/search/?q=<query>
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response([], status=status.HTTP_200_OK)

        from django.db.models import Q

        users = (
            User.objects.filter(is_active=True)
            .exclude(id=request.user.id)
            .filter(Q(username__icontains=query) | Q(display_name__icontains=query))[:20]
        )
        serializer = UserSearchSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Wrap SimpleJWT TokenRefreshView to format tokens consistently.
    POST /api/v1/auth/refresh/
    """

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, InvalidToken) as exc:
            raise AuthenticationError(
                message="Refresh token is invalid or expired.",
                code="TOKEN_INVALID_OR_EXPIRED",
            ) from exc

        return Response(
            {
                "tokens": {
                    "access": serializer.validated_data.get("access"),
                    "refresh": serializer.validated_data.get(
                        "refresh", request.data.get("refresh")
                    ),
                }
            },
            status=status.HTTP_200_OK,
        )
