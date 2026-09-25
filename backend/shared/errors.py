"""Typed HTTP errors for the API and worker.

Internal exception details are logged by the caller but NEVER serialized into
API responses (no AWS exceptions, credentials, ExternalIds, or config leaks).
"""
from __future__ import annotations


class ApiError(Exception):
    """An error that maps to an HTTP status code."""

    def __init__(self, status_code: int, message: str, code: str = "ERROR") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code

    def to_dict(self) -> dict:
        return {"error": self.code, "message": self.message}


def bad_request(message: str = "Invalid request", code: str = "BAD_REQUEST") -> ApiError:
    return ApiError(400, message, code)


def unauthorized(message: str = "Unauthorized", code: str = "UNAUTHORIZED") -> ApiError:
    return ApiError(401, message, code)


def forbidden(message: str = "Forbidden", code: str = "FORBIDDEN") -> ApiError:
    return ApiError(403, message, code)


def not_found(message: str = "Not found", code: str = "NOT_FOUND") -> ApiError:
    return ApiError(404, message, code)


def conflict(message: str = "Conflict", code: str = "CONFLICT") -> ApiError:
    return ApiError(409, message, code)


def server_error(message: str = "Internal server error", code: str = "INTERNAL_ERROR") -> ApiError:
    return ApiError(500, message, code)
