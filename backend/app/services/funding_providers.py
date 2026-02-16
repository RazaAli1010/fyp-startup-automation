"""Funding Data Providers.

Defines the ``FundingDataProvider`` abstract interface and concrete
implementations.  The funding agent interacts only with the interface,
making the data source swappable without touching business logic.

Providers
---------
- ``RapidAPICrunchbaseProvider`` — queries Crunchbase data via RapidAPI.

Adding a new provider
---------------------
1. Subclass ``FundingDataProvider``.
2. Implement ``get_funding_data``.
3. Register it in ``get_provider()``.
"""

from __future__ import annotations

import abc
import logging
import os
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 10.0  # seconds per request
_MAX_RETRIES = 2
_INITIAL_BACKOFF = 1.5  # seconds


# ===================================================================== #
#  Abstract interface                                                     #
# ===================================================================== #

class FundingDataProvider(abc.ABC):
    """Interface that every funding data source must implement.

    ``get_funding_data`` receives a company name and returns a dict with:
    - ``total_funding_usd`` (float)
    - ``last_funding_type`` (str)
    - ``num_rounds`` (int)          — optional, 0 if unavailable
    - ``last_funding_year`` (int)   — optional, None if unavailable

    Return ``None`` when no data can be found.  Never guess values.
    """

    @abc.abstractmethod
    def get_funding_data(self, company_name: str) -> Optional[Dict]:
        ...


# ===================================================================== #
#  RapidAPI Crunchbase provider                                           #
# ===================================================================== #

class RapidAPICrunchbaseProvider(FundingDataProvider):
    """Fetches funding data from Crunchbase endpoints via RapidAPI."""

    def __init__(self) -> None:
        self._api_key = os.getenv("RAPIDAPI_KEY", "")
        self._api_host = os.getenv("RAPIDAPI_HOST", "")
        if not self._api_key or not self._api_host:
            raise EnvironmentError(
                "RAPIDAPI_KEY and RAPIDAPI_HOST environment variables must "
                "be set to use the RapidAPI Crunchbase provider."
            )
        self._headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": self._api_host,
        }

    # ------------------------------------------------------------------ #
    #  Public                                                              #
    # ------------------------------------------------------------------ #

    def get_funding_data(self, company_name: str) -> Optional[Dict]:
        """Search for *company_name* and return structured funding data.

        Returns ``None`` if the company is not found or on any API error.
        """
        permalink = self._search_organisation(company_name)
        if not permalink:
            return None
        return self._fetch_org_funding(permalink)

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _search_organisation(self, name: str) -> Optional[str]:
        """Search RapidAPI Crunchbase autocomplete for *name*.

        Returns the best-match permalink or ``None``.
        """
        url = f"https://{self._api_host}/autocompletes"
        params = {
            "query": name,
            "collection_ids": "organizations",
            "limit": 5,
        }

        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = httpx.get(
                    url,
                    headers=self._headers,
                    params=params,
                    timeout=_REQUEST_TIMEOUT,
                )
                if resp.status_code == 200:
                    entities = resp.json().get("entities", [])
                    if not entities:
                        return None
                    return entities[0].get("identifier", {}).get("permalink")

                if resp.status_code in (400, 401, 403, 404):
                    logger.warning(
                        "RapidAPI search non-retryable %d for name=%r",
                        resp.status_code,
                        name,
                    )
                    return None

            except httpx.TimeoutException:
                logger.warning(
                    "RapidAPI search timeout attempt %d for name=%r",
                    attempt + 1,
                    name,
                )
            except Exception as exc:
                logger.warning(
                    "RapidAPI search error for name=%r: %s", name, exc
                )
                return None

            if attempt < _MAX_RETRIES:
                import time as _time
                _time.sleep(_INITIAL_BACKOFF * (2 ** attempt))

        return None

    def _fetch_org_funding(self, permalink: str) -> Optional[Dict]:
        """Fetch funding details for an organisation by permalink.

        Returns a dict with ``total_funding_usd``, ``num_rounds``,
        ``last_funding_type``, ``last_funding_year``, or ``None``.
        """
        url = f"https://{self._api_host}/entities/organizations/{permalink}"
        params = {
            "field_ids": (
                "funding_total,"
                "num_funding_rounds,"
                "last_funding_type,"
                "last_funding_at"
            ),
        }

        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = httpx.get(
                    url,
                    headers=self._headers,
                    params=params,
                    timeout=_REQUEST_TIMEOUT,
                )
                if resp.status_code == 200:
                    props = resp.json().get("properties", {})

                    funding_obj = props.get("funding_total", {})
                    total_usd = (
                        funding_obj.get("value_usd", 0)
                        if isinstance(funding_obj, dict)
                        else 0
                    )

                    num_rounds = props.get("num_funding_rounds", 0) or 0

                    last_type = props.get("last_funding_type", "") or ""

                    last_at = props.get("last_funding_at", "") or ""
                    last_year: Optional[int] = None
                    if last_at and len(last_at) >= 4:
                        try:
                            last_year = int(last_at[:4])
                        except ValueError:
                            pass

                    return {
                        "total_funding_usd": float(total_usd or 0),
                        "num_rounds": int(num_rounds),
                        "last_funding_type": last_type,
                        "last_funding_year": last_year,
                    }

                if resp.status_code in (400, 401, 403, 404):
                    logger.warning(
                        "RapidAPI org non-retryable %d for permalink=%r",
                        resp.status_code,
                        permalink,
                    )
                    return None

            except httpx.TimeoutException:
                logger.warning(
                    "RapidAPI org timeout attempt %d for permalink=%r",
                    attempt + 1,
                    permalink,
                )
            except Exception as exc:
                logger.warning(
                    "RapidAPI org error for permalink=%r: %s", permalink, exc
                )
                return None

            if attempt < _MAX_RETRIES:
                import time as _time
                _time.sleep(_INITIAL_BACKOFF * (2 ** attempt))

        return None


# ===================================================================== #
#  Provider factory                                                       #
# ===================================================================== #

def get_provider() -> Optional[FundingDataProvider]:
    """Return the configured ``FundingDataProvider``, or ``None`` in
    fallback mode (no provider configured).

    Selection is driven by the ``FUNDING_PROVIDER`` env var:
    - ``rapidapi`` → ``RapidAPICrunchbaseProvider``
    - unset / empty → ``None`` (graceful fallback)
    """
    provider_name = os.getenv("FUNDING_PROVIDER", "").strip().lower()

    if provider_name == "rapidapi":
        try:
            return RapidAPICrunchbaseProvider()
        except EnvironmentError as exc:
            logger.error("Cannot initialise RapidAPI provider: %s", exc)
            return None

    if provider_name:
        logger.warning(
            "Unknown FUNDING_PROVIDER=%r — falling back to no provider.",
            provider_name,
        )

    return None
