import logging
import urllib.parse
from datetime import date
from typing import Any

from pydantic import BaseModel

from reviewagent.connectors.base import BaseConnector, ConnectorError  # noqa: F401 (re-exported)
from reviewagent.schemas.cms import DOI_PATTERN
from reviewagent.snapshots.retraction_watch import RetractionWatchSnapshot

logger = logging.getLogger(__name__)


class RetractionInfo(BaseModel):
    retracted: bool
    retraction_doi: str | None = None
    retraction_date: date | None = None
    reason: str | None = None


class RetractionWatchConnector(BaseConnector):
    """Check DOI retraction status using Crossref API primarily, fallback to offline snapshot."""

    base_url = "https://api.crossref.org"
    source_name = "retraction_watch"

    def __init__(self, snapshot: RetractionWatchSnapshot, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._snapshot = snapshot

    async def check_retraction(self, doi: str) -> RetractionInfo:
        normalized_doi = doi.strip().lower()
        if not DOI_PATTERN.fullmatch(normalized_doi):
            raise ValueError("Invalid DOI")

        # 1. Try checking via Crossref API first
        try:
            encoded_doi = urllib.parse.quote(normalized_doi, safe="")
            raw = await self._get(f"/works/{encoded_doi}")
            if raw:
                message = raw.get("message", {})
                retraction_info = self._parse_crossref_message(message)
                if retraction_info.retracted:
                    logger.info("[retraction_watch] DOI %s verified retracted via Crossref API", doi)
                    return retraction_info
        except Exception as exc:
            logger.warning(
                "[retraction_watch] Crossref API check failed for DOI %s, falling back to offline snapshot: %s",
                doi,
                exc,
            )

        # 2. Fallback to offline snapshot
        entry = self._snapshot.lookup(normalized_doi)
        if entry is None:
            logger.info("[retraction_watch] No retraction found in offline snapshot for DOI: %s", doi)
            return RetractionInfo(retracted=False)

        logger.info("[retraction_watch] DOI %s verified retracted via offline snapshot", doi)
        return RetractionInfo(
            retracted=True,
            retraction_doi=entry.retraction_doi,
            retraction_date=entry.retraction_date,
            reason=entry.reason,
        )

    def _parse_crossref_message(self, msg: dict[str, Any]) -> RetractionInfo:
        """Parse Crossref API work metadata response for retraction records."""
        updates = msg.get("updated-by") or []
        for update in updates:
            if not isinstance(update, dict):
                continue
            if update.get("type") == "retraction":
                retraction_doi = update.get("doi")
                retraction_date = None

                # Parse date if available
                date_block = update.get("date", {})
                date_parts = date_block.get("date-parts", [])
                if date_parts and date_parts[0]:
                    parts = date_parts[0]
                    try:
                        if len(parts) >= 3:
                            retraction_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                        elif len(parts) >= 1:
                            retraction_date = date(int(parts[0]), 1, 1)
                    except (ValueError, TypeError):
                        pass

                reason = update.get("label") or "Retracted"
                return RetractionInfo(
                    retracted=True,
                    retraction_doi=retraction_doi,
                    retraction_date=retraction_date,
                    reason=reason,
                )
        return RetractionInfo(retracted=False)
