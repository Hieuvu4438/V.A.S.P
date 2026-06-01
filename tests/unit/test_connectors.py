from typing import Any
from datetime import date

import pytest

from reviewagent.connectors.base import BaseConnector, ConnectorError
from reviewagent.connectors.crossref import CrossrefConnector
from reviewagent.connectors.doaj import DOAJConnector
from reviewagent.connectors.openalex import OpenAlexConnector
from reviewagent.connectors.orcid import ORCIDConnector
from reviewagent.connectors.retraction_watch import RetractionInfo, RetractionWatchConnector
from reviewagent.snapshots.retraction_watch import RetractionEntry, RetractionWatchSnapshot
from reviewagent.connectors.ror import RORConnector


class DummyConnector(BaseConnector):
    source_name = "dummy"


class DummyResponse:
    def __init__(self, status_code: int, data: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._data = data or {}

    def json(self) -> dict[str, Any]:
        return self._data


class DummyClient:
    def __init__(self, response: DummyResponse) -> None:
        self.response = response
        self.is_closed = False

    async def get(self, path: str, params: dict[str, Any] | None = None) -> DummyResponse:
        return self.response


@pytest.mark.asyncio
async def test_base_connector_treats_404_as_miss() -> None:
    connector = DummyConnector()
    connector._client = DummyClient(DummyResponse(404))  # type: ignore[assignment]

    assert await connector._get("/missing") == {}


@pytest.mark.asyncio
async def test_base_connector_raises_on_500() -> None:
    connector = DummyConnector()
    connector._client = DummyClient(DummyResponse(500))  # type: ignore[assignment]

    with pytest.raises(ConnectorError):
        await connector._get("/error")


def test_crossref_parse_maps_response_to_cms() -> None:
    cms = CrossrefConnector()._parse(
        "10.1000/test",
        {
            "title": ["A grounded paper"],
            "published": {"date-parts": [[2024, 5, 1]]},
            "container-title": ["Journal of Tests"],
            "ISSN-L": "1234-5678",
            "publisher": "Test Publisher",
            "author": [{"given": "Van A", "family": "Nguyen"}],
        },
    )

    assert cms is not None
    assert cms.doi == "10.1000/test"
    assert cms.pub_date == date(2024, 5, 1)
    assert cms.journal.title == "Journal of Tests"
    assert cms.authors[0].full_name == "Van A Nguyen"
    assert cms.source_api == "crossref"


def test_crossref_parse_rejects_missing_required_metadata() -> None:
    assert CrossrefConnector()._parse("10.1000/test", {"title": ["No journal"]}) is None


def test_openalex_parse_maps_response_to_cms() -> None:
    cms = OpenAlexConnector()._parse(
        "10.1000/test",
        {
            "id": "https://openalex.org/W123",
            "title": "A grounded paper",
            "publication_year": 2024,
            "publication_date": "2024-05-01",
            "primary_location": {
                "source": {
                    "display_name": "Journal of Tests",
                    "issn_l": "1234-5678",
                }
            },
            "authorships": [{"author": {"display_name": "Nguyen Van A"}}],
        },
    )

    assert cms is not None
    assert cms.doi == "10.1000/test"
    assert cms.pub_date == date(2024, 5, 1)
    assert cms.journal.issn_l == "1234-5678"
    assert cms.authors[0].full_name == "Nguyen Van A"
    assert cms.source_api == "openalex"

def test_openalex_parse_rejects_missing_required_metadata() -> None:
    assert OpenAlexConnector()._parse("10.1000/test", {"title": "No source", "publication_year": 2024}) is None


def test_ror_parse_maps_affiliation_match() -> None:
    result = RORConnector()._parse(
        {
            "items": [
                {
                    "id": "https://ror.org/03yrm5c26",
                    "names": [
                        {"lang": "en", "types": ["ror_display"], "value": "Posts and Telecommunications Institute of Technology"},
                        {"lang": "vi", "types": ["label"], "value": "Học viện Bưu chính Viễn thông"},
                    ],
                }
            ]
        }
    )

    assert result is not None
    assert result.ror_id == "https://ror.org/03yrm5c26"
    assert result.normalized_name == "Posts and Telecommunications Institute of Technology"


def test_ror_parse_returns_none_on_miss() -> None:
    assert RORConnector()._parse({"items": []}) is None


def _make_retraction_snapshot(*entries: RetractionEntry) -> RetractionWatchSnapshot:
    snap = RetractionWatchSnapshot()
    snap._data = {e.doi: e for e in entries}
    return snap


@pytest.mark.asyncio
async def test_retraction_watch_check_finds_retracted_doi() -> None:
    snap = _make_retraction_snapshot(
        RetractionEntry(
            doi="10.1000/retracted",
            retraction_doi="10.1000/retraction",
            retraction_date=date(2025, 1, 2),
            reason="Data concerns",
        )
    )
    connector = RetractionWatchConnector(snap)
    connector._client = DummyClient(DummyResponse(404))  # type: ignore[assignment]

    info = await connector.check_retraction("10.1000/retracted")

    assert info.retracted is True
    assert info.retraction_doi == "10.1000/retraction"
    assert info.retraction_date == date(2025, 1, 2)
    assert info.reason == "Data concerns"


@pytest.mark.asyncio
async def test_retraction_watch_check_returns_not_retracted_on_miss() -> None:
    snap = _make_retraction_snapshot()
    connector = RetractionWatchConnector(snap)
    connector._client = DummyClient(DummyResponse(404))  # type: ignore[assignment]

    info = await connector.check_retraction("10.1000/missing")

    assert info.retracted is False
    assert info.retraction_doi is None


@pytest.mark.asyncio
async def test_retraction_watch_check_crossref_api_hit() -> None:
    snap = _make_retraction_snapshot()
    connector = RetractionWatchConnector(snap)
    connector._client = DummyClient(DummyResponse(200, {
        "message": {
            "updated-by": [
                {
                    "type": "retraction",
                    "doi": "10.1000/retraction-notice",
                    "date": {"date-parts": [[2025, 1, 2]]},
                    "label": "Retracted due to data concerns"
                }
            ]
        }
    }))  # type: ignore[assignment]

    info = await connector.check_retraction("10.1000/retracted-on-crossref")
    assert info.retracted is True
    assert info.retraction_doi == "10.1000/retraction-notice"
    assert info.retraction_date == date(2025, 1, 2)
    assert info.reason == "Retracted due to data concerns"


@pytest.mark.asyncio
async def test_retraction_watch_check_fallback_on_api_error() -> None:
    snap = _make_retraction_snapshot(
        RetractionEntry(
            doi="10.1000/retracted",
            retraction_doi="10.1000/retraction-notice",
            retraction_date=date(2025, 1, 2),
            reason="Data concerns",
        )
    )
    connector = RetractionWatchConnector(snap)

    class FailingClient:
        is_closed = False
        async def get(self, *args, **kwargs):
            raise Exception("API down")

    connector._client = FailingClient()  # type: ignore[assignment]

    info = await connector.check_retraction("10.1000/retracted")
    assert info.retracted is True
    assert info.retraction_doi == "10.1000/retraction-notice"
    assert info.reason == "Data concerns"


def test_doaj_parse_maps_journal_match() -> None:
    info = DOAJConnector()._parse(
        {
            "results": [
                {
                    "bibjson": {
                        "apc": {"amount": "1200"},
                        "seal": True,
                    }
                }
            ]
        }
    )

    assert info.in_doaj is True
    assert info.apc == 1200.0
    assert info.seal is True


def test_doaj_parse_returns_not_in_doaj_on_miss() -> None:
    info = DOAJConnector()._parse({"results": []})

    assert info.in_doaj is False
    assert info.apc is None
    assert info.seal is False


# --- ORCID connector tests ---


def test_orcid_extract_orcid_ids_parses_results() -> None:
    raw = {
        "result": [
            {"orcid-identifier": {"path": "0000-0001-2345-6789"}},
            {"orcid-identifier": {"path": "0000-0002-9876-5432"}},
        ]
    }
    ids = ORCIDConnector._extract_orcid_ids(raw)
    assert ids == ["0000-0001-2345-6789", "0000-0002-9876-5432"]


def test_orcid_extract_orcid_ids_returns_empty_on_miss() -> None:
    assert ORCIDConnector._extract_orcid_ids({}) == []
    assert ORCIDConnector._extract_orcid_ids({"result": []}) == []


def test_orcid_extract_dois_parses_works() -> None:
    raw = {
        "group": [
            {
                "work-summary": [
                    {
                        "external-ids": {
                            "external-id": [
                                {"external-id-type": "doi", "external-id-value": "10.1000/test123"},
                                {"external-id-type": "eid", "external-id-value": "W123"},
                            ]
                        }
                    }
                ]
            },
            {
                "work-summary": [
                    {
                        "external-ids": {
                            "external-id": [
                                {"external-id-type": "doi", "external-id-value": "10.1000/other456"},
                            ]
                        }
                    }
                ]
            },
        ]
    }
    dois = ORCIDConnector._extract_dois(raw)
    assert dois == ["10.1000/test123", "10.1000/other456"]


def test_orcid_extract_dois_returns_empty_on_miss() -> None:
    assert ORCIDConnector._extract_dois({}) == []
    assert ORCIDConnector._extract_dois({"group": []}) == []


def test_orcid_extract_dois_normalizes_to_lowercase() -> None:
    raw = {
        "group": [
            {
                "work-summary": [
                    {
                        "external-ids": {
                            "external-id": [
                                {"external-id-type": "doi", "external-id-value": "10.1000/ABC"},
                            ]
                        }
                    }
                ]
            }
        ]
    }
    dois = ORCIDConnector._extract_dois(raw)
    assert dois == ["10.1000/abc"]
