"""Unit tests for TemplateService."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import TemplateInUseError, ValidationError
from app.models.domain import MessageTemplate
from app.services.template_service import TemplateService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now():
    return datetime.now(timezone.utc)


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


def _make_svc(db: Any = None) -> TemplateService:
    return TemplateService(db or _make_db())


def _make_template_row(**overrides) -> Dict[str, Any]:
    defaults: Dict[str, Any] = {
        "id": "tmpl-1",
        "name": "Test Template",
        "content": "Hello {{name}}, join {{campaign}}!",
        "variables": ["name", "campaign"],
        "default_values": json.dumps({"name": "Influencer", "campaign": "Summer Sale"}),
        "version": 1,
        "is_active": True,
        "campaign_ids": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return defaults


def _setup_get(db: AsyncMock, row: Dict[str, Any]) -> None:
    """Wire db.execute so that mappings().first() returns *row*."""
    mapping_mock = MagicMock()
    mapping_mock.first.return_value = row
    result_mock = MagicMock()
    result_mock.mappings.return_value = mapping_mock
    db.execute.return_value = result_mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    return _make_db()


@pytest.fixture()
def svc(db):
    return TemplateService(db)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

class TestCreate:
    @pytest.mark.asyncio
    async def test_create_valid_template(self, svc, db):
        db.execute.return_value = MagicMock()
        tmpl = await svc.create(
            name="Invite",
            content="Hi {{name}}, join {{campaign}}!",
            default_values={"name": "Friend", "campaign": "Sale"},
        )
        assert tmpl.name == "Invite"
        assert tmpl.version == 1
        assert set(tmpl.variables) == {"name", "campaign"}

    @pytest.mark.asyncio
    async def test_create_missing_default_raises(self, svc):
        with pytest.raises(ValidationError, match="campaign"):
            await svc.create(
                name="Bad",
                content="Hi {{name}}, join {{campaign}}!",
                default_values={"name": "Friend"},
            )

    @pytest.mark.asyncio
    async def test_create_no_variables_succeeds(self, svc, db):
        db.execute.return_value = MagicMock()
        tmpl = await svc.create(
            name="Static",
            content="Hello world!",
            default_values={},
        )
        assert tmpl.variables == []

    @pytest.mark.asyncio
    async def test_create_duplicate_variable_deduplicated(self, svc, db):
        db.execute.return_value = MagicMock()
        tmpl = await svc.create(
            name="Dup",
            content="{{name}} and {{name}} again",
            default_values={"name": "Alice"},
        )
        assert tmpl.variables == ["name"]

    @pytest.mark.asyncio
    async def test_create_calls_flush(self, svc, db):
        db.execute.return_value = MagicMock()
        await svc.create("T", "{{x}}", {"x": "val"})
        db.flush.assert_called_once()


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

class TestGet:
    @pytest.mark.asyncio
    async def test_get_existing_template(self, svc, db):
        row = _make_template_row()
        _setup_get(db, row)
        tmpl = await svc.get("tmpl-1")
        assert isinstance(tmpl, MessageTemplate)
        assert tmpl.id == "tmpl-1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises(self, svc, db):
        mapping_mock = MagicMock()
        mapping_mock.first.return_value = None
        result_mock = MagicMock()
        result_mock.mappings.return_value = mapping_mock
        db.execute.return_value = result_mock

        with pytest.raises(ValidationError):
            await svc.get("no-such-id")

    @pytest.mark.asyncio
    async def test_get_parses_default_values_from_json_string(self, svc, db):
        row = _make_template_row(
            default_values=json.dumps({"name": "Alice", "campaign": "X"})
        )
        _setup_get(db, row)
        tmpl = await svc.get("tmpl-1")
        assert tmpl.default_values == {"name": "Alice", "campaign": "X"}


# ---------------------------------------------------------------------------
# update (versioning)
# ---------------------------------------------------------------------------

class TestUpdate:
    def _setup_get_then_generic(self, db: AsyncMock, row: Dict[str, Any]) -> None:
        """First execute call returns the template row; subsequent calls return generic mock."""
        call_count = 0

        async def _execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mapping_mock = MagicMock()
                mapping_mock.first.return_value = row
                result_mock = MagicMock()
                result_mock.mappings.return_value = mapping_mock
                return result_mock
            return MagicMock()

        db.execute.side_effect = _execute

    @pytest.mark.asyncio
    async def test_update_increments_version(self, svc, db):
        row = _make_template_row(version=1)
        self._setup_get_then_generic(db, row)

        updated = await svc.update("tmpl-1", content="New {{name}} content")
        assert updated.version == 2

    @pytest.mark.asyncio
    async def test_update_saves_old_version(self, svc, db):
        row = _make_template_row(version=3)
        calls = []

        async def _execute(stmt, params=None):
            calls.append(str(stmt))
            if len(calls) == 1:
                mapping_mock = MagicMock()
                mapping_mock.first.return_value = row
                result_mock = MagicMock()
                result_mock.mappings.return_value = mapping_mock
                return result_mock
            return MagicMock()

        db.execute.side_effect = _execute

        await svc.update("tmpl-1", content="Updated {{name}}")
        # Second call should be INSERT INTO template_versions
        assert "template_versions" in calls[1]

    @pytest.mark.asyncio
    async def test_update_missing_default_raises(self, svc, db):
        row = _make_template_row()
        self._setup_get_then_generic(db, row)

        with pytest.raises(ValidationError):
            await svc.update("tmpl-1", content="Hi {{name}} and {{unknown}}")

    @pytest.mark.asyncio
    async def test_update_content_only_keeps_existing_defaults(self, svc, db):
        row = _make_template_row(
            content="Hello {{name}}",
            variables=["name"],
            default_values=json.dumps({"name": "Alice", "campaign": "X"}),
        )
        self._setup_get_then_generic(db, row)

        updated = await svc.update("tmpl-1", content="Hi {{name}}, welcome!")
        assert updated.content == "Hi {{name}}, welcome!"
        assert "name" in updated.default_values


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_unused_template_succeeds(self, svc, db):
        row = _make_template_row(campaign_ids=[])
        _setup_get(db, row)
        # Subsequent DELETE calls return generic mock
        db.execute.side_effect = None
        db.execute.return_value = MagicMock()

        call_count = 0

        async def _execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mapping_mock = MagicMock()
                mapping_mock.first.return_value = row
                result_mock = MagicMock()
                result_mock.mappings.return_value = mapping_mock
                return result_mock
            return MagicMock()

        db.execute.side_effect = _execute

        await svc.delete("tmpl-1")  # should not raise
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_active_template_raises(self, svc, db):
        row = _make_template_row(campaign_ids=["camp-1", "camp-2"])
        _setup_get(db, row)

        call_count = 0

        async def _execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mapping_mock = MagicMock()
                mapping_mock.first.return_value = row
                result_mock = MagicMock()
                result_mock.mappings.return_value = mapping_mock
                return result_mock
            return MagicMock()

        db.execute.side_effect = _execute

        with pytest.raises(TemplateInUseError):
            await svc.delete("tmpl-1")


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------

class TestPreview:
    def _setup_get(self, db: AsyncMock, row: Dict[str, Any]) -> None:
        mapping_mock = MagicMock()
        mapping_mock.first.return_value = row
        result_mock = MagicMock()
        result_mock.mappings.return_value = mapping_mock
        db.execute.return_value = result_mock

    @pytest.mark.asyncio
    async def test_preview_substitutes_all_variables(self, svc, db):
        row = _make_template_row(
            content="Hi {{name}}, join {{campaign}}!",
            default_values=json.dumps({"name": "Default", "campaign": "Default Camp"}),
        )
        self._setup_get(db, row)

        result = await svc.preview(
            "tmpl-1",
            influencer_data={"name": "Alice", "campaign": "Summer Sale"},
        )
        assert result == "Hi Alice, join Summer Sale!"
        assert "{{" not in result

    @pytest.mark.asyncio
    async def test_preview_uses_default_when_influencer_data_missing(self, svc, db):
        row = _make_template_row(
            content="Hi {{name}}, join {{campaign}}!",
            default_values=json.dumps({"name": "Friend", "campaign": "Big Sale"}),
        )
        self._setup_get(db, row)

        result = await svc.preview("tmpl-1", influencer_data={})
        assert result == "Hi Friend, join Big Sale!"

    @pytest.mark.asyncio
    async def test_preview_influencer_data_overrides_defaults(self, svc, db):
        row = _make_template_row(
            content="Hello {{name}}!",
            default_values=json.dumps({"name": "Default"}),
        )
        self._setup_get(db, row)

        result = await svc.preview("tmpl-1", influencer_data={"name": "Bob"})
        assert result == "Hello Bob!"

    @pytest.mark.asyncio
    async def test_preview_raises_if_placeholder_remains(self, svc, db):
        row = _make_template_row(
            content="Hi {{name}} and {{unknown}}!",
            default_values=json.dumps({"name": "Alice"}),
        )
        self._setup_get(db, row)

        with pytest.raises(ValidationError, match="unknown"):
            await svc.preview("tmpl-1", influencer_data={})

    @pytest.mark.asyncio
    async def test_preview_no_variables_returns_content_as_is(self, svc, db):
        row = _make_template_row(
            content="Static message, no variables.",
            variables=[],
            default_values=json.dumps({}),
        )
        self._setup_get(db, row)

        result = await svc.preview("tmpl-1", influencer_data={})
        assert result == "Static message, no variables."
