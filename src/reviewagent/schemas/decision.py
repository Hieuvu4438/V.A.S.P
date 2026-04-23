from enum import Enum

from pydantic import BaseModel, Field, field_validator


class DecisionLabel(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class DecisionResult(BaseModel):
    decision: DecisionLabel
    confidence_raw: float = Field(ge=0.0, le=1.0)
    confidence_calibrated: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    flags: list[str] = Field(default_factory=list)
    sub_scores: dict[str, float] = Field(default_factory=dict)

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Rationale must not be empty")
        return normalized

    @field_validator("flags")
    @classmethod
    def normalize_flags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for flag in value:
            cleaned = flag.strip()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    @field_validator("sub_scores")
    @classmethod
    def validate_sub_scores(cls, value: dict[str, float]) -> dict[str, float]:
        for key, score in value.items():
            if not key.strip():
                raise ValueError("Sub-score keys must not be empty")
            if not 0.0 <= score <= 1.0:
                raise ValueError("Sub-score values must be between 0 and 1")
        return value
