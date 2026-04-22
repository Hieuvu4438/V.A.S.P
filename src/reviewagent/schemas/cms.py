from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date
import unicodedata, re

class CMSAuthor(BaseModel):
    raw_name: str
    normalized_name: str  # NFC + title case
    orcid: Optional[str] = None
    affiliation_raw: Optional[str] = None
    ror_id: Optional[str] = None  # từ api.ror.org
    and_score: Optional[float] = None  # [0,1]

class CMSJournal(BaseModel):
    issn_l: str           # ISSN-L canonical
    issn_print: Optional[str] = None
    issn_electronic: Optional[str] = None
    title: str
    publisher: Optional[str] = None
    is_scie: bool = False
    is_ssci: bool = False
    is_ahci: bool = False
    is_esci: bool = False
    is_doaj: bool = False
    is_predatory: Optional[bool] = None
    is_hijacked: Optional[bool] = None
    quartile_pub_year: Optional[str] = None  # Q1/Q2/Q3/Q4 theo năm công bố
    sjr_value: Optional[float] = None
    source: str  # "crossref" | "openalex"

class CanonicalMetadataSchema(BaseModel):
    # Identifiers
    doi: str = Field(pattern=r"^10\..+/.+$")
    doi_url: str
    
    # Bibliographic
    title: str
    abstract: Optional[str] = None
    pub_year: int = Field(ge=1900, le=2030)
    pub_date: Optional[date] = None
    article_type: Optional[str] = None  # "journal-article", "proceedings", etc.
    language: Optional[str] = None

    # Journal
    journal: CMSJournal
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None

    # Authors
    authors: List[CMSAuthor] = Field(min_length=1)
    
    # Flags
    is_retracted: bool = False
    retraction_doi: Optional[str] = None
    retraction_date: Optional[date] = None
    
    # Provenance — bắt buộc ghi nguồn
    source_api: str  # "crossref" | "openalex" | "fuzzy_match"
    source_url: str  # URL gọi thực tế
    fetched_at: str  # ISO datetime
    cms_version: str = "1.0"
