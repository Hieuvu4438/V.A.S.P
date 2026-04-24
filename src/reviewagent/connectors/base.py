"""Base HTTP connector shared by Crossref and OpenAlex connectors."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default timeouts (seconds): connect, read, write, pool
_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)


class ConnectorError(Exception):
    """Raised when a connector encounters a non-recoverable HTTP or network error."""

    def __init__(self, source: str, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.source = source
        self.status_code = status_code


class BaseConnector:
    """Minimal async HTTP base class for external metadata connectors.

    Subclasses should set ``base_url`` and call ``self._get()`` for requests.
    The client is created lazily and shared across calls within the same instance.
    Callers are responsible for closing via ``aclose()`` or using as a context manager.
    """

    base_url: str = ""
    source_name: str = "unknown"

    def __init__(self, timeout: httpx.Timeout = _DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self._timeout,
            headers={"Accept": "application/json"},
            follow_redirects=True,
        )

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = self._build_client()
        return self._client

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform a GET request and return the parsed JSON body.

        Returns:
            Parsed JSON as a dict.

        Raises:
            ConnectorError: on HTTP 5xx, network errors, or unexpected response formats.
            Returns ``{}`` implicitly — callers handle 404 themselves (not raised here).
        """
        url = path
        try:
            response = await self.client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise ConnectorError(self.source_name, f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise ConnectorError(self.source_name, f"Network error: {exc}") from exc

        if response.status_code == 404:
            logger.debug("[%s] 404 for %s — treating as miss", self.source_name, url)
            return {}

        if response.status_code >= 500:
            raise ConnectorError(
                self.source_name,
                f"Server error {response.status_code} for {url}",
                status_code=response.status_code,
            )

        if response.status_code >= 400:
            raise ConnectorError(
                self.source_name,
                f"Client error {response.status_code} for {url}",
                status_code=response.status_code,
            )

        try:
            return response.json()  # type: ignore[no-any-return]
        except Exception as exc:
            raise ConnectorError(self.source_name, f"Failed to parse JSON response: {exc}") from exc

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "BaseConnector":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
