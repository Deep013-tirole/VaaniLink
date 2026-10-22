"""
Tests for custom exception handler conforming to Section 43 structured error contract.
"""

from rest_framework import exceptions, serializers
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.common.api.exception_handler import custom_exception_handler
from apps.common.exceptions import ValidationError as AppValidationError


class DummySerializer(serializers.Serializer):
    username = serializers.CharField(max_length=10)


class TestExceptionHandler:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.request = Request(self.factory.get("/"))
        self.context = {"request": self.request, "view": None}

    def test_drf_validation_error_formatting(self):
        serializer = DummySerializer(data={"username": "toolongusername123"})
        assert not serializer.is_valid()
        exc = exceptions.ValidationError(serializer.errors)

        response = custom_exception_handler(exc, self.context)

        assert response is not None
        assert response.status_code == 400
        assert "error" in response.data
        error = response.data["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert "username" in error["fields"]
        assert isinstance(error["fields"]["username"], list)

    def test_not_authenticated_formatting(self):
        exc = exceptions.NotAuthenticated("Authentication credentials were not provided.")
        response = custom_exception_handler(exc, self.context)

        assert response is not None
        assert response.status_code == 401
        assert response.data["error"]["code"] == "NOT_AUTHENTICATED"
        assert "credentials" in response.data["error"]["message"].lower()

    def test_application_error_custom_code(self):
        exc = AppValidationError(
            message="This username is already in use.",
            code="USERNAME_ALREADY_EXISTS",
            fields={"username": ["This username is already in use."]},
        )
        response = custom_exception_handler(exc, self.context)

        assert response is not None
        assert response.status_code == 400
        assert response.data == {
            "error": {
                "code": "USERNAME_ALREADY_EXISTS",
                "message": "This username is already in use.",
                "fields": {"username": ["This username is already in use."]},
            }
        }
