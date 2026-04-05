# AI-ASSISTED: Claude Code | Date: 2026-04-05 | Reviewed: no
"""
In-memory user repository.

Intended to be replaced by a SQLAlchemy-backed repository with a
migration script before any production use.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class UserRepository:
    """Stores and retrieves user records from an in-memory dict.

    Each record has the shape::

        {
            "id": int,
            "username": str,
            "email": str,
            "password_hash": str,   # PBKDF2-HMAC-SHA256 hex digest
            "password_salt": str,   # hex-encoded 32-byte random salt
        }
    """

    def __init__(self) -> None:
        """Initialise an empty store."""
        self._store: dict[int, dict] = {}
        self._next_id: int = 1

    def get_by_username(self, username: str) -> Optional[dict]:
        """Return the user record matching *username*, or None.

        Args:
            username: Case-sensitive username to look up.

        Returns:
            User dict if found, otherwise None.
        """
        for user in self._store.values():
            if user["username"] == username:
                return user
        return None

    def get_by_email(self, email: str) -> Optional[dict]:
        """Return the user record matching *email*, or None.

        Args:
            email: Normalised (lowercase) email address.

        Returns:
            User dict if found, otherwise None.
        """
        for user in self._store.values():
            if user["email"] == email:
                return user
        return None

    def create(self, username: str, email: str, password_hash: str, password_salt: str) -> dict:
        """Persist a new user and return the created record.

        Args:
            username: Validated username.
            email: Normalised email address.
            password_hash: PBKDF2-HMAC-SHA256 hex digest.
            password_salt: Hex-encoded 32-byte random salt.

        Returns:
            The newly created user dict (without secret fields stripped).
        """
        user: dict = {
            "id": self._next_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "password_salt": password_salt,
        }
        self._store[self._next_id] = user
        self._next_id += 1
        logger.info("User created", extra={"user_id": user["id"], "username": username})
        return user

    def clear(self) -> None:
        """Remove all records and reset the ID counter (test helper)."""
        self._store.clear()
        self._next_id = 1


# Module-level singleton - swap for DI-injected instance in production.
user_repo = UserRepository()
