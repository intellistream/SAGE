# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Metrics collector for gathering system performance metrics.

Supports multiple collection methods:
- Prometheus: Query metrics from Prometheus server
- Direct: Collect directly from execution instances
- Mock: For testing purposes

Adapted from Dynamo Planner prometheus.py and metrics collection.
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """
    System performance metrics for autoscaling decisions.

    All metrics are averaged over the collection interval.
    """

    # Request metrics
    num_requests: float = 0.0  # Number of requests in interval
    avg_isl: float = 0.0  # Average input sequence length (tokens)
    avg_osl: float = 0.0  # Average output sequence length (tokens)

    # Latency metrics (milliseconds)
    avg_ttft_ms: Optional[float] = None  # Average Time To First Token
    avg_itl_ms: Optional[float] = None  # Average Inter-Token Latency

    # Instance counts
    num_prefill_instances: int = 0
    num_decode_instances: int = 0

    # Request duration (seconds)
    request_duration_sec: Optional[float] = None

    # Throughput metrics
    prefill_throughput_tokens_per_sec: float = 0.0
    decode_throughput_tokens_per_sec: float = 0.0

    def is_valid(self) -> bool:
        """
        Check if metrics are valid for autoscaling decisions.

        Metrics are valid if we have:
        - Non-zero requests
        - Valid ISL and OSL
        - Valid TTFT and ITL
        """
        return (
            self.num_requests > 0
            and self.avg_isl > 0
            and self.avg_osl > 0
            and self.avg_ttft_ms is not None
            and self.avg_itl_ms is not None
            and not math.isnan(self.avg_ttft_ms)
            and not math.isnan(self.avg_itl_ms)
            and not math.isnan(self.avg_isl)
            and not math.isnan(self.avg_osl)
        )

    def __repr__(self) -> str:
        return (
            f"SystemMetrics(requests={self.num_requests:.1f}, "
            f"isl={self.avg_isl:.1f}, osl={self.avg_osl:.1f}, "
            f"ttft={self.avg_ttft_ms:.1f}ms, itl={self.avg_itl_ms:.1f}ms)"
        )


class MetricsCollector:
    """
    Metrics collector for autoscaling.

    Collects metrics from Prometheus or directly from instances.
    """

    def __init__(
        self,
        prometheus_url: Optional[str] = None,
        namespace: Optional[str] = None,
        model_name: Optional[str] = None,
        executor_coordinator=None,
    ):
        """
        Initialize the metrics collector.

        Args:
            prometheus_url: URL of Prometheus server (e.g., "http://localhost:9090")
            namespace: Namespace for Prometheus queries
            model_name: Model name for filtering metrics
            executor_coordinator: ExecutionCoordinator instance for direct collection
        """
        self.prometheus_url = prometheus_url
        self.namespace = namespace
        self.model_name = model_name
        self.executor_coordinator = executor_coordinator

        # Determine collection method
        if prometheus_url:
            self.collection_method = "prometheus"
            from .utils.prometheus_client import PrometheusClient

            self.prometheus_client = PrometheusClient(prometheus_url, namespace, model_name)
            logger.info(f"Metrics collector using Prometheus at {prometheus_url}")
        elif executor_coordinator:
            self.collection_method = "direct"
            logger.info("Metrics collector using direct instance polling")
        else:
            self.collection_method = "mock"
            logger.warning("No metrics source configured, using mock data")

    async def collect_metrics(self, interval_sec: int = 60) -> SystemMetrics:
        """
        Collect system metrics.

        Args:
            interval_sec: Time interval for metrics aggregation

        Returns:
            SystemMetrics with collected data
        """
        if self.collection_method == "prometheus":
            return await self._collect_from_prometheus(interval_sec)
        elif self.collection_method == "direct":
            return await self._collect_from_instances()
        else:
            return self._collect_mock_metrics()

    async def _collect_from_prometheus(self, interval_sec: int) -> SystemMetrics:
        """
        Collect metrics from Prometheus.

        Args:
            interval_sec: Query interval in seconds

        Returns:
            SystemMetrics populated from Prometheus
        """
        try:
            interval_str = f"{interval_sec}s"

            # Query Prometheus metrics (converted from seconds to milliseconds)
            ttft = await self.prometheus_client.get_avg_time_to_first_token(interval_str)
            itl = await self.prometheus_client.get_avg_inter_token_latency(interval_str)
            num_req = await self.prometheus_client.get_avg_request_count(interval_str)
            isl = await self.prometheus_client.get_avg_input_sequence_tokens(interval_str)
            osl = await self.prometheus_client.get_avg_output_sequence_tokens(interval_str)
            req_duration = await self.prometheus_client.get_avg_request_duration(interval_str)

            metrics = SystemMetrics(
                num_requests=num_req if num_req else 0.0,
                avg_isl=isl if isl else 0.0,
                avg_osl=osl if osl else 0.0,
                avg_ttft_ms=ttft * 1000 if ttft else None,  # Convert to ms
                avg_itl_ms=itl * 1000 if itl else None,  # Convert to ms
                request_duration_sec=req_duration,
            )

            # Get instance counts from executor if available
            if self.executor_coordinator:
                instances = self.executor_coordinator.get_all_instances()
                from .types import ExecutionInstanceType

                metrics.num_prefill_instances = sum(
                    1 for i in instances if i.instance_type == ExecutionInstanceType.PREFILLING
                )
                metrics.num_decode_instances = sum(
                    1 for i in instances if i.instance_type == ExecutionInstanceType.DECODING
                )

            logger.debug(f"Collected Prometheus metrics: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Failed to collect Prometheus metrics: {e}", exc_info=True)
            return SystemMetrics()

    async def _collect_from_instances(self) -> SystemMetrics:
        """
        Collect metrics directly from execution instances.

        Returns:
            SystemMetrics aggregated from instances
        """
        try:
            if not self.executor_coordinator:
                logger.warning("No executor coordinator available for direct collection")
                return SystemMetrics()

            instances = self.executor_coordinator.get_all_instances()
            from .types import ExecutionInstanceType

            if not instances:
                logger.debug("No instances available for metrics collection")
                return SystemMetrics()

            # Aggregate metrics from instances
            total_requests = 0
            total_ttft = 0.0
            total_itl = 0.0
            num_prefill = 0
            num_decode = 0

            for instance in instances:
                if not instance.is_available or not instance.is_healthy:
                    continue

                # Count instance types
                if instance.instance_type == ExecutionInstanceType.PREFILLING:
                    num_prefill += 1
                elif instance.instance_type == ExecutionInstanceType.DECODING:
                    num_decode += 1

                # Aggregate request counts
                total_requests += instance.active_requests

                # Aggregate latencies (weighted by request count)
                if instance.active_requests > 0:
                    total_ttft += instance.avg_latency_ms * instance.active_requests
                    total_itl += instance.avg_latency_ms * instance.active_requests

            # Compute averages
            if total_requests > 0:
                avg_ttft_ms = total_ttft / total_requests
                avg_itl_ms = total_itl / total_requests
            else:
                avg_ttft_ms = None
                avg_itl_ms = None

            # For ISL/OSL, use instance metadata if available
            # Otherwise use defaults
            avg_isl = 1024.0  # Default
            avg_osl = 256.0  # Default

            metrics = SystemMetrics(
                num_requests=float(total_requests),
                avg_isl=avg_isl,
                avg_osl=avg_osl,
                avg_ttft_ms=avg_ttft_ms,
                avg_itl_ms=avg_itl_ms,
                num_prefill_instances=num_prefill,
                num_decode_instances=num_decode,
            )

            logger.debug(f"Collected direct metrics: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Failed to collect direct metrics: {e}", exc_info=True)
            return SystemMetrics()

    def _collect_mock_metrics(self) -> SystemMetrics:
        """
        Generate mock metrics for testing.

        Returns:
            SystemMetrics with mock data
        """
        logger.debug("Using mock metrics")
        return SystemMetrics(
            num_requests=10.0,
            avg_isl=1024.0,
            avg_osl=256.0,
            avg_ttft_ms=150.0,
            avg_itl_ms=45.0,
            num_prefill_instances=2,
            num_decode_instances=4,
            request_duration_sec=5.0,
        )
