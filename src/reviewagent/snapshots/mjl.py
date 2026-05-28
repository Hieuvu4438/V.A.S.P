"""Master Journal List (MJL) snapshot — Phase 2 MVP.

Loads a Web of Science MJL CSV into memory for O(1) ISSN-L lookups.
Provides SCIE/SSCI/AHCI/ESCI indexing flags per journal.

CSV expected columns (case-insensitive, flexible):
  issn_l, title, is_scie, is_ssci, is_ahci, is_esci

Alternative column names are also accepted:
  ISSN-L / ISSN / issn → issn_l
  Journal title / Title / Journal → title
  SCIE / is_scie → is_scie  (truthy values: 1, true, yes, x)
  SSCI / is_ssci → is_ssci
  AHCI / is_ahci → is_ahci
  ESCI / is_esci → is_esci
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Column name aliases → canonical field
_ISSN_ALIASES = {"issn_l", "issn", "issnl", "issn-l", "e_issn", "print_issn", "online_issn"}
_TITLE_ALIASES = {"title", "journal", "journal title", "journal_title", "source title", "source_title"}
_SCIE_ALIASES = {"scie", "is_scie", "sci-expanded", "sci expanded", "science citation index expanded"}
_SSCI_ALIASES = {"ssci", "is_ssci", "social sciences citation index"}
_AHCI_ALIASES = {"ahci", "is_ahci", "arts & humanities citation index", "arts and humanities citation index"}
_ESCI_ALIASES = {"esci", "is_esci", "emerging sources citation index"}

_TRUTHY = {"1", "true", "yes", "x", "y"}


@dataclass(frozen=True, slots=True)
class MJLEntry:
    """One journal record from the Master Journal List."""

    issn_l: str
    title: str
    is_scie: bool
    is_ssci: bool
    is_ahci: bool
    is_esci: bool


class MJLSnapshot:
    """In-memory MJL lookup keyed by ISSN-L.

    Usage::

        snap = MJLSnapshot()
        snap.load("snapshots/mjl_current.csv")
        entry = snap.lookup("0018-9448")
    """

    def __init__(self) -> None:
        self._data: dict[str, MJLEntry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def loaded(self) -> bool:
        return len(self._data) > 0

    @property
    def size(self) -> int:
        return len(self._data)

    def load(self, path: str | Path) -> int:
        """Load MJL CSV from *path*. Returns number of journals loaded.

        Raises:
            FileNotFoundError: if *path* does not exist.
            ValueError: if CSV is missing required columns.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"MJL snapshot not found: {path}")

        count = 0
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise ValueError("MJL CSV has no header row")

            col_map = _resolve_columns(list(reader.fieldnames))

            for row in reader:
                entry = _parse_row(row, col_map)
                if entry is not None:
                    self._data[entry.issn_l] = entry
                    count += 1

        logger.info("[mjl] Loaded %d journals from %s", count, path.name)
        return count

    def lookup(self, issn_l: str) -> MJLEntry | None:
        """O(1) lookup by ISSN-L. Returns ``None`` on miss."""
        return self._data.get(issn_l.strip())


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _resolve_columns(headers: list[str]) -> dict[str, str]:
    """Map canonical field names → actual CSV column names."""
    normalized = {h.strip().lower(): h.strip() for h in headers}
    mapping: dict[str, str] = {}

    for canonical, aliases in [
        ("issn_l", _ISSN_ALIASES),
        ("title", _TITLE_ALIASES),
        ("is_scie", _SCIE_ALIASES),
        ("is_ssci", _SSCI_ALIASES),
        ("is_ahci", _AHCI_ALIASES),
        ("is_esci", _ESCI_ALIASES),
    ]:
        for norm_key, actual_col in normalized.items():
            if norm_key in aliases:
                mapping[canonical] = actual_col
                break

    missing = {"issn_l", "title"} - set(mapping)
    if missing:
        raise ValueError(f"MJL CSV missing required columns: {missing}. Found: {headers}")

    return mapping


def _parse_row(row: dict[str, str], col_map: dict[str, str]) -> MJLEntry | None:
    """Build an MJLEntry from a CSV row, or return None if invalid."""
    issn_l = (row.get(col_map.get("issn_l", ""), "") or "").strip()
    if not issn_l:
        return None

    title = (row.get(col_map.get("title", ""), "") or "").strip()

    return MJLEntry(
        issn_l=issn_l,
        title=title,
        is_scie=_is_truthy(row.get(col_map.get("is_scie", ""), "")),
        is_ssci=_is_truthy(row.get(col_map.get("is_ssci", ""), "")),
        is_ahci=_is_truthy(row.get(col_map.get("is_ahci", ""), "")),
        is_esci=_is_truthy(row.get(col_map.get("is_esci", ""), "")),
    )


def _is_truthy(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in _TRUTHY
