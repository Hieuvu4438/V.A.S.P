"""Beall's List snapshot — Phase 2 MVP.

Loads a predatory-journal CSV into memory for O(1) ISSN and title
lookups.  A journal is flagged predatory when its ISSN-L or a
normalised variant of its title appears in the snapshot.

CSV expected columns (case-insensitive, flexible):
  issn, title

Alternative column names:
  ISSN / ISSN-L / issn_l / Issn / e-ISSN → issn
  Title / Journal / Journal Title / Journal Title / Name → title
  Publisher → (ignored for matching, loaded only if present)
"""

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_ISSN_ALIASES = {"issn", "issn_l", "issnl", "issn-l", "e-issn", "print issn", "online issn", "Issn"}
_TITLE_ALIASES = {"title", "journal", "journal title", "journal_title", "name", "source title"}


class BeallSnapshot:
    """In-memory predatory-journal lookup.

    Usage::

        snap = BeallSnapshot()
        snap.load("snapshots/beall.csv")
        snap.is_predatory("1234-5678", "Journal of Predatory Research")
    """

    def __init__(self) -> None:
        self._issns: set[str] = set()
        self._titles: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def loaded(self) -> bool:
        return len(self._issns) > 0 or len(self._titles) > 0

    @property
    def size(self) -> int:
        return len(self._issns)

    def load(self, path: str | Path) -> int:
        """Load Beall CSV from *path*. Returns number of entries loaded.

        Raises:
            FileNotFoundError: if *path* does not exist.
            ValueError: if CSV has no header row.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Beall snapshot not found: {path}")

        count = 0
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise ValueError("Beall CSV has no header row")

            col_map = _resolve_columns(list(reader.fieldnames))

            for row in reader:
                issn = (row.get(col_map.get("issn", ""), "") or "").strip()
                title = (row.get(col_map.get("title", ""), "") or "").strip()

                if issn:
                    self._issns.add(issn)
                    count += 1
                if title:
                    self._titles.add(_normalise_title(title))

        logger.info("[beall] Loaded %d predatory entries from %s", count, path.name)
        return count

    def is_predatory(self, issn_l: str, title: str) -> bool:
        """Return ``True`` if *issn_l* or *title* matches a predatory entry.

        Both parameters may be empty — the check is skipped for empty values.
        Title comparison is case-insensitive and strips whitespace.
        """
        if issn_l and issn_l.strip() in self._issns:
            return True

        if title and _normalise_title(title) in self._titles:
            return True

        return False


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _resolve_columns(headers: list[str]) -> dict[str, str]:
    """Map canonical field names → actual CSV column names."""
    normalized = {h.strip().lower(): h.strip() for h in headers}
    mapping: dict[str, str] = {}

    for canonical, aliases in [
        ("issn", _ISSN_ALIASES),
        ("title", _TITLE_ALIASES),
    ]:
        for norm_key, actual_col in normalized.items():
            if norm_key in aliases:
                mapping[canonical] = actual_col
                break

    # At least one of issn or title must be present
    if "issn" not in mapping and "title" not in mapping:
        raise ValueError(
            f"Beall CSV must have at least an ISSN or Title column. Found: {headers}"
        )

    return mapping


def _normalise_title(title: str) -> str:
    """Lowercase, collapse whitespace, strip."""
    return " ".join(title.lower().split())
