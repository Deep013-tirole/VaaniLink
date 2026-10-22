"""
Custom application exceptions with machine-readable error codes.
"""

from typing import Any


class ApplicationError(Exception):
    """
    Base class for application-level errors conforming to Section 43 error contract.
    """

    default_code = "INTERNAL_SERVER_ERROR"
    default_message = "An unexpected error occurred."
    default_status_code = 500

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
        fields: dict[str, list[Any]] | None = None,
    ):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.status_code = status_code or self.default_status_code
        self.fields = fields or {}
        super().__init__(self.message)


class ValidationError(ApplicationError):
    default_code = "VALIDATION_ERROR"
    default_message = "The submitted data is invalid."
    default_status_code = 400


class AuthenticationError(ApplicationError):
    default_code = "AUTHENTICATION_FAILED"
    default_message = "Authentication credentials were not provided or are invalid."
    default_status_code = 401


class PermissionDeniedError(ApplicationError):
    default_code = "PERMISSION_DENIED"
    default_message = "You do not have permission to perform this action."
    default_status_code = 403


class NotFoundError(ApplicationError):
    default_code = "RESOURCE_NOT_FOUND"
    default_message = "The requested resource was not found."
    default_status_code = 404


class ConflictError(ApplicationError):
    default_code = "RESOURCE_CONFLICT"
    default_message = "A conflict occurred with an existing resource."
    default_status_code = 409


# Alias for convenience
AppError = ApplicationError
