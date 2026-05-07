import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from reviewagent.agents.graph import ReviewPipeline
from reviewagent.api.deps import get_db, get_pipeline
from reviewagent.db.repositories.decision_repo import save_decision
from reviewagent.db.repositories.submission_repo import create_submission, update_submission_status
from reviewagent.schemas.submission import (
    SubmissionCreateRequest,
    SubmissionCreateResponse,
    SubmissionStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionCreateResponse, status_code=201)
async def create_submission_endpoint(
    request: SubmissionCreateRequest,
    db: AsyncSession = Depends(get_db),
    pipeline: ReviewPipeline = Depends(get_pipeline),
) -> SubmissionCreateResponse:
    submission = await create_submission(db, doi=request.doi, status=SubmissionStatus.PROCESSING)
    submission_id = submission.id

    try:
        state = await pipeline.run(submission_id=submission_id, doi=request.doi)

        if state.cms is not None:
            from reviewagent.db.models.publication import Publication

            pub = Publication(
                doi=state.cms.doi,
                title=state.cms.title,
                pub_year=state.cms.pub_year,
                pub_date=state.cms.pub_date,
                cms=state.cms.model_dump(mode="json"),
                provenance={
                    "source_api": state.cms.source_api,
                    "source_url": str(state.cms.source_url),
                },
            )
            db.add(pub)
            await db.flush()
            submission.publication_id = pub.id

        if state.decision is not None:
            decision = await save_decision(
                session=db,
                submission_id=submission_id,
                decision=state.decision.decision,
                confidence_raw=state.decision.confidence_raw,
                confidence_calibrated=state.decision.confidence_calibrated,
                rationale=state.decision.rationale,
                flags=state.decision.flags,
                evidence={"sub_scores": state.decision.sub_scores},
                prompt_version=state.prompt_version,
            )
            await update_submission_status(db, submission_id, SubmissionStatus.COMPLETED)
            await db.commit()

            return SubmissionCreateResponse(
                submission_id=submission_id,
                status=SubmissionStatus.COMPLETED,
                decision_id=decision.id,
            )

        if state.errors:
            await update_submission_status(db, submission_id, SubmissionStatus.FAILED)
            await db.commit()
            raise HTTPException(
                status_code=422,
                detail={"errors": state.errors},
            )

        await update_submission_status(db, submission_id, SubmissionStatus.COMPLETED)
        await db.commit()
        return SubmissionCreateResponse(
            submission_id=submission_id,
            status=SubmissionStatus.COMPLETED,
        )

    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        await update_submission_status(db, submission_id, SubmissionStatus.FAILED)
        await db.commit()
        raise HTTPException(status_code=500, detail="Pipeline execution failed")
