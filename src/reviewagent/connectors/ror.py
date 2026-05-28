import logging
from typing import Any

from pydantic import BaseModel, Field

from reviewagent.connectors.base import BaseConnector, ConnectorError  # noqa: F401 (re-exported)

logger = logging.getLogger(__name__)


class RORLookupResult(BaseModel):
    ror_id: str = Field(min_length=1)
    normalized_name: str = Field(min_length=1)


class RORConnector(BaseConnector):
    """Resolve raw affiliation names through the ROR Organizations API."""

    base_url = "https://api.ror.org"
    source_name = "ror"

    async def lookup(self, affiliation_name: str) -> tuple[str, str] | None:
        normalized_query = affiliation_name.strip()
        if not normalized_query:
            return None

        raw = await self._get("/v1/organizations", params={"affiliation": normalized_query})
        result = self._parse(raw)
        if result is None:
            logger.info("[ror] No organization match for affiliation: %s", affiliation_name)
            return None
        return result.ror_id, result.normalized_name

    def _parse(self, raw: dict[str, Any]) -> RORLookupResult | None:
        items = raw.get("items") or []
        if not items:
            return None

        first = items[0]
        organization = first.get("organization") if isinstance(first, dict) else None
        org = organization if isinstance(organization, dict) else first
        if not isinstance(org, dict):
            return None

        ror_id = (org.get("id") or "").strip()
        name = (org.get("name") or "").strip()
        if not ror_id or not name:
            return None

        try:
            return RORLookupResult(ror_id=ror_id, normalized_name=name)
        except ValueError:
            return None
