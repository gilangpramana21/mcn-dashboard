"""Template Service — CRUD, versioning, and preview for message templates."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import TemplateInUseError, ValidationError
from app.models.domain import MessageTemplate

_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _extract_variables(content: str) -> List[str]:
    """Return a deduplicated, ordered list of variable names found in *content*."""
    seen: dict[str, None] = {}
    for name in _VAR_PATTERN.findall(content):
        seen[name] = None
    return list(seen)


def _row_to_template(row: Any) -> MessageTemplate:
    default_values: Dict[str, str] = row["default_values"]
    if isinstance(default_values, str):
        default_values = json.loads(default_values)

    variables = row["variables"]
    if isinstance(variables, str):
        variables = json.loads(variables)

    campaign_ids = row["campaign_ids"]
    if isinstance(campaign_ids, str):
        campaign_ids = json.loads(campaign_ids)
    if campaign_ids is None:
        campaign_ids = []

    return MessageTemplate(
        id=str(row["id"]),
        name=row["name"],
        content=row["content"],
        variables=list(variables),
        default_values=dict(default_values),
        version=int(row["version"]),
        is_active=bool(row["is_active"]),
        campaign_ids=[str(c) for c in campaign_ids],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class TemplateService:
    """Handles creation, retrieval, update, deletion, and preview of message templates."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(
        self,
        name: str,
        content: str,
        default_values: Dict[str, str],
        message_type: str = "campaign_invitation",
        channel: str = "whatsapp",
        wa_category: Optional[str] = None,
    ) -> MessageTemplate:
        """Parse variables from *content*, validate all have defaults, then INSERT."""
        variables = _extract_variables(content)
        missing = [v for v in variables if v not in default_values]
        if missing:
            raise ValidationError(
                f"Variabel berikut tidak memiliki nilai default: {', '.join(missing)}"
            )

        template_id = str(uuid.uuid4())
        now = _now_utc()

        await self._db.execute(
            text(
                """
                INSERT INTO message_templates
                    (id, name, content, variables, default_values, version,
                     is_active, campaign_ids, message_type, channel, wa_category, created_at, updated_at)
                VALUES
                    (:id, :name, :content, :variables, :default_values::jsonb,
                     1, TRUE, '{}', :message_type, :channel, :wa_category, :now, :now)
                """
            ),
            {
                "id": template_id, "name": name, "content": content,
                "variables": variables, "default_values": json.dumps(default_values),
                "message_type": message_type, "channel": channel,
                "wa_category": wa_category, "now": now,
            },
        )
        await self._db.flush()

        t = MessageTemplate(
            id=template_id, name=name, content=content, variables=variables,
            default_values=default_values, version=1, is_active=True,
            campaign_ids=[], created_at=now, updated_at=now,
        )
        t.message_type = message_type  # type: ignore
        t.channel = channel  # type: ignore
        t.wa_category = wa_category  # type: ignore
        return t

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------

    async def get(self, template_id: str) -> MessageTemplate:
        """Fetch a template by id. Raises ValidationError if not found."""
        result = await self._db.execute(
            text("SELECT * FROM message_templates WHERE id = :id"),
            {"id": template_id},
        )
        row = result.mappings().first()
        if row is None:
            raise ValidationError(f"Template dengan id '{template_id}' tidak ditemukan.")
        return _row_to_template(row)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update(
        self,
        template_id: str,
        content: Optional[str] = None,
        default_values: Optional[Dict[str, str]] = None,
        wa_category: Optional[str] = None,
    ) -> MessageTemplate:
        """Save old version to template_versions, then update the template.

        Raises ValidationError if the template is not found or variable validation fails.
        """
        current = await self.get(template_id)
        now = _now_utc()

        # Persist old version
        await self._db.execute(
            text(
                """
                INSERT INTO template_versions
                    (id, template_id, version, content, variables, default_values, saved_at)
                VALUES
                    (:id, :template_id, :version, :content, :variables,
                     :default_values::jsonb, :saved_at)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "template_id": template_id,
                "version": current.version,
                "content": current.content,
                "variables": current.variables,
                "default_values": json.dumps(current.default_values),
                "saved_at": now,
            },
        )

        new_content = content if content is not None else current.content
        new_defaults = default_values if default_values is not None else current.default_values

        variables = _extract_variables(new_content)
        missing = [v for v in variables if v not in new_defaults]
        if missing:
            raise ValidationError(
                f"Variabel berikut tidak memiliki nilai default: {', '.join(missing)}"
            )

        new_version = current.version + 1

        await self._db.execute(
            text(
                """
                UPDATE message_templates
                SET content = :content,
                    variables = :variables,
                    default_values = :default_values::jsonb,
                    version = :version,
                    wa_category = COALESCE(:wa_category, wa_category),
                    updated_at = :now
                WHERE id = :id
                """
            ),
            {
                "content": new_content,
                "variables": variables,
                "default_values": json.dumps(new_defaults),
                "version": new_version,
                "wa_category": wa_category,
                "now": now,
                "id": template_id,
            },
        )
        await self._db.flush()

        return MessageTemplate(
            id=template_id,
            name=current.name,
            content=new_content,
            variables=variables,
            default_values=new_defaults,
            version=new_version,
            is_active=current.is_active,
            campaign_ids=current.campaign_ids,
            created_at=current.created_at,
            updated_at=now,
        )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, template_id: str) -> None:
        """Delete a template. Raises TemplateInUseError if used by active campaigns."""
        template = await self.get(template_id)

        if template.campaign_ids:
            raise TemplateInUseError(
                f"Template '{template_id}' sedang digunakan oleh kampanye aktif: "
                f"{', '.join(template.campaign_ids)}"
            )

        await self._db.execute(
            text("DELETE FROM template_versions WHERE template_id = :id"),
            {"id": template_id},
        )
        await self._db.execute(
            text("DELETE FROM message_templates WHERE id = :id"),
            {"id": template_id},
        )
        await self._db.flush()

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    async def preview(
        self,
        template_id: str,
        influencer_data: Dict[str, str],
    ) -> str:
        """Substitute all {{variable}} placeholders and return the rendered message.

        Priority: influencer_data > default_values.
        Raises ValidationError if any placeholder remains after substitution.
        """
        template = await self.get(template_id)

        merged = {**template.default_values, **influencer_data}

        def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
            key = match.group(1)
            return merged.get(key, match.group(0))

        rendered = _VAR_PATTERN.sub(_replace, template.content)

        remaining = _VAR_PATTERN.findall(rendered)
        if remaining:
            raise ValidationError(
                f"Placeholder berikut belum tersubstitusi: {', '.join(remaining)}"
            )

        return rendered
