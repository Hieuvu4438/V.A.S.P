"""Phase 2 MVP — ReviewState TypedDict for LangGraph pipeline."""

from typing import Any, TypedDict

from reviewagent.schemas.author import AuthorCheckResult
from reviewagent.schemas.cms import CanonicalMetadataSchema
from reviewagent.schemas.decision import DecisionResult
from reviewagent.schemas.journal import JournalCheckResult


class ReviewState(TypedDict, total=False):
    submission_id: str
    doi: str
    user_claimed_author: str | None
    user_claimed_affiliation: str | None

    # L1: Identity & Source
    cms: CanonicalMetadataSchema | None

    # L2: Journal Quality
    journal_result: JournalCheckResult | None

    # L3: Author & Affiliation
    author_result: AuthorCheckResult | None

    # L5: Decision
    decision: DecisionResult | None

    # Aggregated sub-scores (populated by aggregator_agent)
    metadata_score: float
    journal_score: float
    author_score: float
    retraction_score: float
    policy_score: float
    evidence_panel: list[dict[str, Any]]

    # Meta / Metrics
    errors: list[str]
    metadata_source: str | None
    prompt_version: str
    timing: dict[str, float]  # execution seconds per agent
