"""Unit tests for NotificationService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.notification_service import Notification, NotificationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service() -> NotificationService:
    return NotificationService()


# ---------------------------------------------------------------------------
# Tests: check_and_notify
# ---------------------------------------------------------------------------


class TestCheckAndNotify:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        service = _make_service()
        result = await service.check_and_notify("camp-1", {}, {})
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_no_notifications_when_no_thresholds(self):
        service = _make_service()
        metrics = {"views": 10_000, "gmv": 500_000.0}
        result = await service.check_and_notify("camp-1", metrics, {})
        assert result == []

    @pytest.mark.asyncio
    async def test_no_notifications_when_metrics_below_threshold(self):
        service = _make_service()
        metrics = {"views": 5_000}
        thresholds = {"views": 10_000.0}
        result = await service.check_and_notify("camp-1", metrics, thresholds)
        assert result == []

    @pytest.mark.asyncio
    async def test_no_notifications_when_metric_equals_threshold(self):
        service = _make_service()
        metrics = {"views": 10_000}
        thresholds = {"views": 10_000.0}
        result = await service.check_and_notify("camp-1", metrics, thresholds)
        assert result == []

    @pytest.mark.asyncio
    async def test_notification_when_metric_exceeds_threshold(self):
        service = _make_service()
        metrics = {"views": 15_000}
        thresholds = {"views": 10_000.0}
        result = await service.check_and_notify("camp-1", metrics, thresholds)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_notification_has_correct_fields(self):
        service = _make_service()
        metrics = {"gmv": 600_000.0}
        thresholds = {"gmv": 500_000.0}
        result = await service.check_and_notify("camp-99", metrics, thresholds)

        assert len(result) == 1
        notif = result[0]
        assert isinstance(notif, Notification)
        assert notif.campaign_id == "camp-99"
        assert notif.metric_name == "gmv"
        assert notif.current_value == 600_000.0
        assert notif.threshold_value == 500_000.0
        assert "gmv" in notif.message
        assert "camp-99" in notif.message

    @pytest.mark.asyncio
    async def test_multiple_metrics_only_exceeding_ones_notified(self):
        service = _make_service()
        metrics = {"views": 20_000, "gmv": 100_000.0, "conversion_rate": 0.03}
        thresholds = {"views": 10_000.0, "gmv": 500_000.0, "conversion_rate": 0.05}
        result = await service.check_and_notify("camp-1", metrics, thresholds)

        # Only "views" exceeds its threshold
        assert len(result) == 1
        assert result[0].metric_name == "views"

    @pytest.mark.asyncio
    async def test_all_metrics_exceeding_all_notified(self):
        service = _make_service()
        metrics = {"views": 20_000, "gmv": 600_000.0}
        thresholds = {"views": 10_000.0, "gmv": 500_000.0}
        result = await service.check_and_notify("camp-1", metrics, thresholds)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_missing_metric_in_metrics_dict_skipped(self):
        service = _make_service()
        metrics = {}  # no metrics provided
        thresholds = {"views": 10_000.0}
        result = await service.check_and_notify("camp-1", metrics, thresholds)
        assert result == []

    @pytest.mark.asyncio
    async def test_redis_publish_called_when_threshold_exceeded(self):
        service = _make_service()
        redis = AsyncMock()
        redis.publish = AsyncMock()

        metrics = {"views": 20_000}
        thresholds = {"views": 10_000.0}
        result = await service.check_and_notify("camp-1", metrics, thresholds, redis=redis)

        assert len(result) == 1
        redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_not_called_when_no_threshold_exceeded(self):
        service = _make_service()
        redis = AsyncMock()
        redis.publish = AsyncMock()

        metrics = {"views": 5_000}
        thresholds = {"views": 10_000.0}
        await service.check_and_notify("camp-1", metrics, thresholds, redis=redis)

        redis.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_redis_error_does_not_raise(self):
        service = _make_service()
        redis = AsyncMock()
        redis.publish = AsyncMock(side_effect=Exception("Redis down"))

        metrics = {"views": 20_000}
        thresholds = {"views": 10_000.0}
        # Should not raise even if Redis fails
        result = await service.check_and_notify("camp-1", metrics, thresholds, redis=redis)
        assert len(result) == 1
