"""
Custom exception handler conforming to Section 43 Error Format:
{
  "error": {
    "code": "USERNAME_ALREADY_EXISTS",
    "message": "This username is already in use.",
    "fields": {
      "username": [
        "This username is already in use."
      ]
    }
  }
}
"""

from typing import Any

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.common.exceptions import ApplicationError


def _map_drf_code(exc: Exception) -> str:
    """Map standard DRF exceptions to consistent uppercase machine codes."""
    if isinstance(exc, exceptions.ValidationError):
        return "VALIDATION_ERROR"
    if isinstance(exc, exceptions.NotAuthenticated):
        return "NOT_AUTHENTICATED"
    if isinstance(exc, exceptions.AuthenticationFailed):
        return "AUTHENTICATION_FAILED"
    if isinstance(exc, exceptions.PermissionDenied):
        return "PERMISSION_DENIED"
    if isinstance(exc, exceptions.NotFound):
        return "RESOURCE_NOT_FOUND"
    if isinstance(exc, exceptions.MethodNotAllowed):
        return "METHOD_NOT_ALLOWED"
    if isinstance(exc, exceptions.NotAcceptable):
        return "NOT_ACCEPTABLE"
    if isinstance(exc, exceptions.UnsupportedMediaType):
        return "UNSUPPORTED_MEDIA_TYPE"
    if isinstance(exc, exceptions.Throttled):
        return "RATE_LIMIT_EXCEEDED"
    return "BAD_REQUEST"


def _extract_fields_and_message(data: Any) -> tuple[str, dict[str, list[str]]]:
    """
    Extract a high-level summary message and structured field errors from DRF response data.
    """
    fields: dict[str, list[str]] = {}
    message = "An error occurred while processing the request."

    if isinstance(data, dict):
        # Check for non_field_errors or detail
        if "detail" in data:
            detail = data["detail"]
            message = str(detail)
        elif "non_field_errors" in data:
            non_fields = data["non_field_errors"]
            if isinstance(non_fields, list) and non_fields:
                message = str(non_fields[0])
            else:
                message = str(non_fields)

        for key, value in data.items():
            if key in ("detail",):
                continue
            if isinstance(value, list):
                fields[key] = [str(item) for item in value]
            elif isinstance(value, dict):
                sub_msg, sub_fields = _extract_fields_and_message(value)
                fields[key] = [sub_msg]
            else:
                fields[key] = [str(value)]

        # If message was default but we have field errors, pick the first error
        if message == "An error occurred while processing the request." and fields:
            first_key = next(iter(fields))
            if fields[first_key]:
                message = f"{first_key}: {fields[first_key][0]}"

    elif isinstance(data, list):
        if data:
            message = str(data[0])
        fields["non_field_errors"] = [str(item) for item in data]
    else:
        message = str(data)

    return message, fields


def custom_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response | None:
    """
    Top-level DRF exception handler intercepting all API exceptions.
    Wraps both custom ApplicationErrors and standard DRF exceptions into the Section 43 envelope.
    """
    # Handle domain-level ApplicationError directly
    if isinstance(exc, ApplicationError):
        payload = {
            "error": {
                "code": exc.code,
                "message": exc.message,
                "fields": exc.fields,
            }
        }
        return Response(payload, status=exc.status_code)

    # Call REST framework's default exception handler to get standard error response
    response = exception_handler(exc, context)

    if response is not None:
        code = getattr(exc, "default_code", None)
        if not code or code == "error" or code == "invalid":
            code = _map_drf_code(exc)
        else:
            code = str(code).upper()

        message, fields = _extract_fields_and_message(response.data)

        payload = {
            "error": {
                "code": code,
                "message": message,
                "fields": fields,
            }
        }
        response.data = payload
        return response

    # Unhandled server exceptions
    return Response(
        {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "fields": {},
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
