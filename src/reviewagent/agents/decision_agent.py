"""Phase 2 MVP — Decision Agent with CoVe + Self-Consistency.

Two advanced techniques:
  1. Chain-of-Verification (CoVe): LLM generates a decision, then
     self-verifies each claim against grounded evidence.
  2. Self-Consistency (k=3): Run LLM k times with temperature > 0,
     majority-vote the label, average the confidence.

Auto-approve/reject thresholds (from config):
  confidence_calibrated >= tau_high (0.90) -> APPROVE
  tau_low (0.65) <= confidence < tau_high  -> REVIEW
  confidence < tau_low                     -> REJECT

Falls back to rule-based decision when LLM is not configured or fails.
"""

import asyncio
import json
import logging
import math
import time
from collections import Counter
from typing import Any

from pydantic import ValidationError

from reviewagent.agents.state import ReviewState
from reviewagent.llm.calibration import calibrate_confidence
from reviewagent.llm.gateway import LLMGateway, LLMGatewayError
from reviewagent.schemas.decision import DecisionLabel, DecisionResult

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# CoVe prompt
# ------------------------------------------------------------------

_COVE_SYSTEM_PROMPT = """You are the Phase 2 decision agent for ReviewAgent PTIT.
Use ONLY the provided evidence. Do not use memory or outside knowledge.

First, produce a decision. Then verify each factual claim you made against
the evidence. If a claim cannot be verified, lower your confidence.

Return ONLY valid JSON matching this shape:
{
  "decision": "APPROVE" | "REVIEW" | "REJECT",
  "confidence_raw": number between 0 and 1,
  "rationale": "short evidence-grounded explanation",
  "verification_checks": [
    {"claim": "string", "verified": true/false, "evidence_field": "string"}
  ]
}
"""

_SELF_CONSISTENCY_SYSTEM_PROMPT = """You are the Phase 2 decision agent for ReviewAgent PTIT.
Use ONLY the provided evidence. Do not use memory or outside knowledge.
If evidence is missing or conflicting, choose REVIEW.

Return ONLY valid JSON matching this shape:
{
  "decision": "APPROVE" | "REVIEW" | "REJECT",
  "confidence_raw": number between 0 and 1,
  "rationale": "short evidence-grounded explanation"
}
"""


# ------------------------------------------------------------------
# Rule-based fallback
# ------------------------------------------------------------------

def _rule_based_decision(state: ReviewState) -> DecisionResult:
    """Deterministic fallback when LLM is unavailable."""
    flags: list[str] = []
    sub_scores: dict[str, float] = {}

    cms = state.get("cms")
    journal_result = state.get("journal_result")
    author_result = state.get("author_result")

    # Metadata completeness
    has_title = bool(cms and cms.title)
    has_authors = bool(cms and cms.authors and cms.authors[0].full_name != "Unknown")
    has_issn = bool(cms and cms.journal.issn_l)
    is_retracted = bool(cms and cms.is_retracted)

    metadata_score = state.get("metadata_score", 0.0)
    journal_score = state.get("journal_score", 0.5)
    author_score = state.get("author_score", 0.5)
    retraction_score = state.get("retraction_score", 1.0)
    policy_score = state.get("policy_score", 1.0)

    confidence_raw = (
        0.25 * metadata_score
        + 0.25 * journal_score
        + 0.30 * author_score
        + 0.10 * retraction_score
        + 0.10 * policy_score
    )

    # Flags
    if is_retracted:
        flags.append("RETRACTED")
    if not has_issn:
        flags.append("MISSING_ISSN")
    if not has_authors:
        flags.append("UNKNOWN_AUTHORS")
    if journal_result:
        flags.extend(journal_result.flags)
    if author_result:
        flags.extend(author_result.flags)

    # De-duplicate
    seen: set[str] = set()
    unique_flags: list[str] = []
    for f in flags:
        if f not in seen:
            seen.add(f)
            unique_flags.append(f)

    sub_scores = {
        "metadata_score": round(metadata_score, 4),
        "journal_score": round(journal_score, 4),
        "author_score": round(author_score, 4),
        "retraction_score": round(retraction_score, 4),
        "policy_score": round(policy_score, 4),
    }

    confidence_calibrated = calibrate_confidence(confidence_raw)

    if is_retracted:
        decision = DecisionLabel.REJECT
        rationale = "Publication has been retracted."
    elif confidence_calibrated >= 0.90:
        decision = DecisionLabel.APPROVE
        rationale = "Evidence strongly supports publication validity."
    elif confidence_calibrated >= 0.65:
        decision = DecisionLabel.REVIEW
        rationale = "Evidence is mixed; manual review recommended."
    else:
        decision = DecisionLabel.REJECT
        rationale = "Insufficient or conflicting evidence for approval."

    return DecisionResult(
        decision=decision,
        confidence_raw=round(confidence_raw, 4),
        confidence_calibrated=round(confidence_calibrated, 4),
        rationale=rationale,
        flags=unique_flags,
        sub_scores=sub_scores,
    )


# ------------------------------------------------------------------
# Prompt builder
# ------------------------------------------------------------------

def _build_evidence_prompt(state: ReviewState) -> str:
    """Build a text block summarizing all evidence for the LLM."""
    parts: list[str] = []

    cms = state.get("cms")
    if cms:
        parts.append(f"DOI: {cms.doi}")
        parts.append(f"Title: {cms.title}")
        parts.append(f"Year: {cms.pub_year}")
        parts.append(f"Journal: {cms.journal.title} (ISSN-L: {cms.journal.issn_l})")
        parts.append(f"Publisher: {cms.journal.publisher}")
        parts.append(f"Authors: {', '.join(a.full_name for a in cms.authors)}")
        parts.append(f"Source: {cms.source_api}")
        parts.append(f"Retracted: {cms.is_retracted}")

    journal_result = state.get("journal_result")
    if journal_result:
        parts.append(f"\nJournal Check:")
        parts.append(f"  Indexes: {', '.join(journal_result.indexes) or 'none'}")
        parts.append(f"  Quartile: {journal_result.quartile_best}")
        parts.append(f"  SJR: {journal_result.sjr_value}")
        parts.append(f"  Predatory: {journal_result.is_predatory}")
        parts.append(f"  Hijacked: {journal_result.is_hijacked}")
        parts.append(f"  Score: {journal_result.score}")

    author_result = state.get("author_result")
    if author_result:
        parts.append(f"\nAuthor Check:")
        parts.append(f"  Claimed: {author_result.user_claimed_name}")
        parts.append(f"  Matched: {author_result.matched_author}")
        parts.append(f"  Method: {author_result.match_method}")
        parts.append(f"  Score: {author_result.match_score}")
        parts.append(f"  ORCID verified: {author_result.orcid_verified}")
        parts.append(f"  Affiliation match: {author_result.affiliation_match}")

    parts.append(f"\nSub-scores:")
    parts.append(f"  Metadata: {state.get('metadata_score', 'N/A')}")
    parts.append(f"  Journal: {state.get('journal_score', 'N/A')}")
    parts.append(f"  Author: {state.get('author_score', 'N/A')}")
    parts.append(f"  Retraction: {state.get('retraction_score', 'N/A')}")
    parts.append(f"  Policy: {state.get('policy_score', 'N/A')}")

    return "\n".join(parts)


# ------------------------------------------------------------------
# LLM call helpers
# ------------------------------------------------------------------

def _parse_decision_json(raw: str, source: str) -> DecisionResult:
    """Parse LLM JSON response into DecisionResult."""
    try:
        data = json.loads(raw)
        if "confidence_raw" in data:
            data["confidence_calibrated"] = calibrate_confidence(float(data["confidence_raw"]))
        # Remove verification_checks if present (not part of DecisionResult)
        data.pop("verification_checks", None)
        return DecisionResult.model_validate(data)
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
        raise LLMGatewayError(f"Invalid {source} response: {exc}") from exc


async def _run_cove(gateway: LLMGateway, state: ReviewState) -> DecisionResult:
    """Chain-of-Verification: generate decision, then verify claims."""
    evidence_text = _build_evidence_prompt(state)
    user_prompt = f"Evaluate this publication evidence:\n{evidence_text}"

    raw = await gateway._call_openrouter(_COVE_SYSTEM_PROMPT, user_prompt)
    result = _parse_decision_json(raw, "CoVe")

    # Penalize confidence for unverified claims
    try:
        data = json.loads(raw)
        checks = data.get("verification_checks", [])
        if checks:
            unverified = sum(1 for c in checks if not c.get("verified", True))
            penalty = unverified * 0.05
            result = DecisionResult(
                decision=result.decision,
                confidence_raw=max(0.0, result.confidence_raw - penalty),
                confidence_calibrated=max(0.0, result.confidence_calibrated - penalty),
                rationale=result.rationale,
                flags=result.flags,
                sub_scores=result.sub_scores,
            )
    except (json.JSONDecodeError, KeyError, TypeError):
        pass  # Use result as-is if verification parsing fails

    return result


async def _run_single(
    gateway: LLMGateway,
    state: ReviewState,
) -> DecisionResult:
    """Single LLM call for self-consistency sampling."""
    evidence_text = _build_evidence_prompt(state)
    user_prompt = f"Evaluate this publication evidence:\n{evidence_text}"

    raw = await gateway._call_openrouter(_SELF_CONSISTENCY_SYSTEM_PROMPT, user_prompt)
    return _parse_decision_json(raw, "self-consistency")


async def _run_self_consistency(
    gateway: LLMGateway,
    state: ReviewState,
    k: int = 3,
) -> DecisionResult:
    """Self-Consistency: run k times, majority-vote label, average confidence."""
    results: list[DecisionResult] = []

    # Run k calls concurrently
    tasks = [_run_single(gateway, state) for _ in range(k)]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    for outcome in outcomes:
        if isinstance(outcome, DecisionResult):
            results.append(outcome)
        elif isinstance(outcome, Exception):
            logger.warning("[decision_agent] Self-consistency call failed: %s", outcome)

    if not results:
        raise LLMGatewayError("All self-consistency calls failed")

    # Majority vote on decision label
    label_counts = Counter(r.decision for r in results)
    majority_label = label_counts.most_common(1)[0][0]

    # Average calibrated confidence
    avg_confidence = sum(r.confidence_calibrated for r in results) / len(results)

    # Pick rationale from the result closest to average confidence
    closest = min(results, key=lambda r: abs(r.confidence_calibrated - avg_confidence))

    # Merge flags from all results
    all_flags: list[str] = []
    seen: set[str] = set()
    for r in results:
        for f in r.flags:
            if f not in seen:
                seen.add(f)
                all_flags.append(f)

    # Merge sub_scores (average)
    merged_sub: dict[str, float] = {}
    for r in results:
        for k_score, v in r.sub_scores.items():
            merged_sub.setdefault(k_score, []).append(v)
    avg_sub = {k: round(sum(v) / len(v), 4) for k, v in merged_sub.items()}

    return DecisionResult(
        decision=majority_label,
        confidence_raw=round(avg_confidence, 4),
        confidence_calibrated=round(calibrate_confidence(avg_confidence), 4),
        rationale=closest.rationale,
        flags=all_flags,
        sub_scores=avg_sub,
    )


# ------------------------------------------------------------------
# Main DecisionAgent class
# ------------------------------------------------------------------

class DecisionAgent:
    """Phase 2 decision agent with CoVe + Self-Consistency."""

    def __init__(self, gateway: LLMGateway | None = None) -> None:
        self._gateway = gateway or LLMGateway()

    async def run(self, state: ReviewState) -> dict:
        """Execute decision logic and return a state update."""
        start = time.monotonic()

        # Apply auto-reject for retracted publications
        cms = state.get("cms")
        if cms and cms.is_retracted:
            result = DecisionResult(
                decision=DecisionLabel.REJECT,
                confidence_raw=0.0,
                confidence_calibrated=0.0,
                rationale="Publication has been retracted.",
                flags=["RETRACTED"],
                sub_scores={"retraction_score": 0.0},
            )
            return {
                "decision": result,
                "timing": _elapsed_timing(state, start),
            }

        if not self._gateway.is_configured:
            result = _rule_based_decision(state)
            return {
                "decision": result,
                "timing": _elapsed_timing(state, start),
            }

        # Try LLM-based decision with retry
        for attempt in range(3):
            try:
                if self._gateway.is_configured:
                    # Check settings for CoVe vs Self-Consistency
                    from reviewagent.config import get_settings
                    settings = get_settings()

                    if settings.llm.cove_enabled:
                        result = await _run_cove(self._gateway, state)
                    else:
                        result = await _run_self_consistency(
                            self._gateway, state, k=settings.llm.self_consistency_k
                        )

                    # Apply thresholds
                    result = _apply_thresholds(result)

                    return {
                        "decision": result,
                        "timing": _elapsed_timing(state, start),
                    }
            except Exception:
                if attempt == 2:
                    logger.warning("[decision_agent] All LLM attempts failed, using rule-based fallback", exc_info=True)
                else:
                    await asyncio.sleep(2 ** attempt)

        # Fallback
        result = _rule_based_decision(state)
        return {
            "decision": result,
            "timing": _elapsed_timing(state, start),
        }


def _apply_thresholds(result: DecisionResult) -> DecisionResult:
    """Apply auto-approve/reject thresholds to the decision."""
    conf = result.confidence_calibrated

    if conf >= 0.90:
        final_label = DecisionLabel.APPROVE
    elif conf >= 0.65:
        final_label = DecisionLabel.REVIEW
    else:
        final_label = DecisionLabel.REJECT

    if final_label != result.decision:
        return DecisionResult(
            decision=final_label,
            confidence_raw=result.confidence_raw,
            confidence_calibrated=result.confidence_calibrated,
            rationale=result.rationale,
            flags=result.flags + ["THRESHOLD_OVERRIDE"],
            sub_scores=result.sub_scores,
        )

    return result


def _elapsed_timing(state: ReviewState, start: float) -> dict[str, float]:
    timing = dict(state.get("timing", {}))
    timing["decision_agent"] = round(time.monotonic() - start, 4)
    return timing
