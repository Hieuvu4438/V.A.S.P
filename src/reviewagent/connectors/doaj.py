import logging
from typing import Any

from pydantic import BaseModel

from reviewagent.connectors.base import BaseConnector, ConnectorError  # noqa: F401 (re-exported)

logger = logging.getLogger(__name__)


class DOAJJournalInfo(BaseModel):
    in_doaj: bool
    apc: float | None = None
    seal: bool = False


class DOAJConnector(BaseConnector):
    """Check whether a journal ISSN is present in DOAJ."""

    base_url = "https://doaj.org"
    source_name = "doaj"

    async def check_journal(self, issn_l: str) -> DOAJJournalInfo:
        normalized_issn = issn_l.strip()
        if not normalized_issn:
            raise ValueError("ISSN-L must not be empty")

        raw = await self._get(f"/api/v2/search/journals/issn:{normalized_issn}")
        result = self._parse(raw)
        if not result.in_doaj:
            logger.info("[doaj] Journal not found for ISSN-L: %s", issn_l)
        return result

    def _parse(self, raw: dict[str, Any]) -> DOAJJournalInfo:
        records = raw.get("results") or raw.get("items") or []
        if not isinstance(records, list) or not records:
            return DOAJJournalInfo(in_doaj=False)

        first = records[0]
        if not isinstance(first, dict):
            return DOAJJournalInfo(in_doaj=False)

        bibjson = first.get("bibjson") if isinstance(first.get("bibjson"), dict) else first
        apc = self._extract_apc(bibjson)
        seal = bool(bibjson.get("seal") or bibjson.get("doaj_seal"))
        return DOAJJournalInfo(in_doaj=True, apc=apc, seal=seal)

    def _extract_apc(self, record: dict[str, Any]) -> float | None:
        value = record.get("apc")
        if isinstance(value, dict):
            value = value.get("amount")
        if isinstance(value, list) and value:
            first = value[0]
            value = first.get("amount") if isinstance(first, dict) else first
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
