"""Unit tests untuk MonitorAgent."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.monitor_agent import CampaignReport, InfluencerReport, MonitorAgent
from app.integrations.tiktok_api import TikTokContent, VideoMetrics
from app.models.domain import ContentMetrics


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_content(
    video_id: str = "vid-1",
    user_id: str = "user-1",
    affiliate_links: Optional[List[str]] = None,
) -> TikTokContent:
    return TikTokContent(
        video_id=video_id,
        user_id=user_id,
        description="Test video",
        created_at=_now(),
        share_url=f"https://tiktok.com/@user/{video_id}",
        affiliate_links=affiliate_links or [],
    )


def _make_video_metrics(
    video_id: str = "vid-1",
    views: int = 1000,
    likes: int = 100,
    comments: int = 50,
    shares: int = 25,
) -> VideoMetrics:
    return VideoMetrics(
        video_id=video_id,
        views=views,
        likes=likes,
        comments=comments,
        shares=shares,
    )


def _make_tiktok_client(
    videos: Optional[List[TikTokContent]] = None,
    metrics: Optional[VideoMetrics] = None,
    raise_videos: Optional[Exception] = None,
    raise_metrics: Optional[Exception] = None,
) -> MagicMock:
    client = MagicMock()
    if raise_videos:
        client.get_user_videos = AsyncMock(side_effect=raise_videos)
    else:
        client.get_user_videos = AsyncMock(return_value=videos or [])
    if raise_metrics:
        client.get_video_metrics = AsyncMock(side_effect=raise_metrics)
    else:
        client.get_video_metrics = AsyncMock(return_value=metrics or _make_video_metrics())
    return client


def _make_db(
    influencer_rows: Optional[List[dict]] = None,
    metrics_rows: Optional[List[dict]] = None,
) -> AsyncMock:
    """Buat mock AsyncSession."""
    db = AsyncMock()
    db.flush = AsyncMock()

    inf_rows = influencer_rows or []
    met_rows = metrics_rows or []

    async def _execute(query, params=None):
        mock_result = MagicMock()
        query_str = str(query)

        if "invitations" in query_str and "tiktok_user_id" in query_str:
            # _get_campaign_influencers
            rows = [MagicMock(**{"__getitem__": lambda s, k: r[k]}) for r in inf_rows]
            for i, r in enumerate(inf_rows):
                rows[i].__getitem__ = lambda s, k, _r=r: _r[k]
            mock_mappings = MagicMock()
            mock_mappings.all = MagicMock(return_value=rows)
            mock_result.mappings = MagicMock(return_value=mock_mappings)
        elif "content_metrics" in query_str and "GROUP BY" in query_str:
            # generate_final_report
            rows = [MagicMock() for r in met_rows]
            for i, r in enumerate(met_rows):
                rows[i].__getitem__ = lambda s, k, _r=r: _r[k]
            mock_mappings = MagicMock()
            mock_mappings.all = MagicMock(return_value=rows)
            mock_result.mappings = MagicMock(return_value=mock_mappings)
        else:
            mock_mappings = MagicMock()
            mock_mappings.all = MagicMock(return_value=[])
            mock_result.mappings = MagicMock(return_value=mock_mappings)

        return mock_result

    db.execute = AsyncMock(side_effect=_execute)
    return db


def _make_agent(
    tiktok_client: Optional[MagicMock] = None,
    redis: Optional[object] = None,
) -> MonitorAgent:
    return MonitorAgent(
        tiktok_client=tiktok_client or _make_tiktok_client(),
        redis=redis,
    )


# ---------------------------------------------------------------------------
# Tests: check_new_content — metrik tidak null/negatif
# ---------------------------------------------------------------------------


class TestCheckNewContentMetrics:
    @pytest.mark.asyncio
    async def test_returns_list_of_content_metrics(self):
        content = _make_content("vid-1", affiliate_links=["https://affiliate.tiktok.com/link"])
        client = _make_tiktok_client(videos=[content], metrics=_make_video_metrics("vid-1"))
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-1", db)

        assert len(results) == 1
        assert isinstance(results[0], ContentMetrics)

    @pytest.mark.asyncio
    async def test_metrics_are_not_negative(self):
        """Metrik views, likes, comments, shares tidak boleh negatif."""
        content = _make_content("vid-1")
        # Simulasikan API mengembalikan nilai negatif (edge case)
        bad_metrics = VideoMetrics(video_id="vid-1", views=-10, likes=-5, comments=-1, shares=-2)
        client = _make_tiktok_client(videos=[content], metrics=bad_metrics)
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-1", db)

        assert len(results) == 1
        m = results[0]
        assert m.views >= 0
        assert m.likes >= 0
        assert m.comments >= 0
        assert m.shares >= 0

    @pytest.mark.asyncio
    async def test_metrics_are_not_null(self):
        """Metrik tidak boleh None — harus dikonversi ke 0."""
        content = _make_content("vid-1")
        null_metrics = VideoMetrics(video_id="vid-1", views=None, likes=None, comments=None, shares=None)
        client = _make_tiktok_client(videos=[content], metrics=null_metrics)
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-1", db)

        assert len(results) == 1
        m = results[0]
        assert m.views is not None
        assert m.likes is not None
        assert m.comments is not None
        assert m.shares is not None

    @pytest.mark.asyncio
    async def test_affiliate_link_detected_in_metrics(self):
        """Konten dengan tautan afiliasi valid harus has_valid_affiliate_link=True."""
        content = _make_content("vid-1", affiliate_links=["https://affiliate.tiktok.com/xyz"])
        client = _make_tiktok_client(videos=[content])
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-1", db)

        assert results[0].has_valid_affiliate_link is True

    @pytest.mark.asyncio
    async def test_no_affiliate_link_in_metrics(self):
        """Konten tanpa tautan afiliasi harus has_valid_affiliate_link=False."""
        content = _make_content("vid-1", affiliate_links=[])
        client = _make_tiktok_client(videos=[content])
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-1", db)

        assert results[0].has_valid_affiliate_link is False

    @pytest.mark.asyncio
    async def test_empty_influencer_list_returns_empty(self):
        agent = _make_agent()
        db = _make_db(influencer_rows=[])

        results = await agent.check_new_content("camp-empty", db)

        assert results == []

    @pytest.mark.asyncio
    async def test_tiktok_api_error_skips_influencer(self):
        """Error dari TikTok API tidak menghentikan proses — influencer dilewati."""
        client = _make_tiktok_client(raise_videos=Exception("API error"))
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-1", db)

        assert results == []

    @pytest.mark.asyncio
    async def test_metrics_api_error_skips_video(self):
        """Error saat ambil metrik video dilewati, video lain tetap diproses."""
        content = _make_content("vid-1")
        client = _make_tiktok_client(videos=[content], raise_metrics=Exception("metrics error"))
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-1", db)

        assert results == []

    @pytest.mark.asyncio
    async def test_non_compliant_content_publishes_redis_event(self):
        """Konten tidak compliant harus publish event ke Redis Streams."""
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock()

        content = _make_content("vid-1", affiliate_links=[])  # tidak ada link → non-compliant
        client = _make_tiktok_client(videos=[content])
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = MonitorAgent(tiktok_client=client, redis=redis_mock)

        await agent.check_new_content("camp-1", db)

        redis_mock.xadd.assert_called_once()
        call_args = redis_mock.xadd.call_args
        event_data = call_args[0][1]
        assert event_data["type"] == "content_non_compliant"
        assert event_data["campaign_id"] == "camp-1"

    @pytest.mark.asyncio
    async def test_compliant_content_does_not_publish_redis_event(self):
        """Konten compliant tidak boleh publish event non_compliant."""
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock()

        content = _make_content("vid-1", affiliate_links=["https://affiliate.tiktok.com/link"])
        client = _make_tiktok_client(videos=[content])
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = MonitorAgent(tiktok_client=client, redis=redis_mock)

        await agent.check_new_content("camp-1", db)

        redis_mock.xadd.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: validate_affiliate_link
# ---------------------------------------------------------------------------


class TestValidateAffiliateLink:
    @pytest.mark.asyncio
    async def test_returns_true_when_link_contains_campaign_id(self):
        agent = _make_agent()
        content = _make_content(affiliate_links=["https://example.com/ref?camp=camp-123"])

        result = await agent.validate_affiliate_link(content, "camp-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_for_known_affiliate_domain(self):
        agent = _make_agent()
        content = _make_content(affiliate_links=["https://affiliate.tiktok.com/product/123"])

        result = await agent.validate_affiliate_link(content, "camp-xyz")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_for_shopee_domain(self):
        agent = _make_agent()
        content = _make_content(affiliate_links=["https://shopee.co.id/product/abc"])

        result = await agent.validate_affiliate_link(content, "camp-xyz")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_for_tokopedia_domain(self):
        agent = _make_agent()
        content = _make_content(affiliate_links=["https://tokopedia.com/product/abc"])

        result = await agent.validate_affiliate_link(content, "camp-xyz")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_links(self):
        agent = _make_agent()
        content = _make_content(affiliate_links=[])

        result = await agent.validate_affiliate_link(content, "camp-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_domain(self):
        agent = _make_agent()
        content = _make_content(affiliate_links=["https://random-site.com/product"])

        result = await agent.validate_affiliate_link(content, "camp-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_empty_link_strings(self):
        agent = _make_agent()
        content = _make_content(affiliate_links=["", "  "])

        result = await agent.validate_affiliate_link(content, "camp-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_deterministic_same_input_same_output(self):
        """Fungsi harus deterministik: input sama → output sama."""
        agent = _make_agent()
        content = _make_content(affiliate_links=["https://affiliate.tiktok.com/link"])

        result1 = await agent.validate_affiliate_link(content, "camp-1")
        result2 = await agent.validate_affiliate_link(content, "camp-1")

        assert result1 == result2

    @pytest.mark.asyncio
    async def test_multiple_links_one_valid_returns_true(self):
        """Jika salah satu dari beberapa link valid, kembalikan True."""
        agent = _make_agent()
        content = _make_content(
            affiliate_links=[
                "https://random.com/link",
                "https://affiliate.tiktok.com/valid",
            ]
        )

        result = await agent.validate_affiliate_link(content, "camp-xyz")

        assert result is True


# ---------------------------------------------------------------------------
# Tests: generate_final_report
# ---------------------------------------------------------------------------


class TestGenerateFinalReport:
    @pytest.mark.asyncio
    async def test_returns_campaign_report(self):
        db = _make_db(
            metrics_rows=[
                {"influencer_id": "inf-1", "total_views": 5000, "total_gmv": 1000.0, "avg_conversion_rate": 0.05},
            ]
        )
        agent = _make_agent()

        report = await agent.generate_final_report("camp-1", db)

        assert isinstance(report, CampaignReport)
        assert report.campaign_id == "camp-1"

    @pytest.mark.asyncio
    async def test_aggregation_totals_are_accurate(self):
        db = _make_db(
            metrics_rows=[
                {"influencer_id": "inf-1", "total_views": 3000, "total_gmv": 500.0, "avg_conversion_rate": 0.04},
                {"influencer_id": "inf-2", "total_views": 7000, "total_gmv": 1500.0, "avg_conversion_rate": 0.06},
            ]
        )
        agent = _make_agent()

        report = await agent.generate_final_report("camp-1", db)

        assert report.total_views == 10000
        assert report.total_gmv == 2000.0
        assert abs(report.total_conversion_rate - 0.05) < 1e-9

    @pytest.mark.asyncio
    async def test_report_includes_all_influencers(self):
        """Laporan harus mencakup semua influencer yang berpartisipasi."""
        db = _make_db(
            metrics_rows=[
                {"influencer_id": "inf-1", "total_views": 1000, "total_gmv": 100.0, "avg_conversion_rate": 0.01},
                {"influencer_id": "inf-2", "total_views": 2000, "total_gmv": 200.0, "avg_conversion_rate": 0.02},
                {"influencer_id": "inf-3", "total_views": 3000, "total_gmv": 300.0, "avg_conversion_rate": 0.03},
            ]
        )
        agent = _make_agent()

        report = await agent.generate_final_report("camp-1", db)

        influencer_ids = {r.influencer_id for r in report.influencer_reports}
        assert influencer_ids == {"inf-1", "inf-2", "inf-3"}
        assert len(report.influencer_reports) == 3

    @pytest.mark.asyncio
    async def test_empty_campaign_returns_zero_totals(self):
        db = _make_db(metrics_rows=[])
        agent = _make_agent()

        report = await agent.generate_final_report("camp-empty", db)

        assert report.total_views == 0
        assert report.total_gmv == 0.0
        assert report.total_conversion_rate == 0.0
        assert report.influencer_reports == []

    @pytest.mark.asyncio
    async def test_influencer_report_fields_correct(self):
        db = _make_db(
            metrics_rows=[
                {"influencer_id": "inf-1", "total_views": 5000, "total_gmv": 750.0, "avg_conversion_rate": 0.07},
            ]
        )
        agent = _make_agent()

        report = await agent.generate_final_report("camp-1", db)

        inf_report = report.influencer_reports[0]
        assert isinstance(inf_report, InfluencerReport)
        assert inf_report.influencer_id == "inf-1"
        assert inf_report.total_views == 5000
        assert inf_report.total_gmv == 750.0
        assert abs(inf_report.conversion_rate - 0.07) < 1e-9


# ---------------------------------------------------------------------------
# Tests: start_monitoring / stop_monitoring
# ---------------------------------------------------------------------------


class TestStartStopMonitoring:
    @pytest.mark.asyncio
    async def test_start_monitoring_creates_task(self):
        agent = _make_agent()
        db = _make_db()

        await agent.start_monitoring("camp-1", db, _interval_seconds=9999)

        assert "camp-1" in agent._monitoring_tasks
        task = agent._monitoring_tasks["camp-1"]
        assert isinstance(task, asyncio.Task)
        assert not task.done()

        # Cleanup
        agent.stop_monitoring("camp-1")

    @pytest.mark.asyncio
    async def test_stop_monitoring_cancels_task(self):
        agent = _make_agent()
        db = _make_db()

        await agent.start_monitoring("camp-1", db, _interval_seconds=9999)
        task = agent._monitoring_tasks["camp-1"]

        agent.stop_monitoring("camp-1")

        # Yield control so the event loop can process the cancellation
        await asyncio.sleep(0)

        assert task.cancelled() or task.done() or task.cancelling() > 0
        assert "camp-1" not in agent._monitoring_tasks

    @pytest.mark.asyncio
    async def test_start_monitoring_idempotent(self):
        """Memanggil start_monitoring dua kali tidak membuat task duplikat."""
        agent = _make_agent()
        db = _make_db()

        await agent.start_monitoring("camp-1", db, _interval_seconds=9999)
        task1 = agent._monitoring_tasks["camp-1"]

        await agent.start_monitoring("camp-1", db, _interval_seconds=9999)
        task2 = agent._monitoring_tasks["camp-1"]

        assert task1 is task2  # task yang sama, tidak dibuat ulang

        # Cleanup
        agent.stop_monitoring("camp-1")

    @pytest.mark.asyncio
    async def test_stop_monitoring_nonexistent_campaign_no_error(self):
        """stop_monitoring untuk campaign yang tidak ada tidak raise error."""
        agent = _make_agent()

        # Tidak boleh raise exception
        agent.stop_monitoring("nonexistent-campaign")

    @pytest.mark.asyncio
    async def test_multiple_campaigns_independent_tasks(self):
        """Setiap kampanye memiliki task monitoring independen."""
        agent = _make_agent()
        db = _make_db()

        await agent.start_monitoring("camp-1", db, _interval_seconds=9999)
        await agent.start_monitoring("camp-2", db, _interval_seconds=9999)

        assert "camp-1" in agent._monitoring_tasks
        assert "camp-2" in agent._monitoring_tasks
        assert agent._monitoring_tasks["camp-1"] is not agent._monitoring_tasks["camp-2"]

        # Cleanup
        agent.stop_monitoring("camp-1")
        agent.stop_monitoring("camp-2")

    @pytest.mark.asyncio
    async def test_stop_one_does_not_affect_other(self):
        """Menghentikan satu kampanye tidak mempengaruhi kampanye lain."""
        agent = _make_agent()
        db = _make_db()

        await agent.start_monitoring("camp-1", db, _interval_seconds=9999)
        await agent.start_monitoring("camp-2", db, _interval_seconds=9999)

        agent.stop_monitoring("camp-1")

        assert "camp-1" not in agent._monitoring_tasks
        assert "camp-2" in agent._monitoring_tasks
        assert not agent._monitoring_tasks["camp-2"].done()

        # Cleanup
        agent.stop_monitoring("camp-2")


# ---------------------------------------------------------------------------
# Tests: Edge Cases (Task 10.3)
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case eksplisit sesuai task 10.3:
    - kampanye tanpa konten
    - konten tanpa tautan afiliasi
    - metrik dengan nilai nol
    """

    # --- Kampanye tanpa konten ---

    @pytest.mark.asyncio
    async def test_campaign_with_no_content_returns_empty_list(self):
        """Kampanye tanpa konten: TikTok API mengembalikan list kosong."""
        client = _make_tiktok_client(videos=[])
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-no-content", db)

        assert results == []

    @pytest.mark.asyncio
    async def test_campaign_with_no_content_final_report_has_zero_totals(self):
        """Laporan akhir kampanye tanpa konten harus mengembalikan nol di semua total."""
        db = _make_db(metrics_rows=[])
        agent = _make_agent()

        report = await agent.generate_final_report("camp-no-content", db)

        assert report.total_views == 0
        assert report.total_gmv == 0.0
        assert report.total_conversion_rate == 0.0
        assert report.influencer_reports == []

    @pytest.mark.asyncio
    async def test_campaign_with_no_influencers_returns_empty(self):
        """Kampanye tanpa influencer terdaftar tidak menghasilkan metrik apapun."""
        client = _make_tiktok_client()
        db = _make_db(influencer_rows=[])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-no-influencers", db)

        assert results == []
        client.get_user_videos.assert_not_called()

    # --- Konten tanpa tautan afiliasi ---

    @pytest.mark.asyncio
    async def test_content_without_affiliate_link_is_not_compliant(self):
        """Konten tanpa tautan afiliasi harus ditandai is_compliant=False."""
        content = _make_content("vid-no-link", affiliate_links=[])
        client = _make_tiktok_client(videos=[content])
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-1", db)

        assert len(results) == 1
        assert results[0].has_valid_affiliate_link is False
        assert results[0].is_compliant is False

    @pytest.mark.asyncio
    async def test_content_without_affiliate_link_triggers_notification(self):
        """Konten tanpa tautan afiliasi harus memicu event non_compliant ke Redis."""
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock()

        content = _make_content("vid-no-link", affiliate_links=[])
        client = _make_tiktok_client(videos=[content])
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = MonitorAgent(tiktok_client=client, redis=redis_mock)

        await agent.check_new_content("camp-1", db)

        redis_mock.xadd.assert_called_once()
        event_data = redis_mock.xadd.call_args[0][1]
        assert event_data["type"] == "content_non_compliant"
        assert event_data["influencer_id"] == "inf-1"
        assert event_data["video_id"] == "vid-no-link"

    @pytest.mark.asyncio
    async def test_validate_affiliate_link_returns_false_for_no_links(self):
        """validate_affiliate_link harus False untuk konten tanpa link."""
        agent = _make_agent()
        content = _make_content(affiliate_links=[])

        result = await agent.validate_affiliate_link(content, "camp-1")

        assert result is False

    @pytest.mark.asyncio
    async def test_validate_affiliate_link_returns_false_for_none_links(self):
        """validate_affiliate_link harus False untuk list link yang berisi None/empty."""
        agent = _make_agent()
        content = _make_content(affiliate_links=["", None])

        result = await agent.validate_affiliate_link(content, "camp-1")

        assert result is False

    # --- Metrik dengan nilai nol ---

    @pytest.mark.asyncio
    async def test_zero_metrics_are_stored_correctly(self):
        """Metrik dengan nilai nol (bukan negatif) harus disimpan apa adanya."""
        content = _make_content("vid-zero")
        zero_metrics = _make_video_metrics("vid-zero", views=0, likes=0, comments=0, shares=0)
        client = _make_tiktok_client(videos=[content], metrics=zero_metrics)
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-1", db)

        assert len(results) == 1
        m = results[0]
        assert m.views == 0
        assert m.likes == 0
        assert m.comments == 0
        assert m.shares == 0

    @pytest.mark.asyncio
    async def test_zero_metrics_are_valid_not_filtered_out(self):
        """Metrik nol adalah valid — konten tetap diproses dan disimpan."""
        content = _make_content("vid-zero")
        zero_metrics = _make_video_metrics("vid-zero", views=0, likes=0, comments=0, shares=0)
        client = _make_tiktok_client(videos=[content], metrics=zero_metrics)
        db = _make_db(influencer_rows=[{"influencer_id": "inf-1", "tiktok_user_id": "tt-1"}])
        agent = _make_agent(tiktok_client=client)

        results = await agent.check_new_content("camp-1", db)

        # Konten dengan metrik nol tetap harus masuk ke hasil
        assert len(results) == 1
        db.execute.assert_called()  # _save_content_metrics dipanggil

    @pytest.mark.asyncio
    async def test_zero_metrics_in_final_report(self):
        """Laporan akhir dengan influencer yang memiliki metrik nol harus tetap muncul."""
        db = _make_db(
            metrics_rows=[
                {"influencer_id": "inf-zero", "total_views": 0, "total_gmv": 0.0, "avg_conversion_rate": 0.0},
            ]
        )
        agent = _make_agent()

        report = await agent.generate_final_report("camp-1", db)

        assert len(report.influencer_reports) == 1
        inf_report = report.influencer_reports[0]
        assert inf_report.influencer_id == "inf-zero"
        assert inf_report.total_views == 0
        assert inf_report.total_gmv == 0.0
        assert inf_report.conversion_rate == 0.0

    @pytest.mark.asyncio
    async def test_mixed_zero_and_nonzero_metrics(self):
        """Campuran influencer dengan metrik nol dan non-nol harus diagregasi dengan benar."""
        db = _make_db(
            metrics_rows=[
                {"influencer_id": "inf-zero", "total_views": 0, "total_gmv": 0.0, "avg_conversion_rate": 0.0},
                {"influencer_id": "inf-active", "total_views": 5000, "total_gmv": 800.0, "avg_conversion_rate": 0.08},
            ]
        )
        agent = _make_agent()

        report = await agent.generate_final_report("camp-1", db)

        assert report.total_views == 5000
        assert report.total_gmv == 800.0
        assert len(report.influencer_reports) == 2
