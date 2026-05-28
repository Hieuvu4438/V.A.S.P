from datetime import date, datetime
from typing import Literal
import re

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator


DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", re.IGNORECASE)
ROR_PATTERN = re.compile(r"^https://ror\.org/[0-9a-hjkmnp-tv-z]{9}$", re.IGNORECASE)


class CMSAuthor(BaseModel):
    full_name: str = Field(min_length=1)
    orcid: str | None = None
    affiliation_raw: str | None = None
    ror_id: str | None = None

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Author name must not be empty")
        return normalized

    @field_validator("orcid")
    @classmethod
    def normalize_orcid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        normalized = re.sub(r"^https?://orcid\.org/", "", normalized, flags=re.IGNORECASE)
        if not normalized:
            return None
        if not ORCID_PATTERN.fullmatch(normalized):
            raise ValueError("Invalid ORCID iD")
        return normalized.upper()

    @field_validator("affiliation_raw")
    @classmethod
    def normalize_affiliation_raw(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("ror_id")
    @classmethod
    def normalize_ror_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.startswith("0"):
            normalized = f"https://ror.org/{normalized}"
        if not ROR_PATTERN.fullmatch(normalized):
            raise ValueError("Invalid ROR ID")
        return normalized.lower()


class CMSJournal(BaseModel):
    title: str = Field(min_length=1)
    issn_l: str | None = None
    publisher: str | None = None
    is_scie: bool = False
    is_ssci: bool = False
    is_ahci: bool = False
    is_esci: bool = False
    is_doaj: bool = False
    is_predatory: bool | None = None
    is_hijacked: bool | None = None
    quartile: Literal["Q1", "Q2", "Q3", "Q4"] | None = None
    sjr_value: float | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Journal title must not be empty")
        return normalized

    @field_validator("issn_l", "publisher")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CanonicalMetadataSchema(BaseModel):
    doi: str
    title: str = Field(min_length=1)
    abstract: str | None = None
    article_type: str | None = None
    language: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    pub_year: int = Field(ge=1900, le=2100)
    pub_date: date | None = None
    journal: CMSJournal
    authors: list[CMSAuthor] = Field(min_length=1)
    is_retracted: bool = False
    retraction_doi: str | None = None
    retraction_date: date | None = None
    cms_version: str = "2.0"
    source_api: Literal["crossref", "openalex"]
    source_url: AnyHttpUrl
    fetched_at: datetime

    @field_validator("doi", "retraction_doi")
    @classmethod
    def validate_doi(cls, value: str | None) -> str | None:
        if value is None:
            return None
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

    @field_validator("abstract", "article_type", "language", "volume", "issue", "pages")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("cms_version")
    @classmethod
    def validate_cms_version(cls, value: str) -> str:
        if value != "2.0":
            raise ValueError("cms_version must be 2.0")
        return value

    @model_validator(mode="after")
    def validate_pub_date(self) -> "CanonicalMetadataSchema":
        if self.pub_date is not None and self.pub_date.year != self.pub_year:
            raise ValueError("pub_date year must match pub_year")
        if self.retraction_date is not None and not self.is_retracted:
            raise ValueError("retraction_date requires is_retracted=true")
        if self.retraction_doi is not None and not self.is_retracted:
            raise ValueError("retraction_doi requires is_retracted=true")
        return self
