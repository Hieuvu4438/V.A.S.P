from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class JournalCheckResult(BaseModel):
    issn_l: str = Field(min_length=1)
    title: str = Field(min_length=1)
    is_indexed: bool
    indexes: list[str] = Field(default_factory=list)
    quartile_best: Literal["Q1", "Q2", "Q3", "Q4"] | None = None
    sjr_value: float | None = None
    is_predatory: bool | None = None
    is_hijacked: bool | None = None
    flags: list[str] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=1.0)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("issn_l", "title")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized

    @field_validator("indexes", "flags")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            cleaned = item.strip()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized
