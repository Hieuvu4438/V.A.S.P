from dataclasses import dataclass, field
from uuid import UUID

from reviewagent.schemas.cms import CanonicalMetadataSchema
from reviewagent.schemas.decision import DecisionResult


@dataclass
class ReviewState:
    submission_id: UUID
    doi: str
    cms: CanonicalMetadataSchema | None = None
    decision: DecisionResult | None = None
    errors: list[str] = field(default_factory=list)
    metadata_source: str | None = None
    prompt_version: str = "decision_v1"
