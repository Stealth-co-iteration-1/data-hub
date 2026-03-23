"""Nango Records API resource for Dagster assets.

Uses httpx for HTTP client with connection pooling and proper lifecycle management.
"""
from typing import Any

import dagster as dg
import httpx
from httpx import QueryParams
from contextlib import contextmanager
from pydantic import PrivateAttr


class NangoResource(dg.ConfigurableResource["NangoResource"]):
    """Nango Records API client as a Dagster ConfigurableResource.

    Configuration:
        secret_key: Nango secret key from environment (NANGO_SECRET_KEY)
        base_url: API base URL, defaults to https://api.nango.dev
    """

    secret_key: str
    base_url: str = "https://api.nango.dev"

    _client: httpx.Client = PrivateAttr()

    @contextmanager
    def yield_for_execution(self, context: dg.InitResourceContext):
        """Initialize HTTP client for asset execution."""
        with httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.secret_key}"},
            timeout=30.0,
        ) as client:
            self._client = client
            yield self

    def get_records(
        self,
        model: str,
        connection_id: str,
        provider_config_key: str = "salesforce",
    ) -> list[dict[str, Any]]:
        """Fetch all records for a model, handling pagination.

        Args:
            model: Nango model name (e.g., 'Opportunity')
            connection_id: Nango connection identifier
            provider_config_key: Integration ID (default: salesforce)

        Returns:
            List of record dicts with _nango_metadata
        """
        records: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            params = QueryParams(model=model, limit=100)
            if cursor:
                params.set("cursor", cursor)

            response = self._client.get(
                "/records",
                params=params,
                headers={
                    "Connection-Id": connection_id,
                    "Provider-Config-Key": provider_config_key,
                },
            )
            response.raise_for_status()
            data = response.json()

            records.extend(data.get("records", []))

            cursor = data.get("next_cursor")
            if not cursor:
                break

        return records
