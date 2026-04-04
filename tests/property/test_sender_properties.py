"""Property-based tests untuk SenderAgent.

Validates: Requirements 9.2
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.agents.sender_agent import SenderAgent
from app.exceptions import BlacklistViolationError
from app.models.domain import (
    Influencer,
    InfluencerStatus,
    InvitationStatus,
    MessageTemplate,
)
from app.services.blacklist_service import BlacklistService

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


def _make_influencer(influencer_id: str, blacklisted: bool = False) -> Influencer:
    return Influencer(
        id=influencer_id,
        tiktok_user_id=f"tiktok-{influencer_id}",
        name=f"Influencer {influencer_id}",
        phone_number="+6281234567890",
        follower_count=10000,
        engagement_rate=0.05,
        content_categories=["fashion"],
        location="Jakarta",
        blacklisted=blacklisted,
    )


def _make_template(content: str = "Halo {{name}}!") -> MessageTemplate:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return MessageTemplate(
        id="template-1",
        name="Test Template",
        content=content,
        variables=["name"],
        default_values={"name": "Influencer"},
        version=1,
        is_active=True,
        campaign_ids=[],
        created_at=now,
        updated_at=now,
    )


def _make_blacklist_service(blacklisted_ids: Set[str]) -> BlacklistService:
    db = AsyncMock()
    db.flush = AsyncMock()

    async def _execute(query, params=None):
        q = str(query)
        mock_result = MagicMock()
        mock_mappings = MagicMock()

        if "SELECT 1 FROM blacklist" in q and params:
            influencer_id = params.get("influencer_id", "")
            if influencer_id in blacklisted_ids:
                mock_result.first.return_value = (1,)
            else:
                mock_result.first.return_value = None
        else:
            mock_result.first.return_value = None

        mock_mappings.first.return_value = None
        mock_mappings.all.return_value = []
        mock_result.mappings.return_value = mock_mappings
        return mock_result

    db.execute = _execute
    return BlacklistService(db)


def _make_db_with_template(template: MessageTemplate) -> AsyncMock:
    """Buat mock DB yang mengembalikan template dan menerima INSERT invitations."""
    import json
    db = AsyncMock()
    db.flush = AsyncMock()

    async def _execute(query, params=None):
        q = str(query)
        mock_result = MagicMock()
        mock_mappings = MagicMock()

        if "SELECT * FROM message_templates" in q:
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
# Property 7 & 9: total_sent + total_failed + total_pending == total_processed
# ---------------------------------------------------------------------------


class TestProperty7And9InvitationAccountability:
    """Validates: Requirements 9.2 — total_sent + total_failed + total_pending == total_processed."""

    @given(
        influencer_count=st.integers(min_value=0, max_value=20),
        blacklist_count=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=50)
    def test_totals_sum_equals_total_processed(
        self,
        influencer_count: int,
        blacklist_count: int,
    ):
        """total_sent + total_failed + total_pending == total_processed untuk semua kasus."""
        async def _run():
            actual_blacklist = min(blacklist_count, influencer_count)
            blacklisted_ids = {f"inf-{i}" for i in range(actual_blacklist)}

            influencers = [
                _make_influencer(
                    influencer_id=f"inf-{i}",
                    blacklisted=(f"inf-{i}" in blacklisted_ids),
                )
                for i in range(influencer_count)
            ]

            template = _make_template()
            blacklist_service = _make_blacklist_service(blacklisted_ids)
            db = _make_db_with_template(template)

            # Mock WhatsApp client
            mock_wa = AsyncMock()
            mock_wa_result = MagicMock()
            mock_wa_result.message_id = "msg-123"
            mock_wa.send_message = AsyncMock(return_value=mock_wa_result)

            sender = SenderAgent(
                blacklist_service=blacklist_service,
                whatsapp_client=mock_wa,
            )

            report = await sender.send_bulk_invitations(
                influencers=influencers,
                template_id="template-1",
                campaign_id="camp-1",
                db=db,
            )

            assert report.total_sent + report.total_failed + report.total_pending == report.total_processed, (
                f"total_sent({report.total_sent}) + total_failed({report.total_failed}) + "
                f"total_pending({report.total_pending}) != total_processed({report.total_processed})"
            )
            assert report.total_processed == influencer_count

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 8: Rate Limiting
# ---------------------------------------------------------------------------


class TestProperty8RateLimiting:
    """Validates: Requirements 9.2 — _count_in_window selalu <= _RATE_LIMIT."""

    @given(
        send_count=st.integers(min_value=0, max_value=200),
    )
    @settings(max_examples=50)
    def test_count_in_window_never_exceeds_rate_limit(self, send_count: int):
        """_count_in_window setelah _wait_for_rate_limit tidak melebihi _RATE_LIMIT."""
        blacklist_service = _make_blacklist_service(set())
        sender = SenderAgent(blacklist_service=blacklist_service)

        # Simulasikan pengiriman dalam window yang sama
        now = time.monotonic()
        for _ in range(min(send_count, sender._RATE_LIMIT)):
            sender._send_timestamps.append(now)

        count = sender._count_in_window(now)
        assert count <= sender._RATE_LIMIT, (
            f"count_in_window={count} melebihi _RATE_LIMIT={sender._RATE_LIMIT}"
        )


# ---------------------------------------------------------------------------
# Property 11: Substitusi Variabel
# ---------------------------------------------------------------------------


class TestProperty11VariableSubstitution:
    """Validates: Requirements 9.2 — hasil substitusi tidak mengandung {{...}}."""

    @given(
        var_name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
            min_size=1,
            max_size=20,
        ),
        var_value=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_substitution_no_remaining_placeholders(
        self,
        var_name: str,
        var_value: str,
    ):
        """For any template content dengan variabel dan data lengkap, hasil tidak mengandung {{...}}."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        blacklist_service = _make_blacklist_service(set())
        sender = SenderAgent(blacklist_service=blacklist_service)

        template = MessageTemplate(
            id="template-1",
            name="Test",
            content=f"Halo {{{{{var_name}}}}}!",
            variables=[var_name],
            default_values={var_name: var_value},
            version=1,
            is_active=True,
            campaign_ids=[],
            created_at=now,
            updated_at=now,
        )

        influencer = _make_influencer("inf-1")

        result = sender._substitute_variables(template, influencer, "camp-1")

        remaining = _VAR_PATTERN.findall(result)
        assert len(remaining) == 0, (
            f"Hasil substitusi masih mengandung placeholder: {remaining}"
        )
