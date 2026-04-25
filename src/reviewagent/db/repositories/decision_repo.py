from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reviewagent.db.models.decision import Decision
from reviewagent.schemas.decision import DecisionLabel


async def save_decision(
    session: AsyncSession,
    submission_id: UUID,
    decision: DecisionLabel,
    confidence_raw: float,
    confidence_calibrated: float,
    rationale: str,
    flags: list[str] | None = None,
    evidence: dict | None = None,
    model_version: str | None = None,
    prompt_version: str | None = None,
) -> Decision:
    db_decision = Decision(
        submission_id=submission_id,
        decision=decision,
        confidence_raw=confidence_raw,
        confidence_calibrated=confidence_calibrated,
        rationale=rationale,
        flags=flags or [],
        evidence=evidence or {},
        model_version=model_version,
        prompt_version=prompt_version,
    )
    session.add(db_decision)
    await session.flush()
    return db_decision


async def get_decision_by_id(session: AsyncSession, decision_id: UUID) -> Decision | None:
    return await session.get(Decision, decision_id)


async def get_decision_by_submission_id(session: AsyncSession, submission_id: UUID) -> Decision | None:
    result = await session.execute(select(Decision).where(Decision.submission_id == submission_id))
    return result.scalar_one_or_none()
