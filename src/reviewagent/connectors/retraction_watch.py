import logging
from datetime import date
from typing import Any

from pydantic import BaseModel

from reviewagent.connectors.base import ConnectorError  # noqa: F401 (re-exported)
from reviewagent.schemas.cms import DOI_PATTERN
from reviewagent.snapshots.retraction_watch import RetractionWatchSnapshot

logger = logging.getLogger(__name__)


class RetractionInfo(BaseModel):
    retracted: bool
    retraction_doi: str | None = None
    retraction_date: date | None = None
    reason: str | None = None


class RetractionWatchConnector:
    """Check DOI retraction status against an offline Retraction Watch snapshot."""

    source_name = "retraction_watch"

    def __init__(self, snapshot: RetractionWatchSnapshot) -> None:
        self._snapshot = snapshot

    def check_retraction(self, doi: str) -> RetractionInfo:
        normalized_doi = doi.strip().lower()
        if not DOI_PATTERN.fullmatch(normalized_doi):
            raise ValueError("Invalid DOI")

        entry = self._snapshot.lookup(normalized_doi)
        if entry is None:
            logger.info("[retraction_watch] No retraction found for DOI: %s", doi)
            return RetractionInfo(retracted=False)

        return RetractionInfo(
            retracted=True,
            retraction_doi=entry.retraction_doi,
            retraction_date=entry.retraction_date,
            reason=entry.reason,
        )
