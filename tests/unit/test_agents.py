from datetime import date, datetime, timezone
from typing import Any

import pytest

from reviewagent.agents.decision_agent import DecisionAgent
from reviewagent.agents.metadata_agent import fetch_metadata_for_doi
from reviewagent.schemas.cms import CMSAuthor, CMSJournal, CanonicalMetadataSchema
from reviewagent.schemas.decision import DecisionLabel, DecisionResult


def make_cms(
    *,
    source_api: str = "crossref",
    issn_l: str | None = "1234-5678",
    publisher: str | None = "Test Publisher",
    is_retracted: bool = False,
) -> CanonicalMetadataSchema:
    return CanonicalMetadataSchema(
        doi="10.1000/test",
        title="A grounded paper",
        pub_year=2024,
        pub_date=date(2024, 5, 1),
        journal=CMSJournal(title="Journal of Tests", issn_l=issn_l, publisher=publisher),
        authors=[CMSAuthor(full_name="Nguyen Van A")],
        is_retracted=is_retracted,
        source_api=source_api,  # type: ignore[arg-type]
        source_url="https://api.crossref.org/works/10.1000/test",  # type: ignore[arg-type]
        fetched_at=datetime.now(tz=timezone.utc),
    )


class StubConnector:
    def __init__(self, result: CanonicalMetadataSchema | None) -> None:
        self.result = result
        self.closed = False

    async def lookup(self, doi: str) -> CanonicalMetadataSchema | None:
        return self.result

    async def aclose(self) -> None:
        self.closed = True


class StubGateway:
    def __init__(self, configured: bool, result: DecisionResult | None = None) -> None:
        self.is_configured = configured
        self.result = result

    async def generate_decision_v1(self, input_data: dict[str, Any]) -> DecisionResult:
        if self.result is None:
            raise RuntimeError("LLM failed")
        return self.result


@pytest.mark.asyncio
async def test_metadata_agent_uses_crossref_first() -> None:
    cms = make_cms()

    result = await fetch_metadata_for_doi(
        "10.1000/test",
        crossref=StubConnector(cms),  # type: ignore[arg-type]
        openalex=StubConnector(None),  # type: ignore[arg-type]
    )

    assert result.cms == cms
    assert result.source == "crossref"
    assert result.errors == []


@pytest.mark.asyncio
async def test_metadata_agent_falls_back_to_openalex() -> None:
    cms = make_cms(source_api="openalex", publisher=None)

    result = await fetch_metadata_for_doi(
        "10.1000/test",
        crossref=StubConnector(None),  # type: ignore[arg-type]
        openalex=StubConnector(cms),  # type: ignore[arg-type]
    )

    assert result.cms == cms
    assert result.source == "openalex"
    assert result.errors == ["Crossref returned no usable metadata"]


@pytest.mark.asyncio
async def test_metadata_agent_reports_fail_safe_miss() -> None:
    result = await fetch_metadata_for_doi(
        "10.1000/test",
        crossref=StubConnector(None),  # type: ignore[arg-type]
        openalex=StubConnector(None),  # type: ignore[arg-type]
    )

    assert result.cms is None
    assert result.needs_review is True
    assert "Crossref returned no usable metadata" in result.errors
    assert "OpenAlex returned no usable metadata" in result.errors


@pytest.mark.asyncio
async def test_decision_agent_uses_rule_when_llm_not_configured() -> None:
    result = await DecisionAgent(gateway=StubGateway(False)).run(make_cms())  # type: ignore[arg-type]

    assert result.source == "rule"
    assert result.decision.decision is DecisionLabel.APPROVE


@pytest.mark.asyncio
async def test_decision_agent_falls_back_to_rule_when_llm_fails() -> None:
    result = await DecisionAgent(gateway=StubGateway(True)).run(make_cms(issn_l=None, publisher=None))  # type: ignore[arg-type]

    assert result.source == "rule"
    assert result.decision.decision is DecisionLabel.REVIEW
    assert "MISSING_ISSN" in result.decision.flags


@pytest.mark.asyncio
async def test_decision_agent_uses_llm_when_configured() -> None:
    decision = DecisionResult(
        decision=DecisionLabel.REVIEW,
        confidence_raw=0.4,
        confidence_calibrated=0.4,
        rationale="LLM structured response.",
        flags=["WEAK_EVIDENCE"],
        sub_scores={"metadata_completeness": 0.5},
    )

    result = await DecisionAgent(gateway=StubGateway(True, decision)).run(make_cms())  # type: ignore[arg-type]

    assert result.source == "llm"
    assert result.decision == decision
