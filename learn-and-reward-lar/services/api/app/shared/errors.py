"""Unified error model (README section 9.1):

    {"error": {"code": "...", "message": "...", "details": {}}}
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # Learning module
    COURSE_NOT_FOUND = "COURSE_NOT_FOUND"
    COURSE_NOT_PUBLISHED = "COURSE_NOT_PUBLISHED"
    ALREADY_ENROLLED = "ALREADY_ENROLLED"
    ENROLLMENT_REQUIRED = "ENROLLMENT_REQUIRED"
    LESSON_NOT_FOUND = "LESSON_NOT_FOUND"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    EXERCISE_INVALID = "EXERCISE_INVALID"
    CERTIFICATE_NOT_READY = "CERTIFICATE_NOT_READY"
    CERTIFICATE_ALREADY_CLAIMED = "CERTIFICATE_ALREADY_CLAIMED"
    CERTIFICATE_NOT_FOUND = "CERTIFICATE_NOT_FOUND"

    # Cross-module adapters
    COIN_TRANSFER_FAILED = "COIN_TRANSFER_FAILED"
    CHAT_UNAVAILABLE = "CHAT_UNAVAILABLE"


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        status_code: int = 400,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_payload(self) -> dict:
        return {"error": {"code": self.code.value, "message": self.message, "details": self.details}}
