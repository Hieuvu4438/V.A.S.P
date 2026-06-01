"""Retraction Watch offline snapshot.

Loads a retracted-DOI CSV into memory for O(1) lookups by DOI.

CSV expected columns (case-insensitive, flexible):
  doi, retraction_doi, retraction_date, reason

Alternative column names are also accepted:
  DOI / OriginalDOI / original_doi → doi
  RetractionDOI / retraction_notice_doi / notice_doi → retraction_doi
  RetractionDate / retraction_date / date → retraction_date
  Reason / retraction_reason / RetractionReason → reason
"""

import csv
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

_DOI_ALIASES = {"doi", "originaldoi", "original_doi", "original doi"}
_RETRACTION_DOI_ALIASES = {
    "retraction_doi",
    "retractiondoi",
    "retraction doi",
    "retraction notice doi",
    "retraction_notice_doi",
    "notice_doi",
    "notice doi",
}
_RETRACTION_DATE_ALIASES = {
    "retraction_date",
    "retractiondate",
    "retraction date",
    "date",
}
_REASON_ALIASES = {"reason", "retraction_reason", "retractionreason", "retraction reason"}


@dataclass(frozen=True, slots=True)
class RetractionEntry:
    """One retraction record."""

    doi: str
    retraction_doi: str | None
    retraction_date: date | None
    reason: str | None


class RetractionWatchSnapshot:
    """In-memory retraction lookup keyed by normalized DOI.

    Usage::

        snap = RetractionWatchSnapshot()
        snap.load("snapshots/retraction_watch.csv")
        entry = snap.lookup("10.1000/example")
    """

    def __init__(self) -> None:
        self._data: dict[str, RetractionEntry] = {}

    @property
    def loaded(self) -> bool:
        return len(self._data) > 0

    @property
    def size(self) -> int:
        return len(self._data)

    def load(self, path: str | Path) -> int:
        """Load retraction CSV from *path*. Returns number of entries loaded.

        Raises:
            FileNotFoundError: if *path* does not exist.
            ValueError: if CSV is missing required columns.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Retraction Watch snapshot not found: {path}")

        temp_data: dict[str, RetractionEntry] = {}
        count = 0
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise ValueError("Retraction Watch CSV has no header row")

            col_map = _resolve_columns(list(reader.fieldnames))

            for row in reader:
                entry = _parse_row(row, col_map)
                if entry is not None:
                    temp_data[entry.doi] = entry
                    count += 1

        self._data = temp_data
        logger.info("[retraction_watch] Loaded %d entries from %s", count, path.name)
        return count

    def lookup(self, doi: str) -> RetractionEntry | None:
        """O(1) lookup by normalized DOI. Returns ``None`` on miss."""
        normalized = doi.strip().lower()
        if normalized.startswith("doi:"):
            normalized = normalized[4:]
        return self._data.get(normalized)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _resolve_columns(headers: list[str]) -> dict[str, str]:
    """Map canonical field names to actual CSV column names."""
    normalized = {h.strip().lower(): h.strip() for h in headers}
    mapping: dict[str, str] = {}

    for canonical, aliases in [
        ("doi", _DOI_ALIASES),
        ("retraction_doi", _RETRACTION_DOI_ALIASES),
        ("retraction_date", _RETRACTION_DATE_ALIASES),
        ("reason", _REASON_ALIASES),
    ]:
        for norm_key, actual_col in normalized.items():
            if norm_key in aliases:
                mapping[canonical] = actual_col
                break

    missing = {"doi"} - set(mapping)
    if missing:
        raise ValueError(f"Retraction Watch CSV missing required columns: {missing}. Found: {headers}")

    return mapping


def _parse_row(row: dict[str, str], col_map: dict[str, str]) -> RetractionEntry | None:
    """Build a RetractionEntry from a CSV row, or return None if invalid."""
    doi_raw = (row.get(col_map.get("doi", ""), "") or "").strip()
    if not doi_raw:
        return None

    doi = doi_raw.lower()
    if doi.startswith("doi:"):
        doi = doi[4:]

    retraction_doi = _optional_text(row, col_map, "retraction_doi")
    retraction_date = _parse_date(_optional_text(row, col_map, "retraction_date"))
    reason = _optional_text(row, col_map, "reason")

    return RetractionEntry(
        doi=doi,
        retraction_doi=retraction_doi,
        retraction_date=retraction_date,
        reason=reason,
    )


def _optional_text(row: dict[str, str], col_map: dict[str, str], field: str) -> str | None:
    col_name = col_map.get(field)
    if not col_name:
        return None
    value = (row.get(col_name, "") or "").strip()
    return value or None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
