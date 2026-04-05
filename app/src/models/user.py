# AI-ASSISTED: Claude Code | Date: 2026-04-05 | Reviewed: no
"""
User Pydantic models with input validation.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,50}$")
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PASSWORD_MIN_LEN = 8
_PASSWORD_MAX_LEN = 128


class UserRegister(BaseModel):
    """Request model for registering a new user.

    Validates:
    - username: 3-50 alphanumeric/underscore characters
    - email: well-formed email address (max 254 chars per RFC 5321)
    - password: 8-128 chars, requires upper, lower, digit, and special character
    """

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=_PASSWORD_MIN_LEN, max_length=_PASSWORD_MAX_LEN)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """Enforce alphanumeric + underscore, 3-50 chars."""
        stripped = value.strip()
        if not _USERNAME_RE.match(stripped):
            raise ValueError(
                "username must be 3-50 characters and contain only letters, digits, or underscores"
            )
        return stripped

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Normalise and validate email format."""
        normalised = value.strip().lower()
        if not _EMAIL_RE.match(normalised):
            raise ValueError("email must be a valid email address")
        return normalised

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        """Require at least one uppercase, lowercase, digit, and special character."""
        errors = []
        if not any(c.isupper() for c in value):
            errors.append("one uppercase letter")
        if not any(c.islower() for c in value):
            errors.append("one lowercase letter")
        if not any(c.isdigit() for c in value):
            errors.append("one digit")
        if not any(c in r"!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in value):
            errors.append("one special character (!@#$%^&*?)")
        if errors:
            raise ValueError(f"password must contain: {', '.join(errors)}")
        return value


class UserLogin(BaseModel):
    """Request model for authenticating a user.

    Validates:
    - username: non-empty after stripping whitespace
    - password: non-empty
    """

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=_PASSWORD_MAX_LEN)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        """Strip surrounding whitespace from username."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("username must not be blank")
        return stripped


class UserResponse(BaseModel):
    """Public user representation (no password hash exposed)."""

    id: int
    username: str
    email: str


class TokenResponse(BaseModel):
    """Successful authentication response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
