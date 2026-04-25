from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reviewagent.db.models.submission import Submission
from reviewagent.schemas.submission import SubmissionStatus


async def create_submission(
    session: AsyncSession,
    doi: str,
    status: SubmissionStatus = SubmissionStatus.PENDING,
) -> Submission:
    submission = Submission(doi=doi, status=status)
    session.add(submission)
    await session.flush()
    return submission


async def get_submission_by_id(session: AsyncSession, submission_id: UUID) -> Submission | None:
    return await session.get(Submission, submission_id)


async def update_submission_status(
    session: AsyncSession,
    submission_id: UUID,
    status: SubmissionStatus,
) -> Submission | None:
    submission = await get_submission_by_id(session, submission_id)
    if submission is None:
        return None
    submission.status = status
    await session.flush()
    return submission


async def get_latest_submission_by_doi(session: AsyncSession, doi: str) -> Submission | None:
    result = await session.execute(
        select(Submission)
        .where(Submission.doi == doi)
        .order_by(Submission.created_at.desc(), Submission.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
