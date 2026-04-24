"""OpenAlex API connector — Phase 1 PoC.

Looks up a paper by DOI and normalises the response into a
CanonicalMetadataSchema. Used as fallback when Crossref returns no result
or is missing key fields.
"""

import logging
import urllib.parse
from datetime import date, datetime, timezone
from typing import Any

from reviewagent.connectors.base import BaseConnector, ConnectorError  # noqa: F401 (re-exported)
from reviewagent.schemas.cms import CMSAuthor, CMSJournal, CanonicalMetadataSchema

logger = logging.getLogger(__name__)


class OpenAlexConnector(BaseConnector):
    """Fetch publication metadata from the OpenAlex API."""

    base_url = "https://api.openalex.org"
    source_name = "openalex"

    def __init__(self, mailto: str = "reviewagent@ptit.edu.vn", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._mailto = mailto

    def _build_client(self) -> Any:
        client = super()._build_client()
        client.headers.update({"User-Agent": f"ReviewAgentPTIT/0.1 (mailto:{self._mailto})"})
        return client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def lookup(self, doi: str) -> CanonicalMetadataSchema | None:
        """Look up a DOI via the OpenAlex Works API.

        Returns:
            A populated ``CanonicalMetadataSchema`` on hit, ``None`` on 404.

        Raises:
            ConnectorError: on network or server errors.
        """
        # OpenAlex accepts DOIs as filter: works?filter=doi:<doi>
        # or directly as works/doi:<doi> — the filter approach is more robust.
        encoded_doi = urllib.parse.quote(doi, safe="")
        path = f"/works/https://doi.org/{encoded_doi}"
        raw = await self._get(path, params={"mailto": self._mailto})

        if not raw:
            # _get returns {} on 404
            logger.info("[openalex] No result for DOI: %s", doi)
            return None

        return self._parse(doi, raw)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse(self, doi: str, work: dict[str, Any]) -> CanonicalMetadataSchema | None:
        title = (work.get("title") or "").strip()
        if not title:
            logger.warning("[openalex] Missing title for DOI: %s", doi)
            return None

        pub_year, pub_date = self._extract_date(work)
        if pub_year is None:
            logger.warning("[openalex] Cannot determine publication year for DOI: %s", doi)
            return None

        journal_title, issn_l = self._extract_journal(work)
        if not journal_title:
            logger.warning("[openalex] Missing journal/source title for DOI: %s", doi)
            return None

        authors = self._extract_authors(work)

        openalex_id: str = work.get("id", "")
        source_url = openalex_id if openalex_id.startswith("http") else f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi, safe='')}"

        try:
            return CanonicalMetadataSchema(
                doi=doi,
                title=title,
                pub_year=pub_year,
                pub_date=pub_date,
                journal=CMSJournal(
                    title=journal_title,
                    issn_l=issn_l,
                    publisher=None,  # OpenAlex doesn't always surface publisher at work level
                ),
                authors=authors if authors else [CMSAuthor(full_name="Unknown")],
                source_api="openalex",
                source_url=source_url,  # type: ignore[arg-type]
                fetched_at=datetime.now(tz=timezone.utc),
            )
        except Exception as exc:
            logger.error("[openalex] Failed to build CMS for DOI %s: %s", doi, exc)
            return None

    def _extract_date(self, work: dict[str, Any]) -> tuple[int | None, date | None]:
        """Return (pub_year, pub_date). pub_date may be None if only year is known."""
        pub_year_raw = work.get("publication_year")
        pub_date_raw = work.get("publication_date")  # ISO 8601 string e.g. "2023-05-01"

        pub_year: int | None = None
        pub_date: date | None = None

        if pub_year_raw is not None:
            try:
                pub_year = int(pub_year_raw)
            except (ValueError, TypeError):
                pass

        if pub_date_raw:
            try:
                parsed = date.fromisoformat(str(pub_date_raw))
                pub_date = parsed
                if pub_year is None:
                    pub_year = parsed.year
            except ValueError:
                pass

        return pub_year, pub_date

    def _extract_journal(self, work: dict[str, Any]) -> tuple[str | None, str | None]:
        """Return (journal_title, issn_l) from primary location or best-match source."""
        # primary_location -> source is the canonical journal info in OpenAlex
        primary = work.get("primary_location") or {}
        source = primary.get("source") or {}

        title = (source.get("display_name") or "").strip() or None
        issn_l = source.get("issn_l") or None

        if not title:
            # Fall back to first location with a named source
            for loc in work.get("locations", []):
                src = loc.get("source") or {}
                t = (src.get("display_name") or "").strip()
                if t:
                    title = t
                    issn_l = src.get("issn_l") or issn_l
                    break

        return title, issn_l

    def _extract_authors(self, work: dict[str, Any]) -> list[CMSAuthor]:
        authors: list[CMSAuthor] = []
        for authorship in work.get("authorships", []):
            author_info = authorship.get("author") or {}
            display_name = (author_info.get("display_name") or "").strip()
            if display_name:
                authors.append(CMSAuthor(full_name=display_name))
        return authors
