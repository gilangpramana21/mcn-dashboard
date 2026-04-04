"""Blacklist Service — manage influencer blacklist entries."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BlacklistViolationError


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class BlacklistService:
    """Handles adding, removing, querying, and exporting the influencer blacklist."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Add
    # ------------------------------------------------------------------

    async def add_to_blacklist(
        self,
        influencer_id: str,
        reason: str,
        added_by_user_id: str,
    ) -> str:
        """Insert a blacklist entry and mark the influencer as blacklisted.

        Returns the new blacklist entry id.
        Raises BlacklistViolationError if the influencer is already blacklisted.
        """
        if await self.is_blacklisted(influencer_id):
            raise BlacklistViolationError(
                f"Influencer {influencer_id} sudah ada dalam daftar hitam."
            )

        entry_id = str(uuid.uuid4())
        now = _now_utc()

        await self._db.execute(
            text(
                """
                INSERT INTO blacklist (id, influencer_id, reason, added_by, added_at)
                VALUES (:id, :influencer_id, :reason, :added_by, :added_at)
                """
            ),
            {
                "id": entry_id,
                "influencer_id": influencer_id,
                "reason": reason,
                "added_by": added_by_user_id,
                "added_at": now,
            },
        )

        await self._db.execute(
            text(
                """
                UPDATE influencers
                SET blacklisted = TRUE,
                    blacklist_reason = :reason,
                    status = 'BLACKLISTED',
                    updated_at = :now
                WHERE id = :influencer_id
                """
            ),
            {"reason": reason, "now": now, "influencer_id": influencer_id},
        )

        await self._db.flush()
        return entry_id

    # ------------------------------------------------------------------
    # Remove
    # ------------------------------------------------------------------

    async def remove_from_blacklist(
        self,
        influencer_id: str,
        removed_by_user_id: str,
        removal_reason: str,
    ) -> None:
        """Mark the active blacklist entry as removed and clear the influencer flag."""
        now = _now_utc()

        await self._db.execute(
            text(
                """
                UPDATE blacklist
                SET removed_at = :now,
                    removed_by = :removed_by,
                    removal_reason = :removal_reason
                WHERE influencer_id = :influencer_id
                  AND removed_at IS NULL
                """
            ),
            {
                "now": now,
                "removed_by": removed_by_user_id,
                "removal_reason": removal_reason,
                "influencer_id": influencer_id,
            },
        )

        await self._db.execute(
            text(
                """
                UPDATE influencers
                SET blacklisted = FALSE,
                    blacklist_reason = NULL,
                    status = 'ACTIVE',
                    updated_at = :now
                WHERE id = :influencer_id
                """
            ),
            {"now": now, "influencer_id": influencer_id},
        )

        await self._db.flush()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def is_blacklisted(self, influencer_id: str) -> bool:
        """Return True if the influencer has an active blacklist entry (removed_at IS NULL)."""
        result = await self._db.execute(
            text(
                """
                SELECT 1 FROM blacklist
                WHERE influencer_id = :influencer_id
                  AND removed_at IS NULL
                LIMIT 1
                """
            ),
            {"influencer_id": influencer_id},
        )
        return result.first() is not None

    async def get_blacklist(self) -> List[Dict[str, Any]]:
        """Return all active blacklist entries."""
        result = await self._db.execute(
            text(
                """
                SELECT b.id, b.influencer_id, b.reason, b.added_by, b.added_at,
                       i.name AS influencer_name
                FROM blacklist b
                JOIN influencers i ON i.id = b.influencer_id
                WHERE b.removed_at IS NULL
                ORDER BY b.added_at DESC
                """
            )
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export_blacklist_csv(self) -> str:
        """Return a CSV string of all active blacklist entries."""
        entries = await self.get_blacklist()

        output = io.StringIO()
        fieldnames = ["id", "influencer_id", "influencer_name", "reason", "added_by", "added_at"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry)

        return output.getvalue()
