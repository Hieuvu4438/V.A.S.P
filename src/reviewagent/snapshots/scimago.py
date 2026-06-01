"""SCImago SJR snapshot — Phase 2 MVP.

Loads a SCImago Journal Rank CSV into memory for quartile/SJR lookups
by ISSN-L and publication year.

CSV expected columns (case-insensitive, flexible):
  issn, title, sjr, quartile, year

Alternative column names are also accepted:
  ISSN / ISSN-L / issn_l / Issn → issn
  Title / Source / Source title / Journal → title
  SJR / SJR Value / sjr_value → sjr
  SJR Best Quartile / Best Quartile / Quartile / sjr_best_quartile → quartile
  Year / Coverage year / coverage_year → year

SCImago CSVs are typically per-year files.  When the *year* column is
absent the caller passes ``default_year`` to :meth:`load`.
"""

import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from reviewagent.snapshots.issn_utils import normalize_issn

logger = logging.getLogger(__name__)

_ISSN_ALIASES = {"issn", "issn_l", "issnl", "issn-l", "e-issn", "print issn", "online issn", "Issn"}
_TITLE_ALIASES = {"title", "source", "source title", "source_title", "journal", "journal title"}
_SJR_ALIASES = {"sjr", "sjr value", "sjr_value", "sjr indicator"}
_QUARTILE_ALIASES = {"sjr best quartile", "best quartile", "quartile", "sjr_best_quartile", "q"}
_YEAR_ALIASES = {"year", "coverage year", "coverage_year"}

_VALID_QUARTILES = {"Q1", "Q2", "Q3", "Q4"}


@dataclass(frozen=True, slots=True)
class SCImagoEntry:
    """One year-specific journal record from SCImago."""

    issn_l: str
    year: int
    sjr_value: float
    quartile: str  # Q1 / Q2 / Q3 / Q4


class SCImagoSnapshot:
    """In-memory SCImago lookup keyed by (issn_l, year).

    Usage::

        snap = SCImagoSnapshot()
        snap.load("snapshots/scimago_jcr.csv", default_year=2023)
        entry = snap.lookup("0018-9448", 2023)
    """

    def __init__(self) -> None:
        # key: (issn_l_normalized, year)
        self._data: dict[tuple[str, int], SCImagoEntry] = {}
        # key: issn_l_normalized -> SCImagoEntry (most recent year)
        self._best_data: dict[str, SCImagoEntry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def loaded(self) -> bool:
        return len(self._data) > 0

    @property
    def size(self) -> int:
        return len(self._data)

    def load(self, path: str | Path, default_year: int | None = None) -> int:
        """Load SCImago CSV from *path*. Returns number of entries loaded.

        Args:
            path: Path to the CSV file.
            default_year: Used when the CSV lacks a *year* column.

        Raises:
            FileNotFoundError: if *path* does not exist.
            ValueError: if CSV is missing required columns or *default_year*
                is needed but not provided.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"SCImago snapshot not found: {path}")

        # Auto-detect delimiter from the header line
        with path.open("r", encoding="utf-8-sig") as f:
            first_line = f.readline()
            delimiter = ";" if ";" in first_line else ","

        temp_data: dict[tuple[str, int], SCImagoEntry] = {}
        temp_best_data: dict[str, SCImagoEntry] = {}
        count = 0
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter=delimiter)
            if reader.fieldnames is None:
                raise ValueError("SCImago CSV has no header row")

            col_map = _resolve_columns(list(reader.fieldnames))
            has_year = "year" in col_map

            if not has_year and default_year is None:
                raise ValueError(
                    "SCImago CSV has no year column and no default_year was provided"
                )

            for row in reader:
                entry = _parse_row(row, col_map, default_year)
                if entry is not None:
                    # Support multiple ISSNs separated by comma or semicolon
                    issns = [p.strip() for p in re.split(r"[,;]+", entry.issn_l) if p.strip()]
                    for single_issn in issns:
                        norm_issn = normalize_issn(single_issn)
                        if not norm_issn:
                            continue

                        # Store specific entry for each normalized ISSN
                        specific_entry = SCImagoEntry(
                            issn_l=single_issn,  # Store the original ISSN as reference
                            year=entry.year,
                            sjr_value=entry.sjr_value,
                            quartile=entry.quartile,
                        )

                        temp_data[(norm_issn, entry.year)] = specific_entry

                        # Update best year entry
                        existing_best = temp_best_data.get(norm_issn)
                        if existing_best is None or specific_entry.year > existing_best.year:
                            temp_best_data[norm_issn] = specific_entry

                        count += 1

        # Atomic assignment
        self._data = temp_data
        self._best_data = temp_best_data

        logger.info("[scimago] Loaded %d entries from %s", count, path.name)
        return count

    def lookup(self, issn_l: str, year: int) -> SCImagoEntry | None:
        """Lookup by ISSN-L + year. Returns ``None`` on miss."""
        return self._data.get((normalize_issn(issn_l), year))

    def lookup_best(self, issn_l: str) -> SCImagoEntry | None:
        """Return the most recent entry for *issn_l* (any year)."""
        return self._best_data.get(normalize_issn(issn_l))


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
        ("sjr", _SJR_ALIASES),
        ("quartile", _QUARTILE_ALIASES),
        ("year", _YEAR_ALIASES),
    ]:
        for norm_key, actual_col in normalized.items():
            if norm_key in aliases:
                mapping[canonical] = actual_col
                break

    missing = {"issn_l", "sjr", "quartile"} - set(mapping)
    if missing:
        raise ValueError(f"SCImago CSV missing required columns: {missing}. Found: {headers}")

    return mapping


def _parse_row(
    row: dict[str, str],
    col_map: dict[str, str],
    default_year: int | None,
) -> SCImagoEntry | None:
    """Build a SCImagoEntry from a CSV row, or return None if invalid."""
    issn_l = (row.get(col_map.get("issn_l", ""), "") or "").strip()
    if not issn_l:
        return None

    # Parse SJR value
    sjr_raw = (row.get(col_map.get("sjr", ""), "") or "").strip()
    sjr_raw = sjr_raw.replace(",", ".")
    try:
        sjr_value = float(sjr_raw)
    except (ValueError, TypeError):
        return None

    # Parse quartile
    quartile = (row.get(col_map.get("quartile", ""), "") or "").strip().upper()
    if quartile not in _VALID_QUARTILES:
        return None

    # Parse year
    year: int | None = None
    if "year" in col_map:
        year_raw = (row.get(col_map["year"], "") or "").strip()
        try:
            year = int(year_raw)
        except (ValueError, TypeError):
            year = default_year
    else:
        year = default_year

    if year is None:
        return None

    return SCImagoEntry(
        issn_l=issn_l,
        year=year,
        sjr_value=sjr_value,
        quartile=quartile,
    )
