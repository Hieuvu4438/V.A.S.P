from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reviewagent.schemas.audit import AuditEntry
from reviewagent.schemas.author import AuthorCheckResult
from reviewagent.schemas.cms import CanonicalMetadataSchema, CMSAuthor, CMSJournal
from reviewagent.schemas.decision import DecisionLabel, DecisionResult
from reviewagent.schemas.journal import JournalCheckResult
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
        pub_date=date(2024, 5, 1),
        journal=CMSJournal(title="Journal of Testing", issn_l="1234-5678"),
        authors=[CMSAuthor(full_name="Nguyen Van A")],
        source_api="crossref",
        source_url="https://api.crossref.org/works/10.1000/xyz-789",  # type: ignore[arg-type]
        fetched_at=datetime.fromisoformat("2026-04-23T10:00:00+00:00"),
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
            pub_date=date(2023, 5, 1),
            journal=CMSJournal(title="Journal of Testing"),
            authors=[CMSAuthor(full_name="Nguyen Van A")],
            source_api="openalex",
            source_url="https://api.openalex.org/works/W123",  # type: ignore[arg-type]
            fetched_at=datetime.fromisoformat("2026-04-23T10:00:00+00:00"),
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


def test_cms_v2_accepts_journal_author_article_and_retraction_fields() -> None:
    cms = CanonicalMetadataSchema(
        doi="https://doi.org/10.1000/PHASE2",
        title="Phase 2 metadata",
        abstract="Grounded abstract from source.",
        article_type="journal-article",
        language="en",
        volume="12",
        issue="3",
        pages="10-20",
        pub_year=2024,
        pub_date=date(2024, 5, 1),
        journal=CMSJournal(
            title="Journal of Testing",
            issn_l="1234-5678",
            is_scie=True,
            is_doaj=True,
            quartile="Q1",
            sjr_value=1.25,
        ),
        authors=[
            CMSAuthor(
                full_name="Nguyen Van A",
                orcid="https://orcid.org/0000-0002-1825-0097",
                affiliation_raw="Posts and Telecommunications Institute of Technology",
                ror_id="https://ror.org/03yrm5c26",
            )
        ],
        is_retracted=True,
        retraction_doi="DOI:10.1000/RETRACTION",
        retraction_date=date(2025, 1, 1),
        source_api="crossref",
        source_url="https://api.crossref.org/works/10.1000/phase2",  # type: ignore[arg-type]
        fetched_at=datetime.fromisoformat("2026-04-23T10:00:00+00:00"),
    )

    assert cms.cms_version == "2.0"
    assert cms.doi == "10.1000/phase2"
    assert cms.retraction_doi == "10.1000/retraction"
    assert cms.journal.is_scie is True
    assert cms.journal.is_doaj is True
    assert cms.authors[0].orcid == "0000-0002-1825-0097"
    assert cms.authors[0].ror_id == "https://ror.org/03yrm5c26"


def test_cms_v2_rejects_retraction_details_when_not_retracted() -> None:
    with pytest.raises(ValidationError):
        CanonicalMetadataSchema(
            doi="10.1000/test-2",
            title="Grounded title",
            pub_year=2024,
            journal=CMSJournal(title="Journal of Testing"),
            authors=[CMSAuthor(full_name="Nguyen Van A")],
            retraction_doi="10.1000/retraction",
            source_api="openalex",
            source_url="https://api.openalex.org/works/W123",  # type: ignore[arg-type]
            fetched_at=datetime.fromisoformat("2026-04-23T10:00:00+00:00"),
        )


def test_journal_check_result_keeps_phase2_shape() -> None:
    result = JournalCheckResult(
        issn_l=" 1234-5678 ",
        title=" Journal of Testing ",
        is_indexed=True,
        indexes=["SCIE", "SCIE", "DOAJ"],
        quartile_best="Q1",
        sjr_value=1.25,
        is_predatory=False,
        is_hijacked=False,
        flags=["", "INDEXED", "INDEXED"],
        score=0.9,
        evidence={"scimago": {"source": "snapshot"}},
    )

    assert result.issn_l == "1234-5678"
    assert result.title == "Journal of Testing"
    assert result.indexes == ["SCIE", "DOAJ"]
    assert result.flags == ["INDEXED"]


def test_author_check_result_keeps_phase2_shape() -> None:
    result = AuthorCheckResult(
        user_claimed_name=" Nguyen Van A ",
        user_claimed_affiliation=" PTIT ",
        matched_author=" Nguyen Van A ",
        match_method="orcid",
        match_score=1.0,
        orcid_verified=True,
        affiliation_match=True,
        flags=["", "ORCID_MATCH", "ORCID_MATCH"],
        evidence={"orcid": {"verified": True}},
    )

    assert result.user_claimed_name == "Nguyen Van A"
    assert result.matched_author == "Nguyen Van A"
    assert result.flags == ["ORCID_MATCH"]


def test_audit_entry_keeps_hmac_chain_shape() -> None:
    entry = AuditEntry(
        entry_id=" entry-1 ",
        timestamp=datetime.fromisoformat("2026-04-23T10:00:00+00:00"),
        event_type=" decision.created ",
        actor=" system ",
        submission_id=" submission-1 ",
        details={"decision": "REVIEW"},
        hmac_hash=" hash-2 ",
        prev_hash=" hash-1 ",
    )

    assert entry.entry_id == "entry-1"
    assert entry.event_type == "decision.created"
    assert entry.actor == "system"
    assert entry.prev_hash == "hash-1"
