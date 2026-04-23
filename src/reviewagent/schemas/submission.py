from enum import Enum
from uuid import UUID
import re

from pydantic import BaseModel, field_validator


DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


class SubmissionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SubmissionCreateRequest(BaseModel):
    doi: str

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, value: str) -> str:
        normalized = value.strip()
        normalized = re.sub(r"^doi:\s*", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", normalized, flags=re.IGNORECASE)
        normalized = normalized.strip()
        if not DOI_PATTERN.fullmatch(normalized):
            raise ValueError("Invalid DOI")
        return normalized.lower()


class SubmissionCreateResponse(BaseModel):
    submission_id: UUID
    status: SubmissionStatus
    decision_id: UUID | None = None
