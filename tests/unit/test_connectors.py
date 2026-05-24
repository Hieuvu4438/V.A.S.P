from typing import Any
from datetime import date

import pytest

from reviewagent.connectors.base import BaseConnector, ConnectorError
from reviewagent.connectors.crossref import CrossrefConnector
from reviewagent.connectors.openalex import OpenAlexConnector


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
