from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from reviewagent.agents.graph import ReviewPipeline
from reviewagent.schemas.cms import CMSAuthor, CMSJournal, CanonicalMetadataSchema
from reviewagent.schemas.decision import DecisionLabel, DecisionResult


def make_cms() -> CanonicalMetadataSchema:
    return CanonicalMetadataSchema(
        doi="10.1000/test",
        title="A grounded paper",
        pub_year=2024,
        pub_date=date(2024, 5, 1),
        journal=CMSJournal(title="Journal of Tests", issn_l="1234-5678", publisher="Test Publisher"),
        authors=[CMSAuthor(full_name="Nguyen Van A")],
        source_api="crossref",
        source_url="https://api.crossref.org/works/10.1000/test",  # type: ignore[arg-type]
        fetched_at=datetime.now(tz=timezone.utc),
    )


class StubMetadataResult:
    def __init__(self, cms: CanonicalMetadataSchema | None, errors: list[str] | None = None) -> None:
        self.cms = cms
        self.source = "crossref" if cms is not None else None
        self.needs_review = cms is None
        self.errors = errors or []


class StubMetadataAgent:
    def __init__(self, result: StubMetadataResult) -> None:
        self.result = result

    async def run(self, doi: str) -> StubMetadataResult:
        return self.result


class StubDecisionResult:
    def __init__(self, decision: DecisionResult) -> None:
        self.decision = decision
        self.source = "rule"


class StubDecisionAgent:
    async def run(self, cms: CanonicalMetadataSchema, errors: list[str] | None = None) -> StubDecisionResult:
        return StubDecisionResult(
            DecisionResult(
                decision=DecisionLabel.APPROVE,
                confidence_raw=0.9,
                confidence_calibrated=0.9,
                rationale="Metadata is complete.",
                flags=errors or [],
                sub_scores={"metadata_completeness": 1.0},
            )
        )


@pytest.mark.asyncio
async def test_review_pipeline_runs_metadata_then_decision() -> None:
    cms = make_cms()
    pipeline = ReviewPipeline(
        metadata_agent=StubMetadataAgent(StubMetadataResult(cms)),  # type: ignore[arg-type]
        decision_agent=StubDecisionAgent(),  # type: ignore[arg-type]
    )

    state = await pipeline.run(submission_id=uuid4(), doi="10.1000/test")

    assert state.cms == cms
    assert state.metadata_source == "crossref"
    assert state.decision is not None
    assert state.decision.decision is DecisionLabel.APPROVE
    assert state.errors == []


@pytest.mark.asyncio
async def test_review_pipeline_stops_when_metadata_missing() -> None:
    pipeline = ReviewPipeline(
        metadata_agent=StubMetadataAgent(StubMetadataResult(None, ["Crossref returned no usable metadata"])),  # type: ignore[arg-type]
        decision_agent=StubDecisionAgent(),  # type: ignore[arg-type]
    )

    state = await pipeline.run(submission_id=uuid4(), doi="10.1000/test")

    assert state.cms is None
    assert state.decision is None
    assert "No metadata could be fetched from any source" in state.errors
