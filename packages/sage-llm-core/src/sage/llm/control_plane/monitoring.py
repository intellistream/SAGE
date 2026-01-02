# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Performance monitoring and metrics collection."""

import logging
from collections import deque
from datetime import datetime

from .types import (
    ExecutionInstance,
    InstanceMetrics,
    PerformanceMetrics,
    RequestMetadata,
    SchedulingDecision,
    SchedulingMetrics,
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and aggregate performance metrics for Control Plane."""

    def __init__(self, window_size: int = 1000):
        """
        Initialize metrics collector.

        Args:
            window_size: Size of sliding window for metric calculation
        """
        self.window_size = window_size

        # Historical data windows (in-memory only)
        self.latency_history: deque[float] = deque(maxlen=window_size)
        self.prediction_errors: deque[float] = deque(maxlen=window_size)
        self.queue_wait_times: deque[float] = deque(maxlen=window_size)
        self.scheduling_times: deque[float] = deque(maxlen=window_size)
        self.queue_lengths: deque[int] = deque(maxlen=window_size)

        # Instance-level metrics
        self.instance_metrics: dict[str, InstanceMetrics] = {}

        # SLO tracking by priority
        self.slo_compliance_by_priority: dict[str, deque[bool]] = {
            "CRITICAL": deque(maxlen=window_size),
            "HIGH": deque(maxlen=window_size),
            "NORMAL": deque(maxlen=window_size),
            "LOW": deque(maxlen=window_size),
            "BACKGROUND": deque(maxlen=window_size),
        }

        # Counters
        self.total_requests = 0
        self.completed_requests = 0
        self.failed_requests = 0

        logger.info("MetricsCollector initialized with window_size=%d", window_size)

    def record_request_completion(
        self,
        request: RequestMetadata,
        decision: SchedulingDecision,
        actual_latency_ms: float,
        success: bool = True,
    ):
        """
        Record request completion.

        Args:
            request: Completed request
            decision: Scheduling decision
            actual_latency_ms: Actual latency in milliseconds
            success: Whether request succeeded
        """
        self.total_requests += 1

        if success:
            self.completed_requests += 1

            # Record latency
            self.latency_history.append(actual_latency_ms)

            # Record prediction error
            prediction_error = abs(actual_latency_ms - decision.estimated_latency_ms)
            self.prediction_errors.append(prediction_error)

            # Record queue wait time
            if request.queue_wait_ms:
                self.queue_wait_times.append(request.queue_wait_ms)

            # Record SLO compliance
            priority_name = request.priority.name
            if request.slo_deadline_ms:
                met_slo = actual_latency_ms <= request.slo_deadline_ms
                if priority_name in self.slo_compliance_by_priority:
                    self.slo_compliance_by_priority[priority_name].append(met_slo)
        else:
            self.failed_requests += 1

    def record_scheduling_decision(self, decision_time_us: float):
        """
        Record scheduling decision latency.

        Args:
            decision_time_us: Time taken for scheduling decision in microseconds
        """
        self.scheduling_times.append(decision_time_us)

    def record_queue_length(self, length: int):
        """
        Record current queue length.

        Args:
            length: Current queue length
        """
        self.queue_lengths.append(length)

    def update_instance_metrics(
        self,
        instance: ExecutionInstance,
        latencies: list[float] | None = None,
    ):
        """
        Update metrics for a specific instance.

        Args:
            instance: Execution instance
            latencies: Recent latencies for this instance (optional)
        """
        # Get or create instance metrics
        if instance.instance_id not in self.instance_metrics:
            self.instance_metrics[instance.instance_id] = InstanceMetrics(
                instance_id=instance.instance_id
            )

        metrics = self.instance_metrics[instance.instance_id]

        # Update from instance state
        metrics.active_requests = instance.active_requests
        metrics.gpu_utilization = instance.gpu_utilization
        metrics.gpu_memory_used_gb = instance.gpu_memory_gb
        metrics.current_load = instance.current_load
        metrics.is_healthy = instance.is_healthy
        metrics.last_health_check = datetime.now()
        metrics.consecutive_failures = instance.metadata.get("consecutive_failures", 0)

        # Update latency statistics if provided
        if latencies and len(latencies) > 0:
            metrics.avg_latency_ms = sum(latencies) / len(latencies)
            sorted_latencies = sorted(latencies)
            metrics.p50_latency_ms = self._percentile_from_list(sorted_latencies, 50)
            metrics.p95_latency_ms = self._percentile_from_list(sorted_latencies, 95)
            metrics.p99_latency_ms = self._percentile_from_list(sorted_latencies, 99)

        metrics.timestamp = datetime.now()

    def record_instance_failure(self, instance_id: str):
        """
        Record instance failure event.

        Args:
            instance_id: Failed instance ID
        """
        if instance_id in self.instance_metrics:
            self.instance_metrics[instance_id].consecutive_failures += 1
            self.instance_metrics[instance_id].is_healthy = False

        logger.warning("Recorded failure for instance %s", instance_id)

    def get_scheduling_metrics(self, policy_name: str) -> SchedulingMetrics:
        """
        Get current scheduling metrics.

        Args:
            policy_name: Name of the scheduling policy

        Returns:
            SchedulingMetrics object
        """
        # Calculate load balance variance
        load_variance = self._calculate_load_variance()

        # Calculate SLO compliance by priority
        slo_by_priority = {}
        for priority, compliance_list in self.slo_compliance_by_priority.items():
            if len(compliance_list) > 0:
                slo_by_priority[priority] = sum(compliance_list) / len(compliance_list)
            else:
                slo_by_priority[priority] = 1.0

        # Calculate prediction accuracy
        accurate_predictions = sum(
            1
            for err in self.prediction_errors
            if err < 10.0  # < 10ms error
        )
        accuracy_rate = (
            accurate_predictions / len(self.prediction_errors) if self.prediction_errors else 1.0
        )

        return SchedulingMetrics(
            policy_name=policy_name,
            scheduling_latency_us=self._percentile(self.scheduling_times, 50),
            scheduling_throughput=self._calculate_throughput(self.scheduling_times),
            latency_prediction_error_avg=self._mean(self.prediction_errors),
            latency_prediction_error_p95=self._percentile(self.prediction_errors, 95),
            prediction_accuracy_rate=accuracy_rate,
            load_balance_variance=load_variance,
            load_balance_coefficient=self._calculate_load_balance_coefficient(load_variance),
            slo_compliance_by_priority=slo_by_priority,
            queue_wait_time_p50=self._percentile(self.queue_wait_times, 50),
            queue_wait_time_p95=self._percentile(self.queue_wait_times, 95),
            queue_wait_time_p99=self._percentile(self.queue_wait_times, 99),
            queue_length_avg=self._mean(self.queue_lengths),
            queue_length_max=max(self.queue_lengths) if self.queue_lengths else 0,
        )

    def get_instance_metrics(self, instance_id: str) -> InstanceMetrics | None:
        """
        Get metrics for a specific instance.

        Args:
            instance_id: Instance identifier

        Returns:
            InstanceMetrics or None if not found
        """
        return self.instance_metrics.get(instance_id)

    def get_all_instance_metrics(self) -> dict[str, InstanceMetrics]:
        """Get metrics for all instances."""
        return self.instance_metrics.copy()

    def get_global_metrics(self) -> PerformanceMetrics:
        """
        Get global performance metrics.

        Returns:
            PerformanceMetrics object
        """
        return PerformanceMetrics(
            total_requests=self.total_requests,
            completed_requests=self.completed_requests,
            failed_requests=self.failed_requests,
            avg_latency_ms=self._mean(self.latency_history),
            p50_latency_ms=self._percentile(self.latency_history, 50),
            p95_latency_ms=self._percentile(self.latency_history, 95),
            p99_latency_ms=self._percentile(self.latency_history, 99),
        )

    def _calculate_load_variance(self) -> float:
        """Calculate load variance across instances."""
        if not self.instance_metrics:
            return 0.0

        loads = [m.current_load for m in self.instance_metrics.values()]
        if not loads:
            return 0.0

        mean_load = sum(loads) / len(loads)
        variance = sum((load - mean_load) ** 2 for load in loads) / len(loads)
        return variance

    def _calculate_load_balance_coefficient(self, variance: float) -> float:
        """
        Calculate load balance coefficient (1.0 = perfect balance).

        Args:
            variance: Load variance

        Returns:
            Coefficient between 0.0 and 1.0
        """
        # Simple heuristic: coefficient = 1 / (1 + variance)
        return 1.0 / (1.0 + variance) if variance >= 0 else 1.0

    def _calculate_throughput(self, times: deque) -> float:
        """
        Calculate throughput based on timing data.

        Args:
            times: Deque of timing values

        Returns:
            Throughput (items/second)
        """
        if not times or len(times) < 2:
            return 0.0

        # Estimate throughput based on average time
        avg_time_us = self._mean(times)
        if avg_time_us > 0:
            return 1_000_000 / avg_time_us  # Convert μs to items/second
        return 0.0

    @staticmethod
    def _mean(values: deque | list) -> float:
        """Calculate mean of values."""
        return float(sum(values) / len(values)) if values else 0.0

    @staticmethod
    def _percentile(values: deque | list, p: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p / 100)
        return float(sorted_values[min(index, len(sorted_values) - 1)])

    @staticmethod
    def _percentile_from_list(sorted_values: list[float], p: int) -> float:
        """Calculate percentile from already sorted list."""
        if not sorted_values:
            return 0.0
        index = int(len(sorted_values) * p / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def reset(self):
        """Reset all metrics (for testing)."""
        self.latency_history.clear()
        self.prediction_errors.clear()
        self.queue_wait_times.clear()
        self.scheduling_times.clear()
        self.queue_lengths.clear()
        self.instance_metrics.clear()

        for priority in self.slo_compliance_by_priority:
            self.slo_compliance_by_priority[priority].clear()

        self.total_requests = 0
        self.completed_requests = 0
        self.failed_requests = 0

        logger.info("MetricsCollector reset")
