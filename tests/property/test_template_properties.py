"""Property-based tests untuk TemplateService.

Validates: Requirements 5.4
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import ValidationError
from app.models.domain import MessageTemplate
from app.services.template_service import TemplateService, _extract_variables

_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_template(
    template_id: str,
    content: str,
    variables: List[str],
    default_values: Dict[str, str],
    version: int = 1,
) -> MessageTemplate:
    return MessageTemplate(
        id=template_id,
        name="Test Template",
        content=content,
        variables=variables,
        default_values=default_values,
        version=version,
        is_active=True,
        campaign_ids=[],
        created_at=_now(),
        updated_at=_now(),
    )


def _make_db_for_template(template: Optional[MessageTemplate] = None) -> AsyncMock:
    """Buat mock DB yang mengembalikan template tertentu."""
    db = AsyncMock()
    db.flush = AsyncMock()

    async def _execute(query, params=None):
        q = str(query)
        mock_result = MagicMock()
        mock_mappings = MagicMock()

        if template and "SELECT * FROM message_templates" in q:
            row = {
                "id": template.id,
                "name": template.name,
                "content": template.content,
                "variables": json.dumps(template.variables),
                "default_values": json.dumps(template.default_values),
                "version": template.version,
                "is_active": template.is_active,
                "campaign_ids": json.dumps(template.campaign_ids),
                "created_at": template.created_at,
                "updated_at": template.updated_at,
            }
            mock_mappings.first.return_value = row
        else:
            mock_mappings.first.return_value = None

        mock_mappings.all.return_value = []
        mock_result.mappings.return_value = mock_mappings
        return mock_result

    db.execute = _execute
    return db


# ---------------------------------------------------------------------------
# Property 22: Validasi Variabel Template
# ---------------------------------------------------------------------------


class TestProperty22TemplateVariableValidation:
    """Validates: Requirements 5.4 — create() tanpa default_values raise ValidationError."""

    @given(
        var_name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=50)
    def test_create_without_default_raises_validation_error(self, var_name: str):
        """For any content dengan {{variable}}, create() tanpa default_values raise ValidationError."""
        async def _run():
            db = AsyncMock()
            db.flush = AsyncMock()
            service = TemplateService(db)

            content = f"Halo {{{{name}}}}, ini adalah pesan untuk {{{{{var_name}}}}}."

            # Tidak menyediakan default untuk var_name
            with pytest.raises(ValidationError):
                await service.create(
                    name="Test Template",
                    content=content,
                    default_values={"name": "Influencer"},  # var_name tidak ada
                )

        _run_async(_run())

    @given(
        var_name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=50)
    def test_create_with_all_defaults_succeeds(self, var_name: str):
        """create() dengan semua default_values tersedia tidak raise ValidationError."""
        async def _run():
            db = AsyncMock()
            db.flush = AsyncMock()

            async def _execute(query, params=None):
                mock_result = MagicMock()
                mock_mappings = MagicMock()
                mock_mappings.first.return_value = None
                mock_result.mappings.return_value = mock_mappings
                return mock_result

            db.execute = _execute
            service = TemplateService(db)

            content = f"Halo {{{{{var_name}}}}}."
            default_values = {var_name: "default_value"}

            # Tidak boleh raise
            template = await service.create(
                name="Test Template",
                content=content,
                default_values=default_values,
            )
            assert template is not None
            assert var_name in template.variables

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 23: Pratinjau Template Tersubstitusi
# ---------------------------------------------------------------------------


class TestProperty23TemplatePreviewSubstituted:
    """Validates: Requirements 5.4 — preview tidak mengandung {{...}} jika data lengkap."""

    @given(
        var_name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
            min_size=1,
            max_size=20,
        ),
        var_value=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_preview_no_remaining_placeholders(self, var_name: str, var_value: str):
        """For any template dengan variabel dan data lengkap, preview tidak mengandung {{...}}."""
        async def _run():
            template_id = str(uuid.uuid4())
            content = f"Halo {{{{{var_name}}}}}!"
            template = _make_template(
                template_id=template_id,
                content=content,
                variables=[var_name],
                default_values={var_name: "default"},
            )

            db = _make_db_for_template(template)
            service = TemplateService(db)

            rendered = await service.preview(
                template_id=template_id,
                influencer_data={var_name: var_value},
            )

            remaining = _VAR_PATTERN.findall(rendered)
            assert len(remaining) == 0, (
                f"Preview masih mengandung placeholder: {remaining}"
            )
            assert var_value in rendered, (
                f"Nilai {var_value!r} harus ada dalam hasil preview"
            )

        _run_async(_run())

    @given(
        var_names=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
                min_size=1,
                max_size=10,
            ),
            min_size=1,
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_preview_with_multiple_variables_no_placeholders(self, var_names: List[str]):
        """Preview dengan banyak variabel dan data lengkap tidak mengandung {{...}}."""
        async def _run():
            template_id = str(uuid.uuid4())
            content = " ".join(f"{{{{{v}}}}}" for v in var_names)
            default_values = {v: f"val_{v}" for v in var_names}
            template = _make_template(
                template_id=template_id,
                content=content,
                variables=var_names,
                default_values=default_values,
            )

            db = _make_db_for_template(template)
            service = TemplateService(db)

            rendered = await service.preview(
                template_id=template_id,
                influencer_data=default_values,
            )

            remaining = _VAR_PATTERN.findall(rendered)
            assert len(remaining) == 0, (
                f"Preview masih mengandung placeholder: {remaining}"
            )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 24: Riwayat Versi Template
# ---------------------------------------------------------------------------


class TestProperty24TemplateVersionHistory:
    """Validates: Requirements 5.4 — version selalu bertambah monoton."""

    @given(
        initial_version=st.integers(min_value=1, max_value=100),
        update_count=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=50)
    def test_version_monotonically_increases(
        self,
        initial_version: int,
        update_count: int,
    ):
        """For any sequence update, version selalu bertambah monoton."""
        async def _run():
            template_id = str(uuid.uuid4())
            current_version = initial_version
            versions_seen: List[int] = [current_version]

            for _ in range(update_count):
                content = f"Updated content v{current_version}"
                template = _make_template(
                    template_id=template_id,
                    content=content,
                    variables=[],
                    default_values={},
                    version=current_version,
                )

                db = AsyncMock()
                db.flush = AsyncMock()

                async def _execute(query, params=None, _tmpl=template):
                    q = str(query)
                    mock_result = MagicMock()
                    mock_mappings = MagicMock()

                    if "SELECT * FROM message_templates" in q:
                        row = {
                            "id": _tmpl.id,
                            "name": _tmpl.name,
                            "content": _tmpl.content,
                            "variables": json.dumps(_tmpl.variables),
                            "default_values": json.dumps(_tmpl.default_values),
                            "version": _tmpl.version,
                            "is_active": _tmpl.is_active,
                            "campaign_ids": json.dumps(_tmpl.campaign_ids),
                            "created_at": _tmpl.created_at,
                            "updated_at": _tmpl.updated_at,
                        }
                        mock_mappings.first.return_value = row
                    else:
                        mock_mappings.first.return_value = None

                    mock_mappings.all.return_value = []
                    mock_result.mappings.return_value = mock_mappings
                    return mock_result

                db.execute = _execute
                service = TemplateService(db)

                updated = await service.update(
                    template_id=template_id,
                    content=f"New content {current_version + 1}",
                    default_values={},
                )

                new_version = updated.version
                assert new_version > current_version, (
                    f"Versi baru {new_version} harus > versi sebelumnya {current_version}"
                )
                versions_seen.append(new_version)
                current_version = new_version

            # Verifikasi monoton meningkat
            for i in range(len(versions_seen) - 1):
                assert versions_seen[i] < versions_seen[i + 1], (
                    f"Versi tidak monoton: {versions_seen[i]} >= {versions_seen[i + 1]}"
                )

        _run_async(_run())
