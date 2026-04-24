"""Crossref REST API connector — Phase 1 PoC.

Looks up a paper by DOI and normalises the response into a
CanonicalMetadataSchema. Returns ``None`` on a 404 (valid miss).
"""

import logging
import urllib.parse
from datetime import date, datetime, timezone
from typing import Any

from reviewagent.connectors.base import BaseConnector, ConnectorError  # noqa: F401 (re-exported)
from reviewagent.schemas.cms import CMSAuthor, CMSJournal, CanonicalMetadataSchema

logger = logging.getLogger(__name__)


class CrossrefConnector(BaseConnector):
    """Fetch publication metadata from the Crossref REST API."""

    base_url = "https://api.crossref.org"
    source_name = "crossref"

    # Crossref requests a polite mailto in the User-Agent.
    # Set via CROSSREF_MAILTO env var or override at construction time.
    def __init__(self, mailto: str = "reviewagent@ptit.edu.vn", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._mailto = mailto

    def _build_client(self) -> Any:
        client = super()._build_client()
        # Crossref polite pool: add mailto to User-Agent
        client.headers.update({"User-Agent": f"ReviewAgentPTIT/0.1 (mailto:{self._mailto})"})
        return client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def lookup(self, doi: str) -> CanonicalMetadataSchema | None:
        """Look up a DOI via the Crossref Works API.

        Returns:
            A populated ``CanonicalMetadataSchema`` on hit, ``None`` on 404.

        Raises:
            ConnectorError: on network or server errors.
        """
        encoded_doi = urllib.parse.quote(doi, safe="")
        path = f"/works/{encoded_doi}"
        raw = await self._get(path)

        if not raw:
            # _get returns {} on 404
            logger.info("[crossref] No result for DOI: %s", doi)
            return None

        message = raw.get("message", {})
        if not message:
            logger.warning("[crossref] Empty message body for DOI: %s", doi)
            return None

        return self._parse(doi, message)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse(self, doi: str, msg: dict[str, Any]) -> CanonicalMetadataSchema | None:
        title_list: list[str] = msg.get("title", [])
        if not title_list:
            logger.warning("[crossref] Missing title for DOI: %s", doi)
            return None
        title = title_list[0].strip()

        pub_year, pub_date = self._extract_date(msg)
        if pub_year is None:
            logger.warning("[crossref] Cannot determine publication year for DOI: %s", doi)
            return None

        journal_title = self._extract_journal_title(msg)
        if not journal_title:
            logger.warning("[crossref] Missing journal title for DOI: %s", doi)
            return None

        issn_l = self._extract_issn(msg)
        publisher = msg.get("publisher")

        authors = self._extract_authors(msg)

        source_url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"

        try:
            return CanonicalMetadataSchema(
                doi=doi,
                title=title,
                pub_year=pub_year,
                pub_date=pub_date,
                journal=CMSJournal(
                    title=journal_title,
                    issn_l=issn_l,
                    publisher=publisher,
                ),
                authors=authors if authors else [CMSAuthor(full_name="Unknown")],
                source_api="crossref",
                source_url=source_url,  # type: ignore[arg-type]
                fetched_at=datetime.now(tz=timezone.utc),
            )
        except Exception as exc:
            logger.error("[crossref] Failed to build CMS for DOI %s: %s", doi, exc)
            return None

    def _extract_date(self, msg: dict[str, Any]) -> tuple[int | None, date | None]:
        """Return (pub_year, pub_date). pub_date may be None if only year is known."""
        for field in ("published", "published-print", "published-online", "issued"):
            date_parts = msg.get(field, {}).get("date-parts", [])
            if date_parts and date_parts[0]:
                parts = date_parts[0]
                year = parts[0] if len(parts) >= 1 else None
                if year is None:
                    continue
                try:
                    if len(parts) >= 3:
                        return int(year), date(int(parts[0]), int(parts[1]), int(parts[2]))
                    return int(year), None
                except (ValueError, TypeError):
                    continue
        return None, None

    def _extract_journal_title(self, msg: dict[str, Any]) -> str | None:
        container = msg.get("container-title", [])
        if container and container[0]:
            return container[0].strip()
        short = msg.get("short-container-title", [])
        if short and short[0]:
            return short[0].strip()
        return None

    def _extract_issn(self, msg: dict[str, Any]) -> str | None:
        issn_l = msg.get("ISSN-L") or msg.get("issn-l")
        if issn_l:
            return str(issn_l)
        issn_list = msg.get("ISSN", [])
        if issn_list:
            return str(issn_list[0])
        return None

    def _extract_authors(self, msg: dict[str, Any]) -> list[CMSAuthor]:
        authors: list[CMSAuthor] = []
        for author in msg.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            name = author.get("name", "").strip()

            if family and given:
                full = f"{given} {family}"
            elif family:
                full = family
            elif name:
                full = name
            else:
                continue

            if full:
                authors.append(CMSAuthor(full_name=full))
        return authors
