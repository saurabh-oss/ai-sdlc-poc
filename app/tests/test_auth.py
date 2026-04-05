# AI-ASSISTED: Claude Code | Date: 2026-04-05 | Reviewed: no
"""
Unit tests for the auth module.

Covers input validation (422), happy paths, conflict detection (409),
and authentication failures (401).
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.auth import get_auth_service, router
from main import app
from repository.user_repository import UserRepository
from service.auth_service import AuthService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_test_repo = UserRepository()
_test_service = AuthService(_test_repo)


@pytest.fixture(autouse=True)
def _reset_auth_state():
    """Isolate each test by clearing the in-memory stores."""
    _test_repo.clear()
    _test_service.clear()
    app.dependency_overrides[get_auth_service] = lambda: _test_service
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


_VALID_PAYLOAD = {
    "username": "alice_01",
    "email": "alice@example.com",
    "password": "Secure#99",
}


def _register(client: TestClient, payload: dict | None = None) -> dict:
    payload = payload or _VALID_PAYLOAD
    return client.post("/api/v1/auth/register", json=payload)


# ---------------------------------------------------------------------------
# Registration - happy path
# ---------------------------------------------------------------------------


class TestRegisterHappyPath:
    def test_returns_201(self, client: TestClient) -> None:
        resp = _register(client)
        assert resp.status_code == 201

    def test_returns_user_without_password(self, client: TestClient) -> None:
        data = _register(client).json()
        assert data["username"] == "alice_01"
        assert data["email"] == "alice@example.com"
        assert "password" not in data
        assert "password_hash" not in data
        assert "id" in data

    def test_email_is_lowercased(self, client: TestClient) -> None:
        payload = {**_VALID_PAYLOAD, "email": "Alice@EXAMPLE.COM"}
        data = _register(client, payload).json()
        assert data["email"] == "alice@example.com"


# ---------------------------------------------------------------------------
# Registration - input validation (422)
# ---------------------------------------------------------------------------


class TestRegisterValidation:
    @pytest.mark.parametrize(
        "username",
        [
            "ab",           # too short
            "a" * 51,       # too long
            "bad name",     # contains space
            "bad-name",     # contains hyphen
            "",             # empty
            "   ",          # blank after strip
        ],
    )
    def test_invalid_username_returns_422(self, client: TestClient, username: str) -> None:
        payload = {**_VALID_PAYLOAD, "username": username}
        assert _register(client, payload).status_code == 422

    @pytest.mark.parametrize(
        "email",
        [
            "notanemail",
            "missing@",
            "@nodomain.com",
            "no-at-sign",
            "spaces @example.com",
            "",
        ],
    )
    def test_invalid_email_returns_422(self, client: TestClient, email: str) -> None:
        payload = {**_VALID_PAYLOAD, "email": email}
        assert _register(client, payload).status_code == 422

    @pytest.mark.parametrize(
        "password",
        [
            "short1A!",     # 8 chars - valid (boundary check)
            "short1A",      # missing special char
            "nouppercase1!",# missing uppercase
            "NOLOWER1!",    # missing lowercase
            "NoDigits!!",   # missing digit
            "Short1!",      # too short (7 chars)
            "",             # empty
        ],
    )
    def test_weak_password_returns_422(self, client: TestClient, password: str) -> None:
        payload = {**_VALID_PAYLOAD, "password": password}
        resp = _register(client, payload)
        # "short1A!" is actually valid - 8 chars with upper, lower, digit, special
        if password == "short1A!":
            assert resp.status_code == 201
        else:
            assert resp.status_code == 422

    def test_missing_fields_returns_422(self, client: TestClient) -> None:
        assert client.post("/api/v1/auth/register", json={}).status_code == 422

    def test_password_max_length_enforced(self, client: TestClient) -> None:
        payload = {**_VALID_PAYLOAD, "password": "A1!" + "x" * 126}  # 129 chars
        assert _register(client, payload).status_code == 422


# ---------------------------------------------------------------------------
# Registration - conflict (409)
# ---------------------------------------------------------------------------


class TestRegisterConflict:
    def test_duplicate_username_returns_409(self, client: TestClient) -> None:
        _register(client)
        resp = _register(client, {**_VALID_PAYLOAD, "email": "other@example.com"})
        assert resp.status_code == 409

    def test_duplicate_email_returns_409(self, client: TestClient) -> None:
        _register(client)
        resp = _register(client, {**_VALID_PAYLOAD, "username": "other_user"})
        assert resp.status_code == 409

    def test_conflict_response_has_error_structure(self, client: TestClient) -> None:
        _register(client)
        data = _register(client).json()
        assert "detail" in data
        assert "error" in data["detail"]


# ---------------------------------------------------------------------------
# Login - happy path
# ---------------------------------------------------------------------------


class TestLoginHappyPath:
    def test_returns_200_with_token(self, client: TestClient) -> None:
        _register(client)
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "alice_01", "password": "Secure#99"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "alice_01"

    def test_token_is_nonempty_string(self, client: TestClient) -> None:
        _register(client)
        data = client.post(
            "/api/v1/auth/login",
            json={"username": "alice_01", "password": "Secure#99"},
        ).json()
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0


# ---------------------------------------------------------------------------
# Login - invalid credentials (401)
# ---------------------------------------------------------------------------


class TestLoginFailures:
    def test_wrong_password_returns_401(self, client: TestClient) -> None:
        _register(client)
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "alice_01", "password": "WrongPass1!"},
        )
        assert resp.status_code == 401

    def test_unknown_username_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "ghost", "password": "Secure#99"},
        )
        assert resp.status_code == 401

    def test_error_message_does_not_reveal_which_field_is_wrong(
        self, client: TestClient
    ) -> None:
        _register(client)
        # Wrong password
        msg_bad_pw = client.post(
            "/api/v1/auth/login",
            json={"username": "alice_01", "password": "BadPass1!"},
        ).json()["detail"]["error"]["message"]
        # Unknown user
        msg_bad_user = client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "Secure#99"},
        ).json()["detail"]["error"]["message"]
        assert msg_bad_pw == msg_bad_user

    def test_blank_credentials_return_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "", "password": "Secure#99"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AuthService unit tests (no HTTP layer)
# ---------------------------------------------------------------------------


class TestAuthServiceDirect:
    def test_register_and_login_round_trip(self) -> None:
        from models.user import UserRegister

        svc = AuthService(UserRepository())
        payload = UserRegister(
            username="bob_test",
            email="bob@example.com",
            password="BobPass1!",
        )
        user = svc.register(payload)
        assert user.username == "bob_test"

        token_resp = svc.login("bob_test", "BobPass1!")
        assert token_resp.access_token
        assert svc.get_user_id_for_token(token_resp.access_token) == user.id

    def test_revoke_token(self) -> None:
        from models.user import UserRegister

        svc = AuthService(UserRepository())
        svc.register(
            UserRegister(username="carol", email="carol@x.com", password="CarolPw1!")
        )
        token_resp = svc.login("carol", "CarolPw1!")
        token = token_resp.access_token
        svc.revoke_token(token)
        assert svc.get_user_id_for_token(token) is None
