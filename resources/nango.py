"""Nango Records API resource for Dagster assets.

Uses httpx for HTTP client with connection pooling and proper lifecycle management.
"""

import time
from contextlib import contextmanager
from typing import Any

import dagster as dg
import httpx
from pydantic import PrivateAttr


class NangoResource(dg.ConfigurableResource["NangoResource"]):
    """Nango Records API client as a Dagster ConfigurableResource.

    Configuration:
        secret_key: Nango secret key from environment (NANGO_SECRET_KEY)
        base_url: API base URL, defaults to https://api.nango.dev
    """

    secret_key: str
    base_url: str = "https://api.nango.dev"
    max_retries: int = 5
    base_delay: float = 1.0

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

    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with exponential backoff retry on 429."""
        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            response = self._client.request(method, url, **kwargs)

            if response.status_code == 429:
                # Get retry-after header or use exponential backoff
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    delay = float(retry_after)
                else:
                    delay = self.base_delay * (2**attempt)

                dg.get_dagster_logger().warning(
                    f"Rate limited (429). Waiting {delay:.1f}s before retry {attempt + 1}/{self.max_retries}"
                )
                time.sleep(delay)
                continue

            response.raise_for_status()
            return response

        # If we exhausted retries on 429, raise the last response
        if last_exception:
            raise last_exception
        raise httpx.HTTPStatusError(
            "Max retries exceeded for rate limit",
            request=response.request,
            response=response,
        )

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
            params: dict[str, Any] = {"model": model, "limit": 100}
            if cursor:
                params["cursor"] = cursor

            response = self._request_with_retry(
                "GET",
                "/records",
                params=params,
                headers={
                    "Connection-Id": connection_id,
                    "Provider-Config-Key": provider_config_key,
                },
            )
            data = response.json()

            records.extend(data.get("records", []))

            cursor = data.get("next_cursor")
            if not cursor:
                break

        return records
