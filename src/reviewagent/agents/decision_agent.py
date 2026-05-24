from dataclasses import dataclass
from typing import Any

from reviewagent.llm.gateway import LLMGateway
from reviewagent.schemas.cms import CanonicalMetadataSchema
from reviewagent.schemas.decision import DecisionLabel, DecisionResult


@dataclass
class DecisionAgentResult:
    decision: DecisionResult
    source: str  # "llm" | "rule"


def _cms_to_input(cms: CanonicalMetadataSchema) -> dict[str, Any]:
    return {
        "doi": cms.doi,
        "title": cms.title,
        "pub_year": cms.pub_year,
        "pub_date": str(cms.pub_date) if cms.pub_date else None,
        "journal": {
            "title": cms.journal.title,
            "issn_l": cms.journal.issn_l,
            "publisher": cms.journal.publisher,
        },
        "authors": [{"full_name": a.full_name} for a in cms.authors],
        "is_retracted": cms.is_retracted,
        "source_api": cms.source_api,
    }


def _rule_based_decision(cms: CanonicalMetadataSchema, errors: list[str] | None = None) -> DecisionResult:
    flags: list[str] = []
    sub_scores: dict[str, float] = {}

    has_issn = cms.journal.issn_l is not None
    has_publisher = cms.journal.publisher is not None
    has_authors = len(cms.authors) > 0 and cms.authors[0].full_name != "Unknown"
    is_retracted = cms.is_retracted

    metadata_score = 0.5
    if has_issn:
        metadata_score += 0.25
    if has_publisher:
        metadata_score += 0.25
    sub_scores["metadata_completeness"] = metadata_score

    source_score = 0.8 if cms.source_api == "crossref" else 0.6
    sub_scores["source_reliability"] = source_score

    confidence_raw = 0.5 * metadata_score + 0.5 * source_score

    if is_retracted:
        confidence_raw = 0.1
        flags.append("RETRACTED")

    if not has_issn:
        flags.append("MISSING_ISSN")
    if not has_publisher:
        flags.append("MISSING_PUBLISHER")
    if not has_authors:
        flags.append("UNKNOWN_AUTHORS")

    if errors:
        flags.extend(errors)

    if is_retracted:
        decision = DecisionLabel.REJECT
        rationale = "Publication has been retracted."
    elif confidence_raw >= 0.75:
        decision = DecisionLabel.APPROVE
        rationale = "Metadata is reasonably complete from an authoritative source."
    elif confidence_raw >= 0.5:
        decision = DecisionLabel.REVIEW
        rationale = "Metadata is partially complete; manual review recommended."
    else:
        decision = DecisionLabel.REVIEW
        rationale = "Insufficient metadata for automated approval."

    return DecisionResult(
        decision=decision,
        confidence_raw=round(confidence_raw, 4),
        confidence_calibrated=round(confidence_raw, 4),
        rationale=rationale,
        flags=flags,
        sub_scores=sub_scores,
    )


class DecisionAgent:
    def __init__(self, gateway: LLMGateway | None = None) -> None:
        self._gateway = gateway or LLMGateway()

    async def run(self, cms: CanonicalMetadataSchema, errors: list[str] | None = None) -> DecisionAgentResult:
        input_data = _cms_to_input(cms)

        if not self._gateway.is_configured:
            result = _rule_based_decision(cms, errors)
            return DecisionAgentResult(decision=result, source="rule")

        try:
            result = await self._gateway.generate_decision_v1(input_data)
            return DecisionAgentResult(decision=result, source="llm")
        except Exception:
            result = _rule_based_decision(cms, errors)
            return DecisionAgentResult(decision=result, source="rule")
