"""Phase 2 MVP — Aggregator Agent.

Compiles sub-scores from metadata, journal, author, and retraction checks
into a unified state for the Decision Agent.

Confidence formula (from phase2_guide.md):
  confidence_raw = (
    0.25 * metadata_score
    0.25 * journal_score
    0.30 * author_score
    0.10 * retraction_score
    0.10 * policy_score
  )
"""

import time
from typing import Any

from reviewagent.agents.state import ReviewState
from reviewagent.schemas.cms import CanonicalMetadataSchema


def run(state: ReviewState) -> dict:
    """Aggregate results from all upstream agents into sub-scores."""
    start = time.monotonic()

    cms: CanonicalMetadataSchema | None = state.get("cms")
    journal_result = state.get("journal_result")
    author_result = state.get("author_result")

    # --- Metadata score ---
    metadata_score = _compute_metadata_score(cms)

    # --- Journal score ---
    journal_score = journal_result.score if journal_result else 0.5  # neutral default

    # --- Author score ---
    author_score = _compute_author_score(author_result)

    # --- Retraction score ---
    retraction_score = 0.0 if (cms and cms.is_retracted) else 1.0

    # --- Policy score (placeholder — always 1.0 in MVP) ---
    policy_score = 1.0

    # --- Evidence panel ---
    evidence_panel: list[dict[str, Any]] = []

    if cms is not None:
        evidence_panel.append({
            "agent": "metadata",
            "source": cms.source_api,
            "score": metadata_score,
            "detail": f"Title, {len(cms.authors)} author(s), journal from {cms.source_api}",
        })

    if journal_result is not None:
        detail_parts = []
        if journal_result.indexes:
            detail_parts.append(f"Indexes: {', '.join(journal_result.indexes)}")
        if journal_result.quartile_best:
            detail_parts.append(f"Quartile: {journal_result.quartile_best}")
        if journal_result.sjr_value is not None:
            detail_parts.append(f"SJR: {journal_result.sjr_value}")
        if journal_result.is_predatory:
            detail_parts.append("PREDATORY")
        if journal_result.is_hijacked:
            detail_parts.append("HIJACKED")
        detail = "; ".join(detail_parts) if detail_parts else "No journal data"

        evidence_panel.append({
            "agent": "journal",
            "source": "mjl+scimago+doaj+beall",
            "score": journal_score,
            "detail": detail,
        })

    if author_result is not None:
        detail = f"Method: {author_result.match_method}, score: {author_result.match_score}"
        if author_result.orcid_verified:
            detail += ", ORCID verified"
        evidence_panel.append({
            "agent": "author",
            "source": author_result.match_method,
            "score": author_score,
            "detail": detail,
        })

    # --- Consolidate flags ---
    all_flags: list[str] = []
    if cms and cms.is_retracted:
        all_flags.append("RETRACTED")
    if journal_result:
        all_flags.extend(journal_result.flags)
    if author_result:
        all_flags.extend(author_result.flags)

    # De-duplicate
    seen: set[str] = set()
    unique_flags: list[str] = []
    for f in all_flags:
        if f not in seen:
            seen.add(f)
            unique_flags.append(f)

    # --- Sub-scores dict ---
    sub_scores = {
        "metadata_score": round(metadata_score, 4),
        "journal_score": round(journal_score, 4),
        "author_score": round(author_score, 4),
        "retraction_score": round(retraction_score, 4),
        "policy_score": round(policy_score, 4),
    }

    elapsed_timing = _elapsed_timing(state, start)

    return {
        "metadata_score": metadata_score,
        "journal_score": journal_score,
        "author_score": author_score,
        "retraction_score": retraction_score,
        "policy_score": policy_score,
        "evidence_panel": evidence_panel,
        "timing": elapsed_timing,
    }


def _compute_metadata_score(cms: CanonicalMetadataSchema | None) -> float:
    """Score metadata completeness: title, authors, year, journal ISSN, publisher."""
    if cms is None:
        return 0.0

    score = 0.0
    if cms.title:
        score += 0.2
    if cms.authors and cms.authors[0].full_name != "Unknown":
        score += 0.2
    if cms.pub_year:
        score += 0.2
    if cms.journal.issn_l:
        score += 0.2
    if cms.journal.publisher:
        score += 0.2

    return min(score, 1.0)


def _compute_author_score(author_result: Any) -> float:
    """Map author check result to a [0, 1] score."""
    if author_result is None:
        return 0.5  # neutral — no author check performed

    if author_result.orcid_verified:
        return 1.0

    return author_result.match_score


def _elapsed_timing(state: ReviewState, start: float) -> dict[str, float]:
    timing = dict(state.get("timing", {}))
    timing["aggregator"] = round(time.monotonic() - start, 4)
    return timing
