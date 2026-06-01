from dataclasses import dataclass, field

from pydantic import ValidationError

from reviewagent.connectors.base import ConnectorError
from reviewagent.connectors.crossref import CrossrefConnector
from reviewagent.connectors.openalex import OpenAlexConnector
from reviewagent.schemas.cms import CanonicalMetadataSchema


@dataclass(frozen=True)
class MetadataAgentResult:
    cms: CanonicalMetadataSchema | None
    source: str | None
    needs_review: bool
    errors: list[str] = field(default_factory=list)


async def fetch_metadata_for_doi(
    doi: str,
    crossref: CrossrefConnector | None = None,
    openalex: OpenAlexConnector | None = None,
) -> MetadataAgentResult:
    owns_crossref = crossref is None
    owns_openalex = openalex is None
    crossref = crossref or CrossrefConnector()
    openalex = openalex or OpenAlexConnector()
    errors: list[str] = []

    try:
        try:
            cms = await crossref.lookup(doi)
            if cms is not None:
                return MetadataAgentResult(cms=cms, source="crossref", needs_review=False)
            errors.append("Crossref returned no usable metadata")
        except (ConnectorError, ValidationError) as exc:
            errors.append(f"Crossref lookup failed: {exc}")

        try:
            cms = await openalex.lookup(doi)
            if cms is not None:
                return MetadataAgentResult(cms=cms, source="openalex", needs_review=False, errors=errors)
            errors.append("OpenAlex returned no usable metadata")
        except (ConnectorError, ValidationError) as exc:
            errors.append(f"OpenAlex lookup failed: {exc}")

        return MetadataAgentResult(cms=None, source=None, needs_review=True, errors=errors)
    finally:
        if owns_crossref:
            await crossref.aclose()
        if owns_openalex:
            await openalex.aclose()


class MetadataAgent:
    def __init__(
        self,
        crossref: CrossrefConnector | None = None,
        openalex: OpenAlexConnector | None = None,
    ) -> None:
        self._crossref = crossref
        self._openalex = openalex

    async def run(self, doi: str) -> MetadataAgentResult:
        return await fetch_metadata_for_doi(doi, self._crossref, self._openalex)


async def run(state: dict) -> dict:
    """LangGraph node wrapper — fetches metadata for the DOI in state.

    Accepts a ReviewState dict and returns a state update dict.
    """
    import time

    from reviewagent.agents.state import ReviewState  # noqa: F811

    start = time.monotonic()
    doi = state.get("doi", "")
    if not doi:
        return {
            "cms": None,
            "errors": ["No DOI provided"],
            "metadata_source": None,
            "timing": _elapsed_timing(state, start),
        }

    result = await fetch_metadata_for_doi(doi)

    timing = _elapsed_timing(state, start)
    return {
        "cms": result.cms,
        "errors": list(state.get("errors", [])) + list(result.errors),
        "metadata_source": result.source,
        "timing": timing,
    }


def _elapsed_timing(state: dict, start: float) -> dict[str, float]:
    timing = dict(state.get("timing", {}))
    timing["metadata_agent"] = round(time.monotonic() - start, 4)
    return timing
