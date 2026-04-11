"""Learning Engine API router."""
from __future__ import annotations
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session
from app.agents.learning_engine import LearningEngine
from app.models.domain import SelectionCriteria
from app.services.rbac import get_current_user
from app.services.message_learning_service import MessageLearningService

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/model-history")
async def get_model_history(
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict]:
    engine = LearningEngine()
    history = await engine.get_model_performance_history(db)
    return [
        {
            "id": m.id,
            "model_type": m.model_type.value,
            "version": m.version,
            "accuracy_before": m.accuracy_before,
            "accuracy_after": m.accuracy_after,
            "trained_at": m.trained_at.isoformat() if m.trained_at else None,
            "training_data_size": m.training_data_size,
        }
        for m in history
    ]


@router.get("/recommendations")
async def get_recommendations(
    top_n: int = 10,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict]:
    from sqlalchemy import text
    engine = LearningEngine()
    criteria = SelectionCriteria(id="default", name="Default")
    recs = await engine.get_influencer_recommendations(criteria, top_n=top_n, db=db)

    # Ambil nama affiliator dari DB
    if recs:
        ids = [r.influencer_id for r in recs]
        placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
        name_result = await db.execute(
            text(f"SELECT id::text, name FROM influencers WHERE id::text IN ({placeholders})"),
            {f"id_{i}": v for i, v in enumerate(ids)}
        )
        name_map = {row[0]: row[1] for row in name_result.fetchall()}
    else:
        name_map = {}

    return [
        {
            "influencer_id": r.influencer_id,
            "influencer_name": name_map.get(r.influencer_id),
            "predicted_conversion_rate": r.predicted_conversion_rate,
            "predicted_gmv": r.predicted_gmv,
            "confidence_score": r.confidence_score,
            "based_on_campaigns": r.based_on_campaigns,
        }
        for r in recs
    ]


# ── Message Variation Learning ──────────────────────────────────────────────

class AddVariationRequest(BaseModel):
    template_type: str = "request_whatsapp"
    content: str


class RecordReplyRequest(BaseModel):
    variation_id: str


@router.get("/message-variations")
async def get_message_variations(
    template_type: str = "request_whatsapp",
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict]:
    """Ambil semua variasi pesan beserta statistik reply rate."""
    svc = MessageLearningService(db)
    stats = await svc.get_variation_stats(template_type)
    return [
        {
            "id": str(s["id"]),
            "content": s["content"],
            "send_count": s["send_count"],
            "reply_count": s["reply_count"],
            "reply_rate": round(float(s["reply_rate"] or 0) * 100, 1),  # dalam persen
            "is_active": s["is_active"],
            "created_at": s["created_at"].isoformat() if s.get("created_at") else None,
        }
        for s in stats
    ]


@router.post("/message-variations")
async def add_message_variation(
    body: AddVariationRequest,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict:
    """Tambah variasi pesan baru."""
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Konten pesan tidak boleh kosong")
    svc = MessageLearningService(db)
    try:
        variation_id = await svc.add_variation(body.template_type, body.content.strip())
        await db.commit()
        return {"id": variation_id, "message": "Variasi berhasil ditambahkan"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/message-variations/record-reply")
async def record_message_reply(
    body: RecordReplyRequest,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict:
    """Catat bahwa pesan dengan variasi ini dibalas (update reply rate)."""
    svc = MessageLearningService(db)
    await svc.record_reply(body.variation_id)
    await db.commit()
    return {"message": "Reply berhasil dicatat"}
