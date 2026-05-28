"""ORCID Public API connector — Phase 2 MVP.

Verifies author identity by searching ORCID for a claimed name and
matching the submission DOI against the author's works list.

Auth: OAuth 2.0 client-credentials (public data, no user authorization).
"""

import logging
from typing import Any

import httpx

from reviewagent.connectors.base import BaseConnector, ConnectorError
from reviewagent.schemas.author import AuthorCheckResult
from reviewagent.schemas.cms import DOI_PATTERN

logger = logging.getLogger(__name__)


class ORCIDConnector(BaseConnector):
    """Verify author identity via the ORCID Public API (v3.0)."""

    base_url = "https://pub.orcid.org/v3.0"
    source_name = "orcid"

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        token_url: str = "https://orcid.org/oauth/token",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._access_token: str | None = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def _ensure_token(self) -> None:
        """Obtain or refresh an OAuth 2.0 client-credentials token."""
        if self._access_token is not None:
            return

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as token_client:
                resp = await token_client.post(
                    self._token_url,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "grant_type": "client_credentials",
                        "scope": "/read-public",
                    },
                    headers={"Accept": "application/json"},
                )
        except httpx.TimeoutException as exc:
            raise ConnectorError(self.source_name, f"Token request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise ConnectorError(self.source_name, f"Token request failed: {exc}") from exc

        if resp.status_code != 200:
            raise ConnectorError(
                self.source_name,
                f"OAuth token request failed with status {resp.status_code}",
                status_code=resp.status_code,
            )

        body = resp.json()
        token = body.get("access_token")
        if not token:
            raise ConnectorError(self.source_name, "No access_token in OAuth response")

        self._access_token = str(token)

    def _build_client(self) -> httpx.AsyncClient:
        # Token is injected per-request in _request; base client has no auth header.
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self._timeout,
            headers={"Accept": "application/json"},
            follow_redirects=True,
        )

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Authenticated GET that attaches the Bearer token."""
        await self._ensure_token()
        assert self._access_token is not None  # for type checker
        try:
            resp = await self.client.get(
                path,
                params=params,
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
        except httpx.TimeoutException as exc:
            raise ConnectorError(self.source_name, f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise ConnectorError(self.source_name, f"Network error: {exc}") from exc

        if resp.status_code == 404:
            logger.debug("[orcid] 404 for %s — treating as miss", path)
            return {}

        if resp.status_code >= 500:
            raise ConnectorError(
                self.source_name, f"Server error {resp.status_code} for {path}", status_code=resp.status_code
            )

        if resp.status_code >= 400:
            raise ConnectorError(
                self.source_name, f"Client error {resp.status_code} for {path}", status_code=resp.status_code
            )

        try:
            return resp.json()  # type: ignore[no-any-return]
        except Exception as exc:
            raise ConnectorError(self.source_name, f"Failed to parse JSON: {exc}") from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search_author(self, name: str, doi: str) -> AuthorCheckResult:
        """Search ORCID for *name* and verify *doi* appears in their works.

        Returns an ``AuthorCheckResult`` with ``orcid_verified=True`` only when
        the DOI is found in the matched ORCID profile's works list.
        """
        name = name.strip()
        if not name:
            return AuthorCheckResult(
                user_claimed_name=name,
                match_method="none",
                match_score=0.0,
                orcid_verified=False,
                affiliation_match=False,
                flags=["EMPTY_NAME"],
            )

        orcid_ids = await self._search_orcid(name)
        if not orcid_ids:
            logger.info("[orcid] No profiles found for name: %s", name)
            return AuthorCheckResult(
                user_claimed_name=name,
                match_method="none",
                match_score=0.0,
                orcid_verified=False,
                affiliation_match=False,
                flags=["NO_ORCID_PROFILE"],
            )

        for orcid_id in orcid_ids:
            doi_match, dois_found = await self._check_works(orcid_id, doi)
            if doi_match:
                logger.info("[orcid] DOI %s verified via ORCID %s", doi, orcid_id)
                return AuthorCheckResult(
                    user_claimed_name=name,
                    match_method="orcid",
                    match_score=1.0,
                    orcid_verified=True,
                    affiliation_match=False,
                    evidence={"orcid_id": orcid_id, "dois_checked": dois_found},
                )

        logger.info("[orcid] DOI %s not found in %d ORCID profile(s)", doi, len(orcid_ids))
        return AuthorCheckResult(
            user_claimed_name=name,
            match_method="none",
            match_score=0.0,
            orcid_verified=False,
            affiliation_match=False,
            flags=["DOI_NOT_IN_ORCID_WORKS"],
            evidence={"orcid_ids_checked": orcid_ids},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _search_orcid(self, name: str) -> list[str]:
        """Return ORCID iDs matching *name* via the search endpoint."""
        parts = name.split(None, 1)
        given = parts[0] if len(parts) >= 1 else ""
        family = parts[1] if len(parts) >= 2 else ""

        params: dict[str, str] = {}
        if family:
            params["given-names"] = given
            params["family-name"] = family
        else:
            params["q"] = f'given-names:"{given}" OR family-name:"{given}"'

        raw = await self._request("/search", params=params)
        return self._extract_orcid_ids(raw)

    @staticmethod
    def _extract_orcid_ids(raw: dict[str, Any]) -> list[str]:
        """Parse ORCID iDs from a search response."""
        results = raw.get("result")
        if not isinstance(results, list):
            return []

        ids: list[str] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            orcid_id = item.get("orcid-identifier", {}).get("path")
            if orcid_id:
                ids.append(str(orcid_id))
        return ids

    async def _check_works(self, orcid_id: str, doi: str) -> tuple[bool, list[str]]:
        """Check whether *doi* appears in the works of *orcid_id*.

        Returns (doi_matched, list_of_dois_found).
        """
        try:
            raw = await self._request(f"/{orcid_id}/works")
        except ConnectorError:
            logger.warning("[orcid] Failed to fetch works for %s", orcid_id, exc_info=True)
            return False, []

        dois = self._extract_dois(raw)
        doi_lower = doi.strip().lower()
        return doi_lower in dois, dois

    @staticmethod
    def _extract_dois(raw: dict[str, Any]) -> list[str]:
        """Extract all DOIs from an ORCID works response."""
        dois: list[str] = []
        for group in raw.get("group", []):
            for summary in group.get("work-summary", []):
                ext_ids = summary.get("external-ids", {}).get("external-id", [])
                for ext_id in ext_ids:
                    if ext_id.get("external-id-type") == "doi":
                        value = ext_id.get("external-id-value")
                        if value:
                            dois.append(str(value).strip().lower())
        return dois
