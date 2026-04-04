"""Learning Engine API router."""
from __future__ import annotations
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session
from app.agents.learning_engine import LearningEngine
from app.models.domain import SelectionCriteria
from app.services.rbac import get_current_user

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
    engine = LearningEngine()
    criteria = SelectionCriteria(id="default", name="Default")
    recs = await engine.get_influencer_recommendations(criteria, top_n=top_n, db=db)
    return [
        {
            "influencer_id": r.influencer_id,
            "predicted_conversion_rate": r.predicted_conversion_rate,
            "predicted_gmv": r.predicted_gmv,
            "confidence_score": r.confidence_score,
            "based_on_campaigns": r.based_on_campaigns,
        }
        for r in recs
    ]
