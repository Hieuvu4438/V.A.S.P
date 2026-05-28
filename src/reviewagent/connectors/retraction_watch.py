import logging
from datetime import date
from typing import Any

from pydantic import BaseModel

from reviewagent.connectors.base import BaseConnector, ConnectorError  # noqa: F401 (re-exported)
from reviewagent.schemas.cms import DOI_PATTERN

logger = logging.getLogger(__name__)


class RetractionInfo(BaseModel):
    retracted: bool
    retraction_doi: str | None = None
    retraction_date: date | None = None
    reason: str | None = None


class RetractionWatchConnector(BaseConnector):
    """Check DOI retraction status through Retraction Watch-style data."""

    base_url = "https://api.retractionwatch.com"
    source_name = "retraction_watch"

    async def check_retraction(self, doi: str) -> RetractionInfo:
        normalized_doi = doi.strip().lower()
        if not DOI_PATTERN.fullmatch(normalized_doi):
            raise ValueError("Invalid DOI")

        raw = await self._get("/api/retractions", params={"doi": normalized_doi})
        info = self._parse(raw)
        if not info.retracted:
            logger.info("[retraction_watch] No retraction found for DOI: %s", doi)
        return info

    def _parse(self, raw: dict[str, Any]) -> RetractionInfo:
        records = self._extract_records(raw)
        if not records:
            return RetractionInfo(retracted=False)

        first = records[0]
        retraction_doi = self._first_text(first, "retraction_doi", "retractionDOI", "RetractionDOI", "notice_doi")
        retraction_date = self._parse_date(
            self._first_text(first, "retraction_date", "retractionDate", "RetractionDate", "date")
        )
        reason = self._first_text(first, "reason", "Reason", "retraction_reason", "RetractionReason")

        return RetractionInfo(
            retracted=True,
            retraction_doi=retraction_doi,
            retraction_date=retraction_date,
            reason=reason,
        )

    def _extract_records(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        for key in ("items", "results", "retractions", "data"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if raw.get("retracted") is True:
            return [raw]
        return []

    def _first_text(self, record: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = record.get(key)
            if value is None:
                continue
            normalized = str(value).strip()
            if normalized:
                return normalized
        return None

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
