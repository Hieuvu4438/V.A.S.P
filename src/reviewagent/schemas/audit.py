from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AuditEntry(BaseModel):
    entry_id: str = Field(min_length=1)
    timestamp: datetime
    event_type: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    submission_id: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)
    hmac_hash: str = Field(min_length=1)
    prev_hash: str = Field(min_length=1)

    @field_validator("entry_id", "event_type", "actor", "submission_id", "hmac_hash", "prev_hash")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized
