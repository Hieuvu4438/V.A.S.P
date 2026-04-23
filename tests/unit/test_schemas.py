from datetime import datetime
from pathlib import Path
from uuid import uuid4
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reviewagent.schemas.cms import CanonicalMetadataSchema, CMSAuthor, CMSJournal
from reviewagent.schemas.decision import DecisionLabel, DecisionResult
from reviewagent.schemas.submission import SubmissionCreateRequest, SubmissionCreateResponse, SubmissionStatus


def test_submission_request_normalizes_doi() -> None:
    request = SubmissionCreateRequest(doi="https://doi.org/10.1000/ABC-123")

    assert request.doi == "10.1000/abc-123"


def test_submission_request_rejects_invalid_doi() -> None:
    with pytest.raises(ValidationError):
        SubmissionCreateRequest(doi="not-a-doi")


def test_cms_requires_grounded_provenance_and_normalizes_doi() -> None:
    cms = CanonicalMetadataSchema(
        doi="DOI:10.1000/XYZ-789",
        title="Grounded title",
        pub_year=2024,
        pub_date="2024-05-01",
        journal=CMSJournal(title="Journal of Testing", issn_l="1234-5678"),
        authors=[CMSAuthor(full_name="Nguyen Van A")],
        source_api="crossref",
        source_url="https://api.crossref.org/works/10.1000/xyz-789",
        fetched_at="2026-04-23T10:00:00Z",
    )

    assert cms.doi == "10.1000/xyz-789"
    assert cms.source_api == "crossref"
    assert cms.fetched_at == datetime.fromisoformat("2026-04-23T10:00:00+00:00")


def test_cms_rejects_pub_date_year_mismatch() -> None:
    with pytest.raises(ValidationError):
        CanonicalMetadataSchema(
            doi="10.1000/test-1",
            title="Grounded title",
            pub_year=2024,
            pub_date="2023-05-01",
            journal=CMSJournal(title="Journal of Testing"),
            authors=[CMSAuthor(full_name="Nguyen Van A")],
            source_api="openalex",
            source_url="https://api.openalex.org/works/W123",
            fetched_at="2026-04-23T10:00:00Z",
        )


def test_decision_result_keeps_structured_output_shape() -> None:
    result = DecisionResult(
        decision=DecisionLabel.REVIEW,
        confidence_raw=0.45,
        confidence_calibrated=0.5,
        rationale="Metadata is incomplete and needs manual review.",
        flags=["MISSING_ISSN", "MISSING_ISSN", " WEAK_EVIDENCE "],
        sub_scores={"metadata_completeness": 0.4, "source_reliability": 0.9},
    )

    assert result.flags == ["MISSING_ISSN", "WEAK_EVIDENCE"]
    assert result.sub_scores["source_reliability"] == 0.9


def test_submission_response_supports_basic_phase1_shape() -> None:
    response = SubmissionCreateResponse(
        submission_id=uuid4(),
        status=SubmissionStatus.PENDING,
        decision_id=None,
    )

    assert response.status is SubmissionStatus.PENDING
