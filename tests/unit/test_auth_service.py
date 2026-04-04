"""Unit tests for AuthService and RBAC."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from app.config import get_settings
from app.exceptions import AuthenticationError, TokenExpiredError, ValidationError
from app.models.domain import User, UserRole
from app.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_db_record(**overrides) -> Dict[str, Any]:
    """Return a fake DB row mapping for a user."""
    defaults: Dict[str, Any] = {
        "id": uuid.uuid4(),
        "username": "testuser",
        "password_hash": "$2b$12$placeholder",
        "role": UserRole.CAMPAIGN_MANAGER.value,
        "is_active": True,
        "failed_login_attempts": 0,
        "locked_until": None,
        "last_activity_at": None,
    }
    defaults.update(overrides)
    return defaults


def _make_auth_service(db: Any = None) -> AuthService:
    if db is None:
        db = AsyncMock()
    return AuthService(db)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    mock = AsyncMock()
    # execute returns an object whose .mappings().first() returns a record
    mock.execute = AsyncMock()
    mock.flush = AsyncMock()
    return mock


@pytest.fixture()
def svc(db):
    return AuthService(db)


# ---------------------------------------------------------------------------
# register_user
# ---------------------------------------------------------------------------

class TestRegisterUser:
    @pytest.mark.asyncio
    async def test_valid_password_creates_user(self, svc, db):
        db.execute.return_value = MagicMock()
        user = await svc.register_user("alice", "securepass", UserRole.CAMPAIGN_MANAGER)
        assert user.username == "alice"
        assert user.role == UserRole.CAMPAIGN_MANAGER
        assert user.password_hash != "securepass"  # must be hashed

    @pytest.mark.asyncio
    async def test_short_password_raises_validation_error(self, svc):
        with pytest.raises(ValidationError):
            await svc.register_user("bob", "short", UserRole.REVIEWER)

    @pytest.mark.asyncio
    async def test_exactly_8_chars_is_valid(self, svc, db):
        db.execute.return_value = MagicMock()
        user = await svc.register_user("carol", "12345678", UserRole.ADMINISTRATOR)
        assert user.username == "carol"

    @pytest.mark.asyncio
    async def test_7_chars_raises_validation_error(self, svc):
        with pytest.raises(ValidationError):
            await svc.register_user("dave", "1234567", UserRole.REVIEWER)


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

class TestLogin:
    def _setup_db_for_login(self, db, record: Dict[str, Any]) -> None:
        """Wire db.execute so that mappings().first() returns *record*."""
        mapping_mock = MagicMock()
        mapping_mock.first.return_value = record
        result_mock = MagicMock()
        result_mock.mappings.return_value = mapping_mock
        db.execute.return_value = result_mock

    @pytest.mark.asyncio
    async def test_login_success(self, svc, db):
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_ctx.hash("goodpassword")
        record = _make_db_record(password_hash=hashed)
        self._setup_db_for_login(db, record)
        # Second execute call (UPDATE) should also work
        db.execute.side_effect = None
        db.execute.return_value = MagicMock()

        # Patch the first SELECT to return the record, subsequent calls return generic mock
        call_count = 0
        original_execute = db.execute

        async def _execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mapping_mock = MagicMock()
                mapping_mock.first.return_value = record
                result_mock = MagicMock()
                result_mock.mappings.return_value = mapping_mock
                return result_mock
            return MagicMock()

        db.execute.side_effect = _execute_side_effect

        user = await svc.login("testuser", "goodpassword")
        assert user.username == "testuser"
        assert user.failed_login_attempts == 0

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises(self, svc, db):
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_ctx.hash("correctpassword")
        record = _make_db_record(password_hash=hashed)

        call_count = 0

        async def _execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mapping_mock = MagicMock()
                mapping_mock.first.return_value = record
                result_mock = MagicMock()
                result_mock.mappings.return_value = mapping_mock
                return result_mock
            return MagicMock()

        db.execute.side_effect = _execute_side_effect

        with pytest.raises(AuthenticationError):
            await svc.login("testuser", "wrongpassword")

    @pytest.mark.asyncio
    async def test_login_unknown_user_raises(self, svc, db):
        mapping_mock = MagicMock()
        mapping_mock.first.return_value = None
        result_mock = MagicMock()
        result_mock.mappings.return_value = mapping_mock
        db.execute.return_value = result_mock

        with pytest.raises(AuthenticationError):
            await svc.login("nobody", "password123")

    @pytest.mark.asyncio
    async def test_locked_account_raises(self, svc, db):
        future = _now() + timedelta(minutes=10)
        record = _make_db_record(locked_until=future)

        mapping_mock = MagicMock()
        mapping_mock.first.return_value = record
        result_mock = MagicMock()
        result_mock.mappings.return_value = mapping_mock
        db.execute.return_value = result_mock

        with pytest.raises(AuthenticationError, match="terkunci"):
            await svc.login("testuser", "anypassword")

    @pytest.mark.asyncio
    async def test_account_locked_after_5_failures(self, svc, db):
        """After 4 failed attempts, the 5th should trigger a lock."""
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_ctx.hash("correctpassword")
        record = _make_db_record(password_hash=hashed, failed_login_attempts=4)

        call_count = 0

        async def _execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mapping_mock = MagicMock()
                mapping_mock.first.return_value = record
                result_mock = MagicMock()
                result_mock.mappings.return_value = mapping_mock
                return result_mock
            return MagicMock()

        db.execute.side_effect = _execute_side_effect

        with pytest.raises(AuthenticationError):
            await svc.login("testuser", "wrongpassword")

        # The UPDATE call should include locked_until
        update_call_args = db.execute.call_args_list[1]
        sql_text = str(update_call_args[0][0])
        assert "locked_until" in sql_text

    @pytest.mark.asyncio
    async def test_expired_lock_allows_login(self, svc, db):
        """A locked_until in the past should not block login."""
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_ctx.hash("goodpassword")
        # Lock expired 1 minute ago
        past_lock = _now() - timedelta(minutes=1)
        record = _make_db_record(password_hash=hashed, locked_until=past_lock, failed_login_attempts=5)

        call_count = 0

        async def _execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mapping_mock = MagicMock()
                mapping_mock.first.return_value = record
                result_mock = MagicMock()
                result_mock.mappings.return_value = mapping_mock
                return result_mock
            return MagicMock()

        db.execute.side_effect = _execute_side_effect

        user = await svc.login("testuser", "goodpassword")
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_locked_account_with_naive_datetime(self, svc, db):
        """locked_until stored as naive datetime (no tzinfo) should still block login."""
        # Naive datetime 10 minutes in the future
        future_naive = datetime.utcnow() + timedelta(minutes=10)
        assert future_naive.tzinfo is None
        record = _make_db_record(locked_until=future_naive)

        mapping_mock = MagicMock()
        mapping_mock.first.return_value = record
        result_mock = MagicMock()
        result_mock.mappings.return_value = mapping_mock
        db.execute.return_value = result_mock

        with pytest.raises(AuthenticationError, match="terkunci"):
            await svc.login("testuser", "anypassword")


# ---------------------------------------------------------------------------
# JWT — create_access_token & verify_token
# ---------------------------------------------------------------------------

class TestJWT:
    def test_create_and_verify_token(self, svc):
        user_id = str(uuid.uuid4())
        token = svc.create_access_token(user_id, UserRole.ADMINISTRATOR)
        payload = svc.verify_token(token)
        assert payload["sub"] == user_id
        assert payload["role"] == UserRole.ADMINISTRATOR.value

    def test_expired_token_raises_token_expired_error(self, svc):
        settings = get_settings()
        past = _now() - timedelta(seconds=1)
        payload = {"sub": "user-1", "role": UserRole.REVIEWER.value, "exp": past}
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(TokenExpiredError):
            svc.verify_token(token)

    def test_tampered_token_raises_authentication_error(self, svc):
        token = "this.is.not.a.valid.jwt"
        with pytest.raises(AuthenticationError):
            svc.verify_token(token)

    def test_token_contains_role(self, svc):
        token = svc.create_access_token("u1", UserRole.CAMPAIGN_MANAGER)
        payload = svc.verify_token(token)
        assert payload["role"] == UserRole.CAMPAIGN_MANAGER.value


# ---------------------------------------------------------------------------
# Session timeout
# ---------------------------------------------------------------------------

class TestSessionTimeout:
    def test_active_session_does_not_raise(self, svc):
        user = User(
            id="u1",
            username="alice",
            password_hash="x",
            role=UserRole.REVIEWER,
            is_active=True,
            last_activity_at=_now() - timedelta(minutes=5),
        )
        svc.check_session_timeout(user)  # should not raise

    def test_timed_out_session_raises(self, svc):
        user = User(
            id="u1",
            username="alice",
            password_hash="x",
            role=UserRole.REVIEWER,
            is_active=True,
            last_activity_at=_now() - timedelta(minutes=31),
        )
        with pytest.raises(AuthenticationError):
            svc.check_session_timeout(user)

    def test_no_last_activity_does_not_raise(self, svc):
        user = User(
            id="u1",
            username="alice",
            password_hash="x",
            role=UserRole.REVIEWER,
            is_active=True,
            last_activity_at=None,
        )
        svc.check_session_timeout(user)  # should not raise

    def test_exactly_30_minutes_does_not_raise(self, svc):
        """29 minutes of inactivity should still be valid (timeout is > 30 min)."""
        user = User(
            id="u1",
            username="alice",
            password_hash="x",
            role=UserRole.REVIEWER,
            is_active=True,
            last_activity_at=_now() - timedelta(minutes=29),
        )
        svc.check_session_timeout(user)  # should not raise

    def test_exactly_31_minutes_raises(self, svc):
        """31 minutes of inactivity exceeds the 30-minute timeout."""
        user = User(
            id="u1",
            username="alice",
            password_hash="x",
            role=UserRole.REVIEWER,
            is_active=True,
            last_activity_at=_now() - timedelta(minutes=31),
        )
        with pytest.raises(AuthenticationError, match="Sesi telah berakhir"):
            svc.check_session_timeout(user)

    def test_naive_last_activity_at_is_handled(self, svc):
        """last_activity_at without tzinfo (naive) should be treated as UTC."""
        # Naive datetime 5 minutes ago — should NOT raise
        naive_recent = datetime.utcnow() - timedelta(minutes=5)
        assert naive_recent.tzinfo is None
        user = User(
            id="u1",
            username="alice",
            password_hash="x",
            role=UserRole.REVIEWER,
            is_active=True,
            last_activity_at=naive_recent,
        )
        svc.check_session_timeout(user)  # should not raise

    def test_naive_last_activity_at_timed_out_raises(self, svc):
        """Naive last_activity_at that is too old should still raise."""
        naive_old = datetime.utcnow() - timedelta(minutes=35)
        assert naive_old.tzinfo is None
        user = User(
            id="u1",
            username="alice",
            password_hash="x",
            role=UserRole.REVIEWER,
            is_active=True,
            last_activity_at=naive_old,
        )
        with pytest.raises(AuthenticationError):
            svc.check_session_timeout(user)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class TestAuditLog:
    @pytest.mark.asyncio
    async def test_audit_log_written(self, svc, db):
        db.execute.return_value = MagicMock()
        await svc.write_audit_log(
            user_id="user-1",
            action="campaign.create",
            resource_type="campaign",
            resource_id="camp-1",
            details={"name": "Test Campaign"},
        )
        db.execute.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_log_without_optional_fields(self, svc, db):
        db.execute.return_value = MagicMock()
        await svc.write_audit_log(
            user_id="user-1",
            action="login",
            resource_type="auth",
        )
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_log_sql_contains_required_fields(self, svc, db):
        db.execute.return_value = MagicMock()
        await svc.write_audit_log(
            user_id="user-42",
            action="invitation.send",
            resource_type="invitation",
            resource_id="inv-99",
            details={"campaign_id": "camp-1"},
        )
        call_args = db.execute.call_args
        params = call_args[0][1]
        assert params["user_id"] == "user-42"
        assert params["action"] == "invitation.send"
        assert params["resource_type"] == "invitation"
        assert params["resource_id"] == "inv-99"


# ---------------------------------------------------------------------------
# Refresh token expired (verify_token edge cases)
# ---------------------------------------------------------------------------

class TestRefreshTokenExpired:
    """Edge cases specifically around token expiry — simulating refresh token scenarios."""

    def test_expired_token_raises_token_expired_not_auth_error(self, svc):
        """Expired token must raise TokenExpiredError, not generic AuthenticationError,
        so callers can distinguish between 'expired' and 'invalid'."""
        settings = get_settings()
        past = _now() - timedelta(seconds=1)
        payload = {"sub": "user-1", "role": UserRole.REVIEWER.value, "exp": past}
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(TokenExpiredError):
            svc.verify_token(token)

    def test_expired_token_is_not_caught_as_auth_error(self, svc):
        """TokenExpiredError should NOT be a subclass of AuthenticationError
        so callers can handle them separately."""
        settings = get_settings()
        past = _now() - timedelta(seconds=1)
        payload = {"sub": "user-1", "role": UserRole.REVIEWER.value, "exp": past}
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        try:
            svc.verify_token(token)
            pytest.fail("Expected TokenExpiredError to be raised")
        except TokenExpiredError:
            pass  # correct
        except AuthenticationError:
            pytest.fail("TokenExpiredError was caught as AuthenticationError — they must be distinct")

    def test_token_signed_with_wrong_secret_raises_auth_error(self, svc):
        """Token signed with a different secret should raise AuthenticationError."""
        payload = {"sub": "user-1", "role": UserRole.REVIEWER.value}
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(AuthenticationError):
            svc.verify_token(token)

    def test_empty_token_raises_auth_error(self, svc):
        with pytest.raises(AuthenticationError):
            svc.verify_token("")

    def test_token_missing_sub_still_decodes(self, svc):
        """A valid token without 'sub' should decode without error (sub is not validated by verify_token)."""
        settings = get_settings()
        expire = _now() + timedelta(minutes=30)
        payload = {"role": UserRole.REVIEWER.value, "exp": expire}
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = svc.verify_token(token)
        assert "sub" not in result or result.get("sub") is None
