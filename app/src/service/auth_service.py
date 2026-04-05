# AI-ASSISTED: Claude Code | Date: 2026-04-05 | Reviewed: no
"""
Authentication service: password hashing and token management.

Uses only the Python standard library so no new runtime dependencies
are required (hashlib.pbkdf2_hmac for hashing, secrets for tokens).
"""

import hashlib
import hmac
import logging
import os
import secrets
from typing import Optional

from models.user import TokenResponse, UserRegister, UserResponse
from repository.user_repository import UserRepository

logger = logging.getLogger(__name__)

_PBKDF2_ITERATIONS = 390_000  # OWASP 2023 recommendation for PBKDF2-HMAC-SHA256
_SALT_BYTES = 32
_TOKEN_BYTES = 32


def _hash_password(password: str, salt_hex: str) -> str:
    """Derive a PBKDF2-HMAC-SHA256 hex digest from *password* and *salt_hex*.

    Args:
        password: Plaintext password (UTF-8 encoded internally).
        salt_hex: Hex-encoded 32-byte salt.

    Returns:
        Hex-encoded derived key.
    """
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return digest.hex()


def _verify_password(password: str, salt_hex: str, stored_hash_hex: str) -> bool:
    """Constant-time password verification.

    Args:
        password: Plaintext password to verify.
        salt_hex: Hex salt stored alongside the hash.
        stored_hash_hex: Previously derived key to compare against.

    Returns:
        True if the password matches, False otherwise.
    """
    candidate = _hash_password(password, salt_hex)
    return hmac.compare_digest(candidate, stored_hash_hex)


class AuthService:
    """Handles user registration, login, and token lifecycle.

    Args:
        repo: User repository instance (injected for testability).
    """

    def __init__(self, repo: UserRepository) -> None:
        """Initialise the service with the provided repository."""
        self._repo = repo
        # Maps opaque token -> user_id (replace with Redis / DB in production)
        self._tokens: dict[str, int] = {}

    def register(self, payload: UserRegister) -> UserResponse:
        """Register a new user after checking for duplicates.

        Args:
            payload: Validated registration data.

        Returns:
            The public user representation.

        Raises:
            ValueError: If the username or email is already taken.
        """
        if self._repo.get_by_username(payload.username):
            raise ValueError("username is already taken")
        if self._repo.get_by_email(payload.email):
            raise ValueError("email address is already registered")

        salt_hex = os.urandom(_SALT_BYTES).hex()
        pw_hash = _hash_password(payload.password, salt_hex)

        user = self._repo.create(
            username=payload.username,
            email=payload.email,
            password_hash=pw_hash,
            password_salt=salt_hex,
        )
        return UserResponse(id=user["id"], username=user["username"], email=user["email"])

    def login(self, username: str, password: str) -> TokenResponse:
        """Authenticate a user and issue an opaque bearer token.

        Args:
            username: The username to authenticate.
            password: The plaintext password to verify.

        Returns:
            A token response containing the bearer token and user info.

        Raises:
            ValueError: If credentials are invalid (message is intentionally vague).
        """
        user = self._repo.get_by_username(username)
        # Deliberate constant-time path: always attempt verification even when
        # the user is not found to mitigate timing-based username enumeration.
        _dummy_salt = "0" * 64
        _dummy_hash = "0" * 64
        salt = user["password_salt"] if user else _dummy_salt
        stored = user["password_hash"] if user else _dummy_hash

        if not _verify_password(password, salt, stored) or user is None:
            logger.warning("Failed login attempt", extra={"username": username})
            raise ValueError("invalid username or password")

        token = secrets.token_urlsafe(_TOKEN_BYTES)
        self._tokens[token] = user["id"]
        logger.info("User logged in", extra={"user_id": user["id"]})
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse(id=user["id"], username=user["username"], email=user["email"]),
        )

    def get_user_id_for_token(self, token: str) -> Optional[int]:
        """Look up the user ID associated with *token*.

        Args:
            token: Opaque bearer token.

        Returns:
            User ID if the token is valid, None otherwise.
        """
        return self._tokens.get(token)

    def revoke_token(self, token: str) -> None:
        """Invalidate *token* (logout).

        Args:
            token: Bearer token to revoke.
        """
        self._tokens.pop(token, None)

    def clear(self) -> None:
        """Reset service state (test helper)."""
        self._tokens.clear()
