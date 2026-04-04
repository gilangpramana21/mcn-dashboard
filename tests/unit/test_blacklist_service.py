"""Unit tests for BlacklistService."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import BlacklistViolationError
from app.services.blacklist_service import BlacklistService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


def _make_svc(db: Any = None) -> BlacklistService:
    return BlacklistService(db or _make_db())


def _mock_execute_returning(rows: list) -> AsyncMock:
    """Return an AsyncMock for db.execute that yields *rows* via .first()."""
    result = MagicMock()
    result.first.return_value = rows[0] if rows else None
    execute_mock = AsyncMock(return_value=result)
    return execute_mock


def _mock_execute_mappings(rows: list) -> AsyncMock:
    """Return an AsyncMock for db.execute that yields *rows* via .mappings().all()."""
    mappings_mock = MagicMock()
    mappings_mock.all.return_value = rows
    result = MagicMock()
    result.mappings.return_value = mappings_mock
    return AsyncMock(return_value=result)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    return _make_db()


@pytest.fixture()
def svc(db):
    return BlacklistService(db)


# ---------------------------------------------------------------------------
# is_blacklisted
# ---------------------------------------------------------------------------

class TestIsBlacklisted:
    @pytest.mark.asyncio
    async def test_returns_true_when_active_entry_exists(self, svc, db):
        db.execute = _mock_execute_returning([{"id": "some-uuid"}])
        result = await svc.is_blacklisted("inf-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_active_entry(self, svc, db):
        db.execute = _mock_execute_returning([])
        result = await svc.is_blacklisted("inf-1")
        assert result is False


# ---------------------------------------------------------------------------
# add_to_blacklist
# ---------------------------------------------------------------------------

class TestAddToBlacklist:
    @pytest.mark.asyncio
    async def test_add_new_influencer_succeeds(self, svc, db):
        call_count = 0

        async def _execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # is_blacklisted check — no active entry
                result = MagicMock()
                result.first.return_value = None
                return result
            return MagicMock()

        db.execute.side_effect = _execute

        entry_id = await svc.add_to_blacklist("inf-1", "Spam", "user-1")
        assert isinstance(entry_id, str)
        assert len(entry_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_add_already_blacklisted_raises(self, svc, db):
        # First call (is_blacklisted) returns an active entry
        db.execute = _mock_execute_returning([{"id": "existing"}])

        with pytest.raises(BlacklistViolationError):
            await svc.add_to_blacklist("inf-1", "Spam", "user-1")

    @pytest.mark.asyncio
    async def test_add_calls_flush(self, svc, db):
        call_count = 0

        async def _execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                result = MagicMock()
                result.first.return_value = None
                return result
            return MagicMock()

        db.execute.side_effect = _execute

        await svc.add_to_blacklist("inf-2", "Fraud", "user-1")
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_executes_insert_and_update(self, svc, db):
        """Verify that both INSERT into blacklist and UPDATE influencers are called."""
        calls = []

        async def _execute(stmt, params=None):
            calls.append(str(stmt))
            if len(calls) == 1:
                result = MagicMock()
                result.first.return_value = None
                return result
            return MagicMock()

        db.execute.side_effect = _execute

        await svc.add_to_blacklist("inf-3", "Reason", "user-1")
        # 1: is_blacklisted SELECT, 2: INSERT blacklist, 3: UPDATE influencers
        assert len(calls) == 3


# ---------------------------------------------------------------------------
# remove_from_blacklist
# ---------------------------------------------------------------------------

class TestRemoveFromBlacklist:
    @pytest.mark.asyncio
    async def test_remove_calls_update_and_flush(self, svc, db):
        db.execute = AsyncMock(return_value=MagicMock())

        await svc.remove_from_blacklist("inf-1", "user-2", "Rehabilitated")

        assert db.execute.call_count == 2  # UPDATE blacklist + UPDATE influencers
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_sql_contains_removed_at(self, svc, db):
        calls = []

        async def _execute(stmt, params=None):
            calls.append((str(stmt), params))
            return MagicMock()

        db.execute.side_effect = _execute

        await svc.remove_from_blacklist("inf-1", "user-2", "OK")

        first_sql = calls[0][0]
        assert "removed_at" in first_sql

    @pytest.mark.asyncio
    async def test_remove_clears_influencer_blacklist_flag(self, svc, db):
        calls = []

        async def _execute(stmt, params=None):
            calls.append((str(stmt), params))
            return MagicMock()

        db.execute.side_effect = _execute

        await svc.remove_from_blacklist("inf-1", "user-2", "OK")

        second_sql = calls[1][0]
        assert "blacklisted" in second_sql


# ---------------------------------------------------------------------------
# get_blacklist
# ---------------------------------------------------------------------------

class TestGetBlacklist:
    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self, svc, db):
        row = {
            "id": "bl-1",
            "influencer_id": "inf-1",
            "influencer_name": "Alice",
            "reason": "Spam",
            "added_by": "user-1",
            "added_at": datetime.now(timezone.utc),
        }
        db.execute = _mock_execute_mappings([row])

        result = await svc.get_blacklist()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["influencer_id"] == "inf-1"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_entries(self, svc, db):
        db.execute = _mock_execute_mappings([])

        result = await svc.get_blacklist()
        assert result == []


# ---------------------------------------------------------------------------
# export_blacklist_csv
# ---------------------------------------------------------------------------

class TestExportBlacklistCsv:
    @pytest.mark.asyncio
    async def test_csv_contains_header(self, svc, db):
        db.execute = _mock_execute_mappings([])

        csv_str = await svc.export_blacklist_csv()
        assert "influencer_id" in csv_str
        assert "reason" in csv_str

    @pytest.mark.asyncio
    async def test_csv_contains_data_rows(self, svc, db):
        row = {
            "id": "bl-1",
            "influencer_id": "inf-42",
            "influencer_name": "Bob",
            "reason": "Fraud",
            "added_by": "user-1",
            "added_at": datetime(2024, 1, 15, tzinfo=timezone.utc),
        }
        db.execute = _mock_execute_mappings([row])

        csv_str = await svc.export_blacklist_csv()
        assert "inf-42" in csv_str
        assert "Fraud" in csv_str

    @pytest.mark.asyncio
    async def test_csv_is_string(self, svc, db):
        db.execute = _mock_execute_mappings([])

        result = await svc.export_blacklist_csv()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_csv_multiple_rows(self, svc, db):
        rows = [
            {
                "id": f"bl-{i}",
                "influencer_id": f"inf-{i}",
                "influencer_name": f"Name{i}",
                "reason": f"Reason{i}",
                "added_by": "user-1",
                "added_at": datetime.now(timezone.utc),
            }
            for i in range(3)
        ]
        db.execute = _mock_execute_mappings(rows)

        csv_str = await svc.export_blacklist_csv()
        lines = [l for l in csv_str.strip().splitlines() if l]
        # 1 header + 3 data rows
        assert len(lines) == 4
