"""
Monthly Report Service — Auto-calculate metrics dari deal_records + generate AI insights.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _fmt_rupiah(n: int) -> str:
    return f"Rp{n:,.0f}".replace(",", ".")


def _pct(a: int, b: int) -> str:
    if b == 0:
        return "0%"
    return f"{round(a / b * 100)}%"


async def calculate_metrics(
    db: AsyncSession,
    brand_id: str,
    period_start: date,
    period_end: date,
    gmv_previous: int = 0,
) -> dict:
    """Hitung semua metrics dari deal_records untuk periode tertentu."""

    result = await db.execute(text("""
        SELECT
            COUNT(*) as total_deal,
            COUNT(CASE WHEN link_video IS NOT NULL AND link_video != '' THEN 1 END) as total_uploaded,
            COUNT(CASE WHEN total_vt > 0 THEN 1 END) as total_videos_count,
            COUNT(CASE WHEN gmv_perbulan_after_join > 0 THEN 1 END) as total_generate_sales,
            COALESCE(SUM(gmv_perbulan_after_join), 0) as gmv_current,
            COALESCE(SUM(total_vt), 0) as total_videos
        FROM deal_records
        WHERE brand_id = :brand_id
          AND tanggal BETWEEN :start AND :end
    """), {"brand_id": brand_id, "start": period_start, "end": period_end})

    row = result.mappings().first()
    if not row:
        return {}

    total_deal = row["total_deal"] or 0
    total_uploaded = row["total_uploaded"] or 0
    total_videos = row["total_videos"] or 0
    total_generate_sales = row["total_generate_sales"] or 0
    gmv_current = row["gmv_current"] or 0

    # GMV breakdown: pakai gmv_week1-4 sebagai proxy video, sisanya live
    gmv_video_result = await db.execute(text("""
        SELECT COALESCE(SUM(
            gmv_week1_after_join + gmv_week2_after_join +
            gmv_week3_after_join + gmv_week4_after_join
        ), 0) as gmv_video
        FROM deal_records
        WHERE brand_id = :brand_id AND tanggal BETWEEN :start AND :end
    """), {"brand_id": brand_id, "start": period_start, "end": period_end})
    gmv_video = gmv_video_result.scalar() or 0
    gmv_live = max(0, gmv_current - gmv_video)

    return {
        "total_deal": total_deal,
        "total_uploaded": total_uploaded,
        "total_not_uploaded": total_deal - total_uploaded,
        "total_videos": total_videos,
        "total_generate_sales": total_generate_sales,
        "gmv_current": gmv_current,
        "gmv_previous": gmv_previous,
        "gmv_video": gmv_video,
        "gmv_live": gmv_live,
        "total_products_sold": 0,   # manual input
        "total_orders_settled": 0,  # manual input
    }


async def get_top_performers(
    db: AsyncSession,
    brand_id: str,
    period_start: date,
    period_end: date,
    limit: int = 10,
) -> list[dict]:
    result = await db.execute(text("""
        SELECT username, gmv_perbulan_after_join as gmv, link_acc
        FROM deal_records
        WHERE brand_id = :brand_id
          AND tanggal BETWEEN :start AND :end
          AND gmv_perbulan_after_join > 0
        ORDER BY gmv_perbulan_after_join DESC
        LIMIT :limit
    """), {"brand_id": brand_id, "start": period_start, "end": period_end, "limit": limit})
    return [dict(r) for r in result.mappings().all()]


def generate_ai_insights(metrics: dict, brand_name: str, batch_name: str, top_performers: list) -> dict:
    """Generate rule-based AI insights dari metrics. Semua teks bisa diedit user."""

    total_deal = metrics.get("total_deal", 0)
    total_uploaded = metrics.get("total_uploaded", 0)
    total_not_uploaded = metrics.get("total_not_uploaded", 0)
    total_videos = metrics.get("total_videos", 0)
    total_generate_sales = metrics.get("total_generate_sales", 0)
    gmv_current = metrics.get("gmv_current", 0)
    gmv_previous = metrics.get("gmv_previous", 0)
    gmv_video = metrics.get("gmv_video", 0)
    gmv_live = metrics.get("gmv_live", 0)

    conversion_rate = round(total_generate_sales / total_deal * 100) if total_deal > 0 else 0
    avg_video = round(total_videos / total_uploaded, 1) if total_uploaded > 0 else 0
    gmv_growth = round((gmv_current - gmv_previous) / gmv_previous * 100) if gmv_previous > 0 else 0

    # Insight Key Metrics
    insight_key_metrics = (
        f"Campaign {batch_name} untuk {brand_name} mencatat {total_deal} creator deal "
        f"dengan {total_uploaded} sudah upload konten dan {total_not_uploaded} belum upload. "
        f"Total {total_videos} video dihasilkan, dengan {total_generate_sales} creator menghasilkan penjualan. "
        f"GMV periode ini mencapai {_fmt_rupiah(gmv_current)}"
    )
    if gmv_previous > 0:
        insight_key_metrics += f", naik {gmv_growth}% dibanding periode sebelumnya ({_fmt_rupiah(gmv_previous)})."
    else:
        insight_key_metrics += "."

    # Insight Affiliate
    insight_affiliate = (
        f"Dari {total_deal} creator deal, {total_generate_sales} sudah menghasilkan penjualan "
        f"(conversion rate {conversion_rate}%). "
    )
    if total_uploaded > 0:
        insight_affiliate += f"{total_uploaded} creator sudah posting menghasilkan {total_videos} video "
        insight_affiliate += f"(rata-rata {avg_video} video per creator). "
    if conversion_rate >= 80:
        insight_affiliate += "Conversion rate sangat tinggi, menandakan kualitas creator yang baik."
    elif conversion_rate >= 60:
        insight_affiliate += "Conversion rate cukup baik, masih ada ruang untuk optimasi."
    else:
        insight_affiliate += "Conversion rate perlu ditingkatkan dengan seleksi creator yang lebih ketat."

    if top_performers:
        top1 = top_performers[0]
        insight_affiliate += f"\n\nTop performer: @{top1.get('username', '-')} dengan GMV {_fmt_rupiah(top1.get('gmv', 0))}."
        if len(top_performers) >= 3:
            insight_affiliate += " Distribusi GMV cenderung top-heavy (terkonsentrasi pada beberapa creator besar)."

    # Insight Funnel
    insight_funnel = (
        f"Funnel campaign: {total_deal} creator deal → {total_uploaded} posting → {total_generate_sales} generate sales. "
    )
    if total_not_uploaded > 0:
        insight_funnel += f"Bottleneck utama ada di posting konten ({total_not_uploaded} creator belum upload). "
        insight_funnel += "Perlu follow-up aktif untuk mendorong creator segera posting."
    else:
        insight_funnel += "Semua creator sudah upload konten — eksekusi sangat baik."

    # Insight GMV
    insight_gmv = f"GMV periode ini: {_fmt_rupiah(gmv_current)}. "
    if gmv_video > 0:
        pct_video = round(gmv_video / gmv_current * 100) if gmv_current > 0 else 0
        insight_gmv += f"GMV dari video: {_fmt_rupiah(gmv_video)} ({pct_video}% dari total). "
    if gmv_live > 0:
        insight_gmv += f"GMV dari live: {_fmt_rupiah(gmv_live)}. "
    else:
        insight_gmv += "Live commerce belum berkontribusi signifikan — ada peluang untuk dioptimasi. "
    if gmv_previous > 0 and gmv_growth > 0:
        insight_gmv += f"Terjadi pertumbuhan {gmv_growth}% dibanding periode sebelumnya."

    # Insight Product
    insight_product = (
        "Campaign berfokus pada hero product. Fokus 1 SKU terbukti efektif untuk scaling GMV, "
        "namun perlu diversifikasi produk untuk mengurangi risiko ketergantungan pada satu SKU."
    )

    # Insight Gap
    gaps = []
    if total_not_uploaded > 0:
        gaps.append(f"{total_not_uploaded} creator belum upload → potensi GMV belum terealisasi")
    if gmv_live < gmv_current * 0.05:
        gaps.append("Live performance sangat rendah → peluang channel live belum dimanfaatkan")
    insight_gap = "Gap operasional yang teridentifikasi:\n" + "\n".join(f"• {g}" for g in gaps) if gaps else "Tidak ada gap operasional signifikan yang teridentifikasi."

    # Insight Strategic
    if gmv_growth > 100:
        phase = "Scaling Phase — pertumbuhan sangat agresif"
    elif gmv_growth > 20:
        phase = "Growth Phase — pertumbuhan stabil"
    else:
        phase = "Stabilization Phase — perlu strategi baru untuk akselerasi"

    insight_strategic = (
        f"Campaign ini berada di {phase}. "
        f"Creator menunjukkan inisiatif tinggi dengan conversion rate {conversion_rate}%. "
        "Exposure sudah terbentuk dan GMV berpotensi terus naik dengan optimasi yang tepat."
    )

    # Next Plan
    next_plan = """Operasional:
• Follow-up creator yang belum upload (reminder + guideline)
• Percepat proses distribusi sample
• Monitoring timeline upload

Growth:
• Dorong creator untuk posting lebih rutin
• Optimasi komunikasi dengan affiliate
• Evaluasi performa konten secara mingguan

Revenue Optimization:
• Fokus scaling hero SKU
• Gunakan strategi bundle, promo hemat, konten edukasi

Order Management:
• Monitoring settlement
• Dorong penyelesaian pesanan lebih cepat"""

    # Kesimpulan
    if conversion_rate >= 80 and gmv_current > 0:
        status = "sangat sukses"
    elif conversion_rate >= 60:
        status = "cukup sukses"
    else:
        status = "perlu evaluasi lebih lanjut"

    kesimpulan = (
        f"Campaign {batch_name} untuk {brand_name} bisa dikategorikan {status} "
        f"dengan GMV {_fmt_rupiah(gmv_current)} dan conversion rate creator {conversion_rate}%. "
        f"Total {total_videos} video konten dihasilkan oleh {total_uploaded} creator. "
        "Untuk scale lebih lanjut, fokus pada aktivasi creator yang belum posting, "
        "diversifikasi channel (terutama live), dan optimasi conversion & settlement."
    )

    return {
        "insight_key_metrics": insight_key_metrics,
        "insight_affiliate": insight_affiliate,
        "insight_funnel": insight_funnel,
        "insight_gmv": insight_gmv,
        "insight_product": insight_product,
        "insight_gap": insight_gap,
        "insight_strategic": insight_strategic,
        "next_plan": next_plan,
        "kesimpulan": kesimpulan,
    }
