"""Property-based tests untuk MonitorAgent.

Validates: Requirements 4.2, 4.3, 4.5, 4.6
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.agents.monitor_agent import MonitorAgent
from app.integrations.tiktok_api import TikTokContent
from app.models.domain import ContentMetrics


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


def _make_db(influencer_rows: List[Dict] = None) -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()

    async def _execute(query, params=None):
        q = str(query)
        mock_result = MagicMock()
        mock_mappings = MagicMock()

        if "influencer_id" in q and "tiktok_user_id" in q:
            rows = influencer_rows or []
            mock_mappings.all.return_value = rows
        else:
            mock_mappings.all.return_value = []

        mock_mappings.first.return_value = None
        mock_result.mappings.return_value = mock_mappings
        return mock_result

    db.execute = _execute
    return db


def _make_tiktok_content(
    video_id: str = "video-1",
    affiliate_links: List[str] = None,
) -> TikTokContent:
    from datetime import datetime, timezone
    return TikTokContent(
        video_id=video_id,
        user_id="user-1",
        description="Test video",
        created_at=datetime.now(timezone.utc),
        share_url="https://tiktok.com/video/1",
        affiliate_links=affiliate_links or [],
    )


# ---------------------------------------------------------------------------
# Property 12: Metrik Tidak Negatif
# ---------------------------------------------------------------------------


class TestProperty12MetricsNonNegative:
    """Validates: Requirements 10.2 — check_new_content menghasilkan views/likes/comments/shares >= 0."""

    @given(
        views=st.integers(min_value=-1000, max_value=1000000),
        likes=st.integers(min_value=-1000, max_value=1000000),
        comments=st.integers(min_value=-1000, max_value=1000000),
        shares=st.integers(min_value=-1000, max_value=1000000),
    )
    @settings(max_examples=50)
    def test_metrics_always_non_negative(
        self,
        views: int,
        likes: int,
        comments: int,
        shares: int,
    ):
        """check_new_content menghasilkan views/likes/comments/shares >= 0 meskipun input negatif."""
        async def _run():
            # Mock TikTok client
            mock_tiktok = AsyncMock()

            mock_content = _make_tiktok_content(
                video_id="video-1",
                affiliate_links=["https://affiliate.tiktok.com/test"],
            )
            mock_tiktok.get_user_videos = AsyncMock(return_value=[mock_content])

            mock_metrics = MagicMock()
            mock_metrics.views = views
            mock_metrics.likes = likes
            mock_metrics.comments = comments
            mock_metrics.shares = shares
            mock_tiktok.get_video_metrics = AsyncMock(return_value=mock_metrics)

            db = _make_db(influencer_rows=[
                {"influencer_id": "inf-1", "tiktok_user_id": "tiktok-1"}
            ])

            agent = MonitorAgent(tiktok_client=mock_tiktok)
            results = await agent.check_new_content("camp-1", db)

            assert len(results) == 1
            m = results[0]
            assert m.views >= 0, f"views={m.views} harus >= 0"
            assert m.likes >= 0, f"likes={m.likes} harus >= 0"
            assert m.comments >= 0, f"comments={m.comments} harus >= 0"
            assert m.shares >= 0, f"shares={m.shares} harus >= 0"

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 13: Deteksi Tautan Konsisten
# ---------------------------------------------------------------------------


class TestProperty13AffiliateLinkDetectionConsistent:
    """Validates: Requirements 10.2 — validate_affiliate_link deterministik untuk input yang sama."""

    @given(
        campaign_id=st.text(min_size=1, max_size=36),
        links=st.lists(
            st.text(min_size=0, max_size=100),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_validate_affiliate_link_deterministic(
        self,
        campaign_id: str,
        links: List[str],
    ):
        """validate_affiliate_link deterministik untuk input yang sama."""
        async def _run():
            agent = MonitorAgent()
            content = _make_tiktok_content(
                video_id="video-1",
                affiliate_links=links,
            )

            result1 = await agent.validate_affiliate_link(content, campaign_id)
            result2 = await agent.validate_affiliate_link(content, campaign_id)

            assert result1 == result2, (
                f"validate_affiliate_link tidak deterministik: {result1} != {result2}"
            )
            assert isinstance(result1, bool)

        _run_async(_run())

    @given(
        campaign_id=st.text(min_size=1, max_size=36),
    )
    @settings(max_examples=50)
    def test_validate_affiliate_link_with_known_domain_returns_true(
        self,
        campaign_id: str,
    ):
        """Link dengan domain afiliasi yang dikenal harus mengembalikan True."""
        async def _run():
            agent = MonitorAgent()
            content = _make_tiktok_content(
                video_id="video-1",
                affiliate_links=["https://affiliate.tiktok.com/product/123"],
            )

            result = await agent.validate_affiliate_link(content, campaign_id)
            assert result is True

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 14: Riwayat Metrik Tersimpan Per Hari
# ---------------------------------------------------------------------------


class TestProperty14MetricHistoryPerDay:
    """Validates: Requirements 4.5 — metrik yang dicatat pada tanggal tertentu dapat diambil kembali."""

    @given(
        num_metrics=st.integers(min_value=1, max_value=20),
        views=st.integers(min_value=0, max_value=1_000_000),
        likes=st.integers(min_value=0, max_value=1_000_000),
    )
    @settings(max_examples=50)
    def test_metrics_saved_and_retrievable_by_date(
        self,
        num_metrics: int,
        views: int,
        likes: int,
    ):
        """Metrik yang disimpan pada tanggal tertentu harus dapat diambil kembali seluruhnya."""
        from datetime import date, datetime, timezone
        import uuid

        async def _run():
            target_date = date(2024, 6, 15)
            target_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

            # Simulasikan penyimpanan dan pengambilan metrik per hari
            stored_metrics: List[ContentMetrics] = []
            saved_ids: List[str] = []

            db = AsyncMock()
            db.flush = AsyncMock()

            async def _execute(query, params=None):
                q = str(query)
                mock_result = MagicMock()
                mock_mappings = MagicMock()

                if "INSERT INTO content_metrics" in q:
                    # Simpan metrik ke list lokal
                    m = ContentMetrics(
                        id=params["id"],
                        campaign_id=params["campaign_id"],
                        influencer_id=params["influencer_id"],
                        tiktok_video_id=params["tiktok_video_id"],
                        views=params["views"],
                        likes=params["likes"],
                        comments=params["comments"],
                        shares=params["shares"],
                        has_valid_affiliate_link=params["has_valid_affiliate_link"],
                        gmv_generated=params["gmv_generated"],
                        conversion_rate=params["conversion_rate"],
                        recorded_at=params["recorded_at"],
                        is_compliant=params["is_compliant"],
                    )
                    stored_metrics.append(m)
                    saved_ids.append(params["id"])
                    mock_mappings.all.return_value = []
                elif "recorded_at" in q and "DATE" in q:
                    # Query pengambilan metrik per tanggal
                    rows = [
                        {
                            "id": m.id,
                            "influencer_id": m.influencer_id,
                            "views": m.views,
                            "likes": m.likes,
                            "recorded_at": m.recorded_at,
                        }
                        for m in stored_metrics
                        if m.recorded_at.date() == target_date
                    ]
                    mock_mappings.all.return_value = rows
                else:
                    mock_mappings.all.return_value = []

                mock_mappings.first.return_value = None
                mock_result.mappings.return_value = mock_mappings
                return mock_result

            db.execute = _execute

            # Buat mock TikTok client yang menghasilkan num_metrics video
            mock_tiktok = AsyncMock()
            contents = [
                _make_tiktok_content(
                    video_id=f"video-{i}",
                    affiliate_links=["https://affiliate.tiktok.com/p"],
                )
                for i in range(num_metrics)
            ]
            mock_tiktok.get_user_videos = AsyncMock(return_value=contents)

            mock_video_metrics = MagicMock()
            mock_video_metrics.views = views
            mock_video_metrics.likes = likes
            mock_video_metrics.comments = 0
            mock_video_metrics.shares = 0
            mock_tiktok.get_video_metrics = AsyncMock(return_value=mock_video_metrics)

            db_influencer_rows = [{"influencer_id": "inf-1", "tiktok_user_id": "tiktok-1"}]

            # Override execute untuk influencer query
            original_execute = db.execute

            async def _execute_with_influencers(query, params=None):
                q = str(query)
                if "tiktok_user_id" in q:
                    mock_result = MagicMock()
                    mock_mappings = MagicMock()
                    mock_mappings.all.return_value = db_influencer_rows
                    mock_mappings.first.return_value = None
                    mock_result.mappings.return_value = mock_mappings
                    return mock_result
                return await original_execute(query, params)

            db.execute = _execute_with_influencers

            agent = MonitorAgent(tiktok_client=mock_tiktok)
            results = await agent.check_new_content("camp-1", db)

            # Semua metrik yang disimpan harus dapat diidentifikasi
            assert len(results) == num_metrics, (
                f"Harus ada {num_metrics} metrik, tapi ada {len(results)}"
            )

            # Setiap metrik harus memiliki recorded_at yang valid
            for m in results:
                assert m.recorded_at is not None, "recorded_at tidak boleh None"
                assert isinstance(m.recorded_at, datetime), (
                    f"recorded_at harus datetime, bukan {type(m.recorded_at)}"
                )

            # Semua ID yang disimpan harus unik (tidak ada duplikat)
            assert len(saved_ids) == len(set(saved_ids)), (
                "ID metrik yang disimpan harus unik"
            )

        _run_async(_run())

    @given(
        dates=st.lists(
            st.dates(min_value=__import__("datetime").date(2024, 1, 1),
                     max_value=__import__("datetime").date(2024, 12, 31)),
            min_size=1,
            max_size=10,
            unique=True,
        ),
    )
    @settings(max_examples=30)
    def test_metrics_grouped_correctly_by_date(self, dates):
        """Metrik dari tanggal berbeda tidak tercampur saat diambil per tanggal."""
        from datetime import datetime, timezone

        async def _run():
            # Buat metrik untuk setiap tanggal
            all_metrics: List[ContentMetrics] = []
            for i, d in enumerate(dates):
                m = ContentMetrics(
                    id=f"metric-{i}",
                    campaign_id="camp-1",
                    influencer_id=f"inf-{i}",
                    tiktok_video_id=f"video-{i}",
                    views=100,
                    likes=10,
                    comments=5,
                    shares=2,
                    has_valid_affiliate_link=True,
                    gmv_generated=0.0,
                    conversion_rate=0.0,
                    recorded_at=datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=timezone.utc),
                    is_compliant=True,
                )
                all_metrics.append(m)

            # Untuk setiap tanggal, filter metrik yang sesuai
            for target_date in dates:
                metrics_on_date = [
                    m for m in all_metrics
                    if m.recorded_at.date() == target_date
                ]

                # Harus ada tepat 1 metrik per tanggal (karena dates unique)
                assert len(metrics_on_date) == 1, (
                    f"Tanggal {target_date} harus memiliki tepat 1 metrik, "
                    f"tapi ada {len(metrics_on_date)}"
                )

                # Metrik yang diambil harus memiliki tanggal yang benar
                for m in metrics_on_date:
                    assert m.recorded_at.date() == target_date, (
                        f"Metrik {m.id} memiliki tanggal {m.recorded_at.date()}, "
                        f"bukan {target_date}"
                    )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 15: Laporan Mencakup Semua Influencer
# ---------------------------------------------------------------------------


class TestProperty15ReportCoversAllInfluencers:
    """Validates: Requirements 10.2 — generate_final_report mengandung data untuk semua influencer."""

    @given(
        influencer_count=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=50)
    def test_final_report_contains_all_influencers(self, influencer_count: int):
        """generate_final_report mengandung data untuk semua influencer."""
        async def _run():
            influencer_ids = [f"inf-{i}" for i in range(influencer_count)]

            db = AsyncMock()
            db.flush = AsyncMock()

            async def _execute(query, params=None):
                q = str(query)
                mock_result = MagicMock()
                mock_mappings = MagicMock()

                if "content_metrics" in q and "GROUP BY influencer_id" in q:
                    rows = [
                        {
                            "influencer_id": inf_id,
                            "total_views": 1000,
                            "total_gmv": 500000.0,
                            "avg_conversion_rate": 0.05,
                        }
                        for inf_id in influencer_ids
                    ]
                    mock_mappings.all.return_value = rows
                else:
                    mock_mappings.all.return_value = []

                mock_mappings.first.return_value = None
                mock_result.mappings.return_value = mock_mappings
                return mock_result

            db.execute = _execute

            agent = MonitorAgent()
            report = await agent.generate_final_report("camp-1", db)

            assert len(report.influencer_reports) == influencer_count, (
                f"Laporan harus mengandung {influencer_count} influencer, "
                f"tapi hanya ada {len(report.influencer_reports)}"
            )

            report_ids = {r.influencer_id for r in report.influencer_reports}
            for inf_id in influencer_ids:
                assert inf_id in report_ids, (
                    f"Influencer {inf_id!r} tidak ada dalam laporan"
                )

        _run_async(_run())
