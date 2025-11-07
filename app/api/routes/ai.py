from fastapi import APIRouter, Depends
from app.api.deps import Authed
from app.schemas.intervention import EmotionLabelsIn, EmotionLabelsOut
from app.services.ai import emotion_labels

router = APIRouter(prefix="/api/ai", tags=["ai"])

@router.post("/emotion-labels", response_model=EmotionLabelsOut)
async def labels(payload: EmotionLabelsIn, ctx=Depends(Authed)):
    opts = await emotion_labels(payload.model_dump())
    return {"emotion_options": opts}
