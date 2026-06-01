"""Phase 2 MVP — Author Verification Agent (Layer 3).

Dual-route verification:
  Route 1 — ORCID: If any CMS author has an ORCID iD, verify the submission
             DOI against their ORCID works list.
  Route 2 — Vietnamese AND Pipeline: Normalize names, fuzzy match, and
             check affiliation.
"""

import logging
import time

from reviewagent.agents.state import ReviewState
from reviewagent.author_nd.disambiguation import affiliation_match, match_authors
from reviewagent.connectors.base import ConnectorError
from reviewagent.connectors.orcid import ORCIDConnector
from reviewagent.schemas.author import AuthorCheckResult
from reviewagent.schemas.cms import CanonicalMetadataSchema

logger = logging.getLogger(__name__)


async def run(state: ReviewState) -> dict:
    """Execute author verification and return a state update."""
    start = time.monotonic()

    claimed_name = state.get("user_claimed_author")
    claimed_affiliation = state.get("user_claimed_affiliation")
    cms: CanonicalMetadataSchema | None = state.get("cms")

    if not claimed_name or cms is None:
        result = AuthorCheckResult(
            user_claimed_name=claimed_name or "",
            user_claimed_affiliation=claimed_affiliation,
            match_method="none",
            match_score=0.0,
            orcid_verified=False,
            affiliation_match=False,
            flags=["NO_AUTHOR_MATCH"],
        )
        return {
            "author_result": result,
            "timing": _elapsed_timing(state, start),
        }

    doi = cms.doi

    # --- Route 1: ORCID verification ---
    orcid_result = await _try_orcid_route(cms, claimed_name, doi)
    if orcid_result is not None:
        return {
            "author_result": orcid_result,
            "timing": _elapsed_timing(state, start),
        }

    # --- Route 2: Vietnamese AND pipeline ---
    result = _and_pipeline(cms, claimed_name, claimed_affiliation)
    return {
        "author_result": result,
        "timing": _elapsed_timing(state, start),
    }


async def _try_orcid_route(
    cms: CanonicalMetadataSchema,
    claimed_name: str,
    doi: str,
) -> AuthorCheckResult | None:
    """Try ORCID verification.  Returns AuthorCheckResult on success, None to fall back."""
    # Find first author with an ORCID iD
    orcid_id: str | None = None
    for author in cms.authors:
        if author.orcid:
            orcid_id = author.orcid
            break

    if orcid_id is None:
        return None

    try:
        connector = ORCIDConnector()
        async with connector:
            # Search by claimed name and verify DOI in works
            result = await connector.search_author(claimed_name, doi)
            if result.orcid_verified:
                # Also check affiliation if available
                aff_match = False
                if claimed_affiliation:
                    cms_affiliations = [
                        a.affiliation_raw for a in cms.authors if a.affiliation_raw
                    ]
                    aff_match = affiliation_match(claimed_affiliation, cms_affiliations)

                return AuthorCheckResult(
                    user_claimed_name=claimed_name,
                    user_claimed_affiliation=claimed_affiliation,
                    matched_author=result.matched_author,
                    match_method="orcid",
                    match_score=1.0,
                    orcid_verified=True,
                    affiliation_match=aff_match,
                    evidence=result.evidence,
                )
    except (ConnectorError, Exception):
        logger.warning("[author_agent] ORCID verification failed, falling back to AND", exc_info=True)

    return None


def _and_pipeline(
    cms: CanonicalMetadataSchema,
    claimed_name: str,
    claimed_affiliation: str | None,
) -> AuthorCheckResult:
    """Vietnamese Author Name Disambiguation pipeline."""
    author_names = [a.full_name for a in cms.authors]
    matched_name, match_score, match_method = match_authors(claimed_name, author_names)

    # Affiliation check
    aff_match = False
    if claimed_affiliation and matched_name:
        # Find the matched author's affiliation
        cms_affiliations = [a.affiliation_raw for a in cms.authors if a.affiliation_raw]
        aff_match = affiliation_match(claimed_affiliation, cms_affiliations)

    # Build flags
    flags: list[str] = []
    if match_method == "none":
        flags.append("NO_AUTHOR_MATCH")
    if claimed_affiliation and not aff_match:
        flags.append("AFFILIATION_MISMATCH")

    evidence = {
        "claimed_name": claimed_name,
        "cms_authors": author_names,
        "matched_author": matched_name,
        "match_score": match_score,
        "match_method": match_method,
    }

    return AuthorCheckResult(
        user_claimed_name=claimed_name,
        user_claimed_affiliation=claimed_affiliation,
        matched_author=matched_name,
        match_method=match_method,
        match_score=round(match_score, 4),
        orcid_verified=False,
        affiliation_match=aff_match,
        flags=flags,
        evidence=evidence,
    )


def _elapsed_timing(state: ReviewState, start: float) -> dict[str, float]:
    timing = dict(state.get("timing", {}))
    timing["author_agent"] = round(time.monotonic() - start, 4)
    return timing
