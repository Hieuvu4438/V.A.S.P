from datetime import date, datetime
from typing import Literal
import re

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator


DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


class CMSAuthor(BaseModel):
    full_name: str = Field(min_length=1)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Author name must not be empty")
        return normalized


class CMSJournal(BaseModel):
    title: str = Field(min_length=1)
    issn_l: str | None = None
    publisher: str | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Journal title must not be empty")
        return normalized


class CanonicalMetadataSchema(BaseModel):
    doi: str
    title: str = Field(min_length=1)
    pub_year: int = Field(ge=1900, le=2100)
    pub_date: date | None = None
    journal: CMSJournal
    authors: list[CMSAuthor] = Field(min_length=1)
    is_retracted: bool = False
    source_api: Literal["crossref", "openalex"]
    source_url: AnyHttpUrl
    fetched_at: datetime

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

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Title must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_pub_date(self) -> "CanonicalMetadataSchema":
        if self.pub_date is not None and self.pub_date.year != self.pub_year:
            raise ValueError("pub_date year must match pub_year")
        return self
