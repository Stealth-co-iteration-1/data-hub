"""Nango API client for fetching synced records.

Uses httpx for async HTTP requests to the Nango Records API.
"""

from typing import Any

import httpx

from src.config.settings import settings
from src.observability.logging import get_logger

logger = get_logger(__name__)


class NangoClient:
    """Client for Nango Records API.

    Fetches synced records after webhook notification.
    Handles pagination via cursor-based approach.
    """

    def __init__(
        self,
        base_url: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize Nango client.

        Args:
            base_url: Nango API base URL (defaults to settings)
            secret_key: Nango Secret Key for auth (defaults to settings)
        """
        self._base_url = base_url or settings.nango_base_url
        self._secret_key = secret_key or settings.nango_secret_key

    async def fetch_records(
        self,
        model: str,
        connection_id: str,
        provider_config_key: str = "salesforce",
        cursor: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Fetch synced records from Nango.

        Args:
            model: The model/sync name (e.g., "Opportunity", "Task")
            connection_id: The Nango connection ID
            provider_config_key: Integration provider key (default: "salesforce")
            cursor: Pagination cursor for fetching next page
            limit: Maximum records per page (default: 100)

        Returns:
            Dict with "records" list and optional "next_cursor" for pagination

        Raises:
            httpx.HTTPStatusError: On API errors
        """
        params: dict[str, Any] = {
            "model": model,
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor

        headers = {
            "Authorization": f"Bearer {self._secret_key}",
            "Provider-Config-Key": provider_config_key,
            "Connection-Id": connection_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._base_url}/records",
                headers=headers,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def fetch_all_records(
        self,
        model: str,
        connection_id: str,
        provider_config_key: str = "salesforce",
    ) -> list[dict[str, Any]]:
        """Fetch all synced records, handling pagination.

        Args:
            model: The model/sync name (e.g., "Opportunity", "Task")
            connection_id: The Nango connection ID
            provider_config_key: Integration provider key (default: "salesforce")

        Returns:
            List of all records across all pages
        """
        all_records: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            result = await self.fetch_records(
                model=model,
                connection_id=connection_id,
                provider_config_key=provider_config_key,
                cursor=cursor,
            )

            records = result.get("records", [])
            all_records.extend(records)

            logger.debug(
                "nango_records_fetched",
                model=model,
                connection_id=connection_id,
                batch_size=len(records),
                total_so_far=len(all_records),
            )

            cursor = result.get("next_cursor")
            if not cursor:
                break

        logger.info(
            "nango_records_fetch_complete",
            model=model,
            connection_id=connection_id,
            total_records=len(all_records),
        )

        return all_records
