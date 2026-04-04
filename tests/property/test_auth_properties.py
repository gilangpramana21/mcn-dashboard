"""Property-based tests untuk AuthService dan RBAC.

Validates: Requirements 9.1, 9.2, 9.4, 9.5
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import ValidationError
from app.models.domain import UserRole
from app.services.auth_service import AuthService
from app.services.rbac import require_role


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Jalankan coroutine dalam event loop baru (kompatibel dengan Hypothesis)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_db() -> AsyncMock:
    """Buat mock DB dengan execute dan flush."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.flush = AsyncMock()
    return db


def _make_auth_service(db: Any = None) -> AuthService:
    if db is None:
        db = _make_db()
    return AuthService(db)


def _make_login_db(record: Dict[str, Any]) -> AsyncMock:
    """Buat mock DB yang mengembalikan record pada SELECT pertama."""
    db = AsyncMock()
    db.flush = AsyncMock()

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
    return db


# ---------------------------------------------------------------------------
# Property 28: Validasi Panjang Kata Sandi
# ---------------------------------------------------------------------------


class TestProperty28PasswordLengthValidation:
    """Validates: Requirements 9.1 — password < 8 karakter selalu ditolak."""

    @given(
        username=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
        password=st.text(min_size=0, max_size=7),
        role=st.sampled_from(list(UserRole)),
    )
    @settings(max_examples=50)
    def test_short_password_always_rejected(
        self,
        username: str,
        password: str,
        role: UserRole,
    ):
        """Password dengan panjang < 8 karakter selalu menghasilkan ValidationError."""
        async def _run():
            svc = _make_auth_service()
            with pytest.raises(ValidationError):
                await svc.register_user(username, password, role)

        _run_async(_run())

    @given(
        username=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
        password=st.text(min_size=8, max_size=100),
        role=st.sampled_from(list(UserRole)),
    )
    @settings(max_examples=50)
    def test_password_8_or_more_chars_accepted(
        self,
        username: str,
        password: str,
        role: UserRole,
    ):
        """Password dengan panjang >= 8 karakter tidak menghasilkan ValidationError."""
        async def _run():
            db = _make_db()
            svc = _make_auth_service(db)
            # Tidak boleh raise ValidationError
            try:
                user = await svc.register_user(username, password, role)
                assert user.username == username
                assert user.role == role
            except ValidationError:
                raise AssertionError(
                    f"ValidationError tidak seharusnya muncul untuk password panjang {len(password)}"
                )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 29: Kontrol Akses Berbasis Peran
# ---------------------------------------------------------------------------


class TestProperty29RoleBasedAccessControl:
    """Validates: Requirements 9.2 — operasi terbatas mengembalikan 403 untuk peran tidak berwenang."""

    @given(
        role=st.sampled_from([UserRole.CAMPAIGN_MANAGER, UserRole.REVIEWER]),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_non_admin_role_gets_403_for_admin_only_endpoint(
        self,
        role: UserRole,
    ):
        """Peran non-Administrator selalu mendapat HTTP 403 saat mengakses endpoint admin."""
        # Buat mock current_user dengan peran yang diberikan
        mock_user = {"sub": str(uuid.uuid4()), "role": role.value}

        # Buat dependency require_role(ADMINISTRATOR)
        dependency = require_role(UserRole.ADMINISTRATOR)

        # Panggil dependency dengan mock user
        with pytest.raises(HTTPException) as exc_info:
            await dependency(current_user=mock_user)

        assert exc_info.value.status_code == 403, (
            f"Peran {role.value} seharusnya mendapat 403, bukan {exc_info.value.status_code}"
        )

    @given(
        unauthorized_role=st.sampled_from([UserRole.REVIEWER]),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_reviewer_cannot_access_campaign_manager_endpoint(
        self,
        unauthorized_role: UserRole,
    ):
        """Peran Peninjau tidak dapat mengakses endpoint yang membutuhkan Manajer_Kampanye."""
        mock_user = {"sub": str(uuid.uuid4()), "role": unauthorized_role.value}

        dependency = require_role(UserRole.CAMPAIGN_MANAGER, UserRole.ADMINISTRATOR)

        with pytest.raises(HTTPException) as exc_info:
            await dependency(current_user=mock_user)

        assert exc_info.value.status_code == 403, (
            f"Peran {unauthorized_role.value} seharusnya mendapat 403"
        )

    @given(
        role=st.sampled_from(list(UserRole)),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_authorized_role_does_not_get_403(
        self,
        role: UserRole,
    ):
        """Peran yang diizinkan tidak mendapat HTTP 403."""
        mock_user = {"sub": str(uuid.uuid4()), "role": role.value}

        # Izinkan semua peran
        dependency = require_role(*list(UserRole))

        # Tidak boleh raise HTTPException
        result = await dependency(current_user=mock_user)
        assert result == mock_user


# ---------------------------------------------------------------------------
# Property 30: Audit Log untuk Setiap Operasi Kampanye
# ---------------------------------------------------------------------------


class TestProperty30AuditLogForCampaignOperations:
    """Validates: Requirements 9.4 — setiap operasi kampanye/undangan menghasilkan entri audit log."""

    @given(
        user_id=st.uuids().map(str),
        action=st.sampled_from([
            "campaign.create",
            "campaign.update",
            "campaign.delete",
            "campaign.start",
            "campaign.stop",
            "invitation.send",
            "invitation.schedule",
        ]),
        resource_type=st.sampled_from(["campaign", "invitation"]),
        resource_id=st.one_of(st.none(), st.uuids().map(str)),
        details=st.fixed_dictionaries({
            "name": st.text(min_size=1, max_size=50),
        }),
    )
    @settings(max_examples=50)
    def test_audit_log_always_written_for_campaign_operations(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id,
        details: dict,
    ):
        """Setiap operasi kampanye/undangan menghasilkan tepat satu entri audit log."""
        async def _run():
            db = _make_db()
            svc = _make_auth_service(db)

            await svc.write_audit_log(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
            )

            # Harus ada tepat satu panggilan execute (INSERT audit log)
            assert db.execute.call_count == 1, (
                f"Harus ada tepat 1 panggilan execute, bukan {db.execute.call_count}"
            )
            # Harus ada panggilan flush
            assert db.flush.call_count == 1, (
                f"Harus ada tepat 1 panggilan flush, bukan {db.flush.call_count}"
            )

        _run_async(_run())

    @given(
        user_id=st.uuids().map(str),
        action=st.sampled_from([
            "campaign.create",
            "campaign.update",
            "invitation.send",
        ]),
        resource_type=st.sampled_from(["campaign", "invitation"]),
        resource_id=st.uuids().map(str),
    )
    @settings(max_examples=50)
    def test_audit_log_params_contain_required_fields(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
    ):
        """Parameter audit log selalu mengandung user_id, action, resource_type, resource_id."""
        async def _run():
            db = _make_db()
            svc = _make_auth_service(db)

            await svc.write_audit_log(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
            )

            call_args = db.execute.call_args
            params = call_args[0][1]

            assert params["user_id"] == user_id, f"user_id tidak cocok: {params['user_id']} != {user_id}"
            assert params["action"] == action, f"action tidak cocok: {params['action']} != {action}"
            assert params["resource_type"] == resource_type, (
                f"resource_type tidak cocok: {params['resource_type']} != {resource_type}"
            )
            assert params["resource_id"] == resource_id, (
                f"resource_id tidak cocok: {params['resource_id']} != {resource_id}"
            )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 31: Penguncian Akun Setelah 5 Kali Gagal Login
# ---------------------------------------------------------------------------


class TestProperty31AccountLockoutAfter5Failures:
    """Validates: Requirements 9.5 — akun terkunci setelah 5 kali gagal berturut-turut."""

    @given(
        failed_attempts=st.integers(min_value=4, max_value=20),
    )
    @settings(max_examples=50)
    def test_account_locked_when_failed_attempts_gte_4(
        self,
        failed_attempts: int,
    ):
        """Untuk failed_login_attempts >= 4, percobaan login salah berikutnya memicu penguncian."""
        from passlib.context import CryptContext

        async def _run():
            pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
            hashed = pwd_ctx.hash("correctpassword")

            record = {
                "id": str(uuid.uuid4()),
                "username": "testuser",
                "password_hash": hashed,
                "role": UserRole.CAMPAIGN_MANAGER.value,
                "is_active": True,
                "failed_login_attempts": failed_attempts,
                "locked_until": None,
                "last_activity_at": None,
            }

            db = _make_login_db(record)
            svc = _make_auth_service(db)

            from app.exceptions import AuthenticationError
            with pytest.raises(AuthenticationError):
                await svc.login("testuser", "wrongpassword")

            # Cek bahwa UPDATE SQL mengandung locked_until
            assert db.execute.call_count >= 2, (
                f"Harus ada minimal 2 panggilan execute (SELECT + UPDATE), bukan {db.execute.call_count}"
            )
            update_call_args = db.execute.call_args_list[1]
            sql_text = str(update_call_args[0][0])
            assert "locked_until" in sql_text, (
                f"UPDATE SQL harus mengandung 'locked_until' untuk failed_attempts={failed_attempts}, "
                f"SQL: {sql_text}"
            )

        _run_async(_run())

    @given(
        failed_attempts=st.integers(min_value=0, max_value=3),
    )
    @settings(max_examples=50)
    def test_account_not_locked_when_failed_attempts_lt_4(
        self,
        failed_attempts: int,
    ):
        """Untuk failed_login_attempts < 4, percobaan login salah tidak memicu penguncian."""
        from passlib.context import CryptContext

        async def _run():
            pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
            hashed = pwd_ctx.hash("correctpassword")

            record = {
                "id": str(uuid.uuid4()),
                "username": "testuser",
                "password_hash": hashed,
                "role": UserRole.CAMPAIGN_MANAGER.value,
                "is_active": True,
                "failed_login_attempts": failed_attempts,
                "locked_until": None,
                "last_activity_at": None,
            }

            db = _make_login_db(record)
            svc = _make_auth_service(db)

            from app.exceptions import AuthenticationError
            with pytest.raises(AuthenticationError):
                await svc.login("testuser", "wrongpassword")

            # Cek bahwa UPDATE SQL TIDAK mengandung locked_until
            assert db.execute.call_count >= 2, (
                f"Harus ada minimal 2 panggilan execute (SELECT + UPDATE), bukan {db.execute.call_count}"
            )
            update_call_args = db.execute.call_args_list[1]
            sql_text = str(update_call_args[0][0])
            assert "locked_until" not in sql_text, (
                f"UPDATE SQL tidak seharusnya mengandung 'locked_until' untuk failed_attempts={failed_attempts}, "
                f"SQL: {sql_text}"
            )

        _run_async(_run())
