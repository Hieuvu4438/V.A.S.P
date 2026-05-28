from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AuthorCheckResult(BaseModel):
    user_claimed_name: str = Field(min_length=1)
    user_claimed_affiliation: str | None = None
    matched_author: str | None = None
    match_method: Literal["orcid", "and_exact", "and_fuzzy", "none"]
    match_score: float = Field(ge=0.0, le=1.0)
    orcid_verified: bool
    affiliation_match: bool
    flags: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("user_claimed_name")
    @classmethod
    def normalize_user_claimed_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("User claimed name must not be empty")
        return normalized

    @field_validator("user_claimed_affiliation", "matched_author")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("flags")
    @classmethod
    def normalize_flags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            cleaned = item.strip()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized
