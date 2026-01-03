# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Prometheus client for querying metrics.

Adapted from Dynamo Planner utils/prometheus.py.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PrometheusClient:
    """Client for querying Prometheus metrics."""

    def __init__(
        self,
        prometheus_url: str,
        namespace: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        Initialize Prometheus client.

        Args:
            prometheus_url: URL of Prometheus server (e.g., "http://localhost:9090")
            namespace: Namespace for filtering queries
            model_name: Model name for filtering queries
        """
        self.prometheus_url = prometheus_url.rstrip("/")
        self.namespace = namespace
        self.model_name = model_name
        self._session = None

        logger.info(
            f"Prometheus client initialized: url={prometheus_url}, "
            f"namespace={namespace}, model={model_name}"
        )

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None:
            import aiohttp

            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def query(self, query: str) -> Optional[float]:
        """
        Execute a Prometheus query and return scalar result.

        Args:
            query: PromQL query string

        Returns:
            Float value or None if query fails
        """
        try:
            session = await self._get_session()
            url = f"{self.prometheus_url}/api/v1/query"
            params = {"query": query}

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(
                        f"Prometheus query failed: {response.status} {await response.text()}"
                    )
                    return None

                data = await response.json()
                if data["status"] != "success":
                    logger.error(f"Prometheus query error: {data}")
                    return None

                result = data["data"]["result"]
                if not result:
                    logger.debug(f"Prometheus query returned no results: {query}")
                    return None

                # Extract scalar value
                value = float(result[0]["value"][1])
                return value

        except Exception as e:
            logger.error(f"Prometheus query exception: {e}", exc_info=True)
            return None

    def _build_label_filters(self) -> str:
        """Build label filters for queries."""
        filters = []
        if self.namespace:
            filters.append(f'namespace="{self.namespace}"')
        if self.model_name:
            # Normalize model name (lowercase, as per MDC convention)
            model = self.model_name.lower()
            filters.append(f'model="{model}"')

        return ",".join(filters) if filters else ""

    async def get_avg_time_to_first_token(self, interval: str) -> Optional[float]:
        """
        Get average Time To First Token over interval.

        Args:
            interval: Time interval (e.g., "60s", "5m")

        Returns:
            Average TTFT in seconds, or None
        """
        label_filters = self._build_label_filters()
        if label_filters:
            label_filters = "{" + label_filters + "}"

        query = f"avg_over_time(vllm:time_to_first_token_seconds{label_filters}[{interval}])"
        result = await self.query(query)
        logger.debug(f"TTFT query result: {result}")
        return result

    async def get_avg_inter_token_latency(self, interval: str) -> Optional[float]:
        """
        Get average Inter-Token Latency over interval.

        Args:
            interval: Time interval (e.g., "60s", "5m")

        Returns:
            Average ITL in seconds, or None
        """
        label_filters = self._build_label_filters()
        if label_filters:
            label_filters = "{" + label_filters + "}"

        query = f"avg_over_time(vllm:time_per_output_token_seconds{label_filters}[{interval}])"
        result = await self.query(query)
        logger.debug(f"ITL query result: {result}")
        return result

    async def get_avg_request_count(self, interval: str) -> Optional[float]:
        """
        Get average request count over interval.

        Args:
            interval: Time interval (e.g., "60s", "5m")

        Returns:
            Average request count, or None
        """
        label_filters = self._build_label_filters()
        if label_filters:
            label_filters = "{" + label_filters + "}"

        query = f"rate(vllm:request_success_total{label_filters}[{interval}]) * {interval[:-1]}"
        result = await self.query(query)
        logger.debug(f"Request count query result: {result}")
        return result

    async def get_avg_input_sequence_tokens(self, interval: str) -> Optional[float]:
        """
        Get average input sequence length over interval.

        Args:
            interval: Time interval (e.g., "60s", "5m")

        Returns:
            Average ISL in tokens, or None
        """
        label_filters = self._build_label_filters()
        if label_filters:
            label_filters = "{" + label_filters + "}"

        query = f"avg_over_time(vllm:prompt_tokens{label_filters}[{interval}])"
        result = await self.query(query)
        logger.debug(f"ISL query result: {result}")
        return result

    async def get_avg_output_sequence_tokens(self, interval: str) -> Optional[float]:
        """
        Get average output sequence length over interval.

        Args:
            interval: Time interval (e.g., "60s", "5m")

        Returns:
            Average OSL in tokens, or None
        """
        label_filters = self._build_label_filters()
        if label_filters:
            label_filters = "{" + label_filters + "}"

        query = f"avg_over_time(vllm:generation_tokens{label_filters}[{interval}])"
        result = await self.query(query)
        logger.debug(f"OSL query result: {result}")
        return result

    async def get_avg_request_duration(self, interval: str) -> Optional[float]:
        """
        Get average request duration over interval.

        Args:
            interval: Time interval (e.g., "60s", "5m")

        Returns:
            Average duration in seconds, or None
        """
        label_filters = self._build_label_filters()
        if label_filters:
            label_filters = "{" + label_filters + "}"

        query = f"avg_over_time(vllm:request_duration_seconds{label_filters}[{interval}])"
        result = await self.query(query)
        logger.debug(f"Request duration query result: {result}")
        return result
