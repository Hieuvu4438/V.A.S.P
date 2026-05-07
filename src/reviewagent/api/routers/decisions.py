from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from reviewagent.api.deps import get_db
from reviewagent.db.repositories.decision_repo import get_decision_by_id, get_decision_by_submission_id
from reviewagent.schemas.decision import DecisionLabel

router = APIRouter(prefix="/decisions", tags=["decisions"])


class DecisionResponse(BaseModel):
    decision_id: UUID
    submission_id: UUID
    decision: DecisionLabel
    confidence_raw: float
    confidence_calibrated: float
    rationale: str
    flags: list[str]
    evidence: dict
    model_config = {"from_attributes": True}


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DecisionResponse:
    decision = await get_decision_by_id(db, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return DecisionResponse(
        decision_id=decision.id,
        submission_id=decision.submission_id,
        decision=decision.decision,
        confidence_raw=decision.confidence_raw,
        confidence_calibrated=decision.confidence_calibrated,
        rationale=decision.rationale,
        flags=decision.flags,
        evidence=decision.evidence,
    )


@router.get("", response_model=DecisionResponse)
async def get_decision_by_submission(
    submission_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> DecisionResponse:
    decision = await get_decision_by_submission_id(db, submission_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found for this submission")
    return DecisionResponse(
        decision_id=decision.id,
        submission_id=decision.submission_id,
        decision=decision.decision,
        confidence_raw=decision.confidence_raw,
        confidence_calibrated=decision.confidence_calibrated,
        rationale=decision.rationale,
        flags=decision.flags,
        evidence=decision.evidence,
    )
