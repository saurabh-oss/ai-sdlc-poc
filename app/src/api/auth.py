# AI-ASSISTED: Claude Code | Date: 2026-04-05 | Reviewed: no
"""
Auth API router: /api/v1/auth endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from models.user import TokenResponse, UserLogin, UserRegister, UserResponse
from repository.user_repository import user_repo
from service.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Module-level service instance using the shared repo singleton.
_auth_service = AuthService(user_repo)


def get_auth_service() -> AuthService:
    """Return the module-level AuthService (override in tests)."""
    return _auth_service


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    payload: UserRegister,
    svc: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Register a new user account.

    Args:
        payload: Validated registration data (username, email, password).
        svc: Injected AuthService instance.

    Returns:
        The newly created user (no password fields).

    Raises:
        HTTPException: 409 if username or email is already taken.
        HTTPException: 422 if input validation fails (handled by FastAPI/Pydantic).
    """
    try:
        return svc.register(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "CONFLICT", "message": str(exc)}},
        ) from exc


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive a bearer token",
)
def login(
    payload: UserLogin,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate a user and return a bearer token.

    Args:
        payload: Login credentials (username, password).
        svc: Injected AuthService instance.

    Returns:
        Bearer token and basic user info.

    Raises:
        HTTPException: 401 if credentials are invalid.
        HTTPException: 422 if input validation fails (handled by FastAPI/Pydantic).
    """
    try:
        return svc.login(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": str(exc)}},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
