"""
Telemetry Module

Provides performance monitoring and metrics collection for agent runtime.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from sage.libs.agentic.agents.runtime.config import TelemetryConfig


@dataclass
class Telemetry:
    """Single telemetry record."""

    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    def finish(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark operation as finished."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "metadata": self.metadata,
            "success": self.success,
            "error": self.error,
        }


class TelemetryCollector:
    """Collects and manages telemetry data."""

    def __init__(self, config: TelemetryConfig):
        """Initialize telemetry collector.

        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.records: list[Telemetry] = []
        self._enabled = config.enabled

    def start(self, operation: str, metadata: Optional[dict[str, Any]] = None) -> Telemetry:
        """Start tracking an operation.

        Args:
            operation: Operation name
            metadata: Additional metadata

        Returns:
            Telemetry record
        """
        if not self._enabled:
            return Telemetry(operation=operation, start_time=time.time(), metadata=metadata or {})

        record = Telemetry(operation=operation, start_time=time.time(), metadata=metadata or {})
        self.records.append(record)
        return record

    def finish(self, record: Telemetry, success: bool = True, error: Optional[str] = None) -> None:
        """Finish tracking an operation.

        Args:
            record: Telemetry record to finish
            success: Whether operation succeeded
            error: Error message if any
        """
        if self._enabled:
            record.finish(success=success, error=error)

    def get_metrics(self) -> dict[str, Any]:
        """Get aggregated metrics.

        Returns:
            Dictionary of metrics
        """
        if not self.records:
            return {}

        successful = [r for r in self.records if r.success]
        failed = [r for r in self.records if not r.success]

        durations = [r.duration for r in successful if r.duration is not None]

        metrics = {
            "total_operations": len(self.records),
            "successful_operations": len(successful),
            "failed_operations": len(failed),
            "success_rate": len(successful) / len(self.records) if self.records else 0.0,
        }

        if durations:
            metrics.update(
                {
                    "avg_latency": sum(durations) / len(durations),
                    "min_latency": min(durations),
                    "max_latency": max(durations),
                    "total_time": sum(durations),
                }
            )

        # Group by operation type
        by_operation: dict[str, list[Telemetry]] = {}
        for record in self.records:
            by_operation.setdefault(record.operation, []).append(record)

        operation_metrics = {}
        for op_name, op_records in by_operation.items():
            op_durations = [r.duration for r in op_records if r.duration is not None and r.success]
            if op_durations:
                operation_metrics[op_name] = {
                    "count": len(op_records),
                    "success_count": len([r for r in op_records if r.success]),
                    "avg_latency": sum(op_durations) / len(op_durations),
                }

        metrics["by_operation"] = operation_metrics

        return metrics

    def clear(self) -> None:
        """Clear all records."""
        self.records.clear()

    def to_dict(self) -> dict[str, Any]:
        """Export all records.

        Returns:
            Dictionary with all records
        """
        return {
            "records": [r.to_dict() for r in self.records],
            "metrics": self.get_metrics(),
        }
