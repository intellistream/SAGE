# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
GPU Monitor Module
==================

Provides GPU resource monitoring for benchmarks.

This module supports:
- pynvml for NVIDIA GPU monitoring
- Fallback to nvidia-smi command
- Mock mode when no GPU is available
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# Try to import pynvml
PYNVML_AVAILABLE = False
try:
    import pynvml  # type: ignore[import-not-found]

    PYNVML_AVAILABLE = True
except ImportError:
    pynvml = None  # type: ignore[assignment]


class GPUMonitorBackend(str, Enum):
    """GPU monitoring backend type."""

    PYNVML = "pynvml"
    NVIDIA_SMI = "nvidia-smi"
    MOCK = "mock"


@dataclass
class GPUMetrics:
    """GPU metrics snapshot.

    Attributes:
        timestamp: Time when metrics were collected (epoch seconds)
        device_count: Number of GPU devices
        utilization_percent: GPU utilization percentage per device
        memory_used_mb: Memory used in MB per device
        memory_total_mb: Total memory in MB per device
        memory_percent: Memory utilization percentage per device
        temperature_celsius: Temperature in Celsius per device
        power_watts: Power consumption in Watts per device
    """

    timestamp: float = 0.0
    device_count: int = 0
    utilization_percent: list[float] = field(default_factory=list)
    memory_used_mb: list[float] = field(default_factory=list)
    memory_total_mb: list[float] = field(default_factory=list)
    memory_percent: list[float] = field(default_factory=list)
    temperature_celsius: list[float] = field(default_factory=list)
    power_watts: list[float] = field(default_factory=list)

    @property
    def avg_utilization(self) -> float:
        """Average GPU utilization across all devices."""
        if not self.utilization_percent:
            return 0.0
        return sum(self.utilization_percent) / len(self.utilization_percent)

    @property
    def avg_memory_percent(self) -> float:
        """Average memory utilization across all devices."""
        if not self.memory_percent:
            return 0.0
        return sum(self.memory_percent) / len(self.memory_percent)

    @property
    def total_memory_used_mb(self) -> float:
        """Total memory used across all devices."""
        return sum(self.memory_used_mb)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "device_count": self.device_count,
            "utilization_percent": self.utilization_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_total_mb": self.memory_total_mb,
            "memory_percent": self.memory_percent,
            "temperature_celsius": self.temperature_celsius,
            "power_watts": self.power_watts,
            "avg_utilization": self.avg_utilization,
            "avg_memory_percent": self.avg_memory_percent,
            "total_memory_used_mb": self.total_memory_used_mb,
        }


@dataclass
class GPUMetricsSummary:
    """Summary of GPU metrics over a time period.

    Attributes:
        samples: Number of samples collected
        duration_seconds: Duration of monitoring
        utilization_avg: Average GPU utilization
        utilization_max: Maximum GPU utilization
        utilization_min: Minimum GPU utilization
        memory_used_avg_mb: Average memory used
        memory_used_max_mb: Maximum memory used
        memory_percent_avg: Average memory percentage
        temperature_avg_celsius: Average temperature
        temperature_max_celsius: Maximum temperature
        power_avg_watts: Average power consumption
        power_max_watts: Maximum power consumption
    """

    samples: int = 0
    duration_seconds: float = 0.0
    utilization_avg: float = 0.0
    utilization_max: float = 0.0
    utilization_min: float = 100.0
    memory_used_avg_mb: float = 0.0
    memory_used_max_mb: float = 0.0
    memory_percent_avg: float = 0.0
    temperature_avg_celsius: float = 0.0
    temperature_max_celsius: float = 0.0
    power_avg_watts: float = 0.0
    power_max_watts: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "samples": self.samples,
            "duration_seconds": self.duration_seconds,
            "utilization": {
                "avg": self.utilization_avg,
                "max": self.utilization_max,
                "min": self.utilization_min,
            },
            "memory": {
                "used_avg_mb": self.memory_used_avg_mb,
                "used_max_mb": self.memory_used_max_mb,
                "percent_avg": self.memory_percent_avg,
            },
            "temperature": {
                "avg_celsius": self.temperature_avg_celsius,
                "max_celsius": self.temperature_max_celsius,
            },
            "power": {
                "avg_watts": self.power_avg_watts,
                "max_watts": self.power_max_watts,
            },
        }


class GPUMonitor:
    """GPU resource monitor with background sampling.

    Supports multiple backends:
    - pynvml: Most efficient, requires pynvml package
    - nvidia-smi: Fallback using nvidia-smi command
    - mock: Returns dummy data when no GPU available

    Example:
        monitor = GPUMonitor()
        monitor.start_monitoring(interval_seconds=0.5)
        # ... run benchmark ...
        monitor.stop_monitoring()
        summary = monitor.get_summary()
    """

    def __init__(
        self,
        backend: GPUMonitorBackend | str | None = None,
        mock_device_count: int = 1,
    ):
        """Initialize GPU monitor.

        Args:
            backend: Monitoring backend to use. If None, auto-detect.
            mock_device_count: Number of mock devices in mock mode
        """
        self._backend = self._select_backend(backend)
        self._mock_device_count = mock_device_count
        self._samples: list[GPUMetrics] = []
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._pynvml_initialized = False

        logger.info(f"GPU Monitor initialized with backend: {self._backend.value}")

    def _select_backend(self, backend: GPUMonitorBackend | str | None) -> GPUMonitorBackend:
        """Select appropriate backend.

        Args:
            backend: Requested backend or None for auto-detect

        Returns:
            Selected backend
        """
        if backend is not None:
            if isinstance(backend, str):
                return GPUMonitorBackend(backend)
            return backend

        # Auto-detect
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()  # type: ignore[union-attr]
                device_count = pynvml.nvmlDeviceGetCount()  # type: ignore[union-attr]
                pynvml.nvmlShutdown()  # type: ignore[union-attr]
                if device_count > 0:
                    return GPUMonitorBackend.PYNVML
            except Exception:
                pass

        # Try nvidia-smi
        if self._check_nvidia_smi():
            return GPUMonitorBackend.NVIDIA_SMI

        # Fall back to mock
        logger.warning("No GPU detected, using mock backend")
        return GPUMonitorBackend.MOCK

    def _check_nvidia_smi(self) -> bool:
        """Check if nvidia-smi is available."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=count", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    @property
    def backend(self) -> GPUMonitorBackend:
        """Get current backend."""
        return self._backend

    @property
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring

    def start_monitoring(self, interval_seconds: float = 0.5) -> None:
        """Start background GPU monitoring.

        Args:
            interval_seconds: Sampling interval in seconds
        """
        if self._monitoring:
            logger.warning("Monitoring already active")
            return

        self._samples = []
        self._stop_event.clear()
        self._monitoring = True

        if self._backend == GPUMonitorBackend.PYNVML:
            self._init_pynvml()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            daemon=True,
        )
        self._monitor_thread.start()
        logger.debug(f"Started GPU monitoring with interval {interval_seconds}s")

    def stop_monitoring(self) -> None:
        """Stop background GPU monitoring."""
        if not self._monitoring:
            return

        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)

        self._monitoring = False

        if self._backend == GPUMonitorBackend.PYNVML and self._pynvml_initialized:
            try:
                pynvml.nvmlShutdown()  # type: ignore[union-attr]
            except Exception:
                pass
            self._pynvml_initialized = False

        logger.debug(f"Stopped GPU monitoring, collected {len(self._samples)} samples")

    def _init_pynvml(self) -> None:
        """Initialize pynvml."""
        if self._pynvml_initialized:
            return
        try:
            pynvml.nvmlInit()  # type: ignore[union-attr]
            self._pynvml_initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize pynvml: {e}")
            self._backend = GPUMonitorBackend.MOCK

    def _monitor_loop(self, interval_seconds: float) -> None:
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            try:
                metrics = self.get_metrics()
                with self._lock:
                    self._samples.append(metrics)
            except Exception as e:
                logger.error(f"Error collecting GPU metrics: {e}")

            self._stop_event.wait(interval_seconds)

    def get_metrics(self) -> GPUMetrics:
        """Get current GPU metrics.

        Returns:
            Current GPU metrics snapshot
        """
        if self._backend == GPUMonitorBackend.PYNVML:
            return self._get_metrics_pynvml()
        elif self._backend == GPUMonitorBackend.NVIDIA_SMI:
            return self._get_metrics_nvidia_smi()
        else:
            return self._get_metrics_mock()

    def _get_metrics_pynvml(self) -> GPUMetrics:
        """Get metrics using pynvml."""
        metrics = GPUMetrics(timestamp=time.time())

        if not self._pynvml_initialized:
            self._init_pynvml()

        try:
            device_count = pynvml.nvmlDeviceGetCount()  # type: ignore[union-attr]
            metrics.device_count = device_count

            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)  # type: ignore[union-attr]

                # Utilization
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)  # type: ignore[union-attr]
                    metrics.utilization_percent.append(float(util.gpu))
                except Exception:
                    metrics.utilization_percent.append(0.0)

                # Memory
                try:
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)  # type: ignore[union-attr]
                    used_mb = mem.used / (1024 * 1024)
                    total_mb = mem.total / (1024 * 1024)
                    metrics.memory_used_mb.append(used_mb)
                    metrics.memory_total_mb.append(total_mb)
                    metrics.memory_percent.append(100.0 * mem.used / mem.total if mem.total else 0.0)
                except Exception:
                    metrics.memory_used_mb.append(0.0)
                    metrics.memory_total_mb.append(0.0)
                    metrics.memory_percent.append(0.0)

                # Temperature
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(  # type: ignore[union-attr]
                        handle, pynvml.NVML_TEMPERATURE_GPU  # type: ignore[union-attr]
                    )
                    metrics.temperature_celsius.append(float(temp))
                except Exception:
                    metrics.temperature_celsius.append(0.0)

                # Power
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # type: ignore[union-attr]  # mW to W
                    metrics.power_watts.append(power)
                except Exception:
                    metrics.power_watts.append(0.0)

        except Exception as e:
            logger.error(f"Error getting pynvml metrics: {e}")

        return metrics

    def _get_metrics_nvidia_smi(self) -> GPUMetrics:
        """Get metrics using nvidia-smi command."""
        metrics = GPUMetrics(timestamp=time.time())

        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                metrics.device_count = len(lines)

                for line in lines:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 5:
                        metrics.utilization_percent.append(float(parts[0]))
                        metrics.memory_used_mb.append(float(parts[1]))
                        total_mb = float(parts[2])
                        metrics.memory_total_mb.append(total_mb)
                        used_mb = float(parts[1])
                        metrics.memory_percent.append(100.0 * used_mb / total_mb if total_mb else 0.0)
                        metrics.temperature_celsius.append(float(parts[3]))
                        # Power might be "[N/A]" for some GPUs
                        try:
                            metrics.power_watts.append(float(parts[4]))
                        except ValueError:
                            metrics.power_watts.append(0.0)

        except Exception as e:
            logger.error(f"Error getting nvidia-smi metrics: {e}")

        return metrics

    def _get_metrics_mock(self) -> GPUMetrics:
        """Get mock metrics for testing without GPU."""
        import random

        metrics = GPUMetrics(timestamp=time.time())
        metrics.device_count = self._mock_device_count

        for _ in range(self._mock_device_count):
            metrics.utilization_percent.append(random.uniform(50.0, 90.0))
            metrics.memory_used_mb.append(random.uniform(4000.0, 12000.0))
            metrics.memory_total_mb.append(16384.0)
            metrics.memory_percent.append(
                100.0 * metrics.memory_used_mb[-1] / metrics.memory_total_mb[-1]
            )
            metrics.temperature_celsius.append(random.uniform(40.0, 70.0))
            metrics.power_watts.append(random.uniform(100.0, 250.0))

        return metrics

    def get_samples(self) -> list[GPUMetrics]:
        """Get all collected samples.

        Returns:
            List of GPU metrics samples
        """
        with self._lock:
            return self._samples.copy()

    def get_summary(self) -> GPUMetricsSummary:
        """Compute summary statistics from collected samples.

        Returns:
            Summary of GPU metrics over monitoring period
        """
        with self._lock:
            samples = self._samples.copy()

        summary = GPUMetricsSummary()

        if not samples:
            return summary

        summary.samples = len(samples)

        if len(samples) >= 2:
            summary.duration_seconds = samples[-1].timestamp - samples[0].timestamp

        # Aggregate across samples
        all_util = []
        all_mem_used = []
        all_mem_pct = []
        all_temp = []
        all_power = []

        for s in samples:
            all_util.extend(s.utilization_percent)
            all_mem_used.extend(s.memory_used_mb)
            all_mem_pct.extend(s.memory_percent)
            all_temp.extend(s.temperature_celsius)
            all_power.extend(s.power_watts)

        if all_util:
            summary.utilization_avg = sum(all_util) / len(all_util)
            summary.utilization_max = max(all_util)
            summary.utilization_min = min(all_util)

        if all_mem_used:
            summary.memory_used_avg_mb = sum(all_mem_used) / len(all_mem_used)
            summary.memory_used_max_mb = max(all_mem_used)

        if all_mem_pct:
            summary.memory_percent_avg = sum(all_mem_pct) / len(all_mem_pct)

        if all_temp:
            summary.temperature_avg_celsius = sum(all_temp) / len(all_temp)
            summary.temperature_max_celsius = max(all_temp)

        if all_power:
            summary.power_avg_watts = sum(all_power) / len(all_power)
            summary.power_max_watts = max(all_power)

        return summary

    def __enter__(self) -> GPUMonitor:
        """Context manager entry."""
        self.start_monitoring()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop_monitoring()
