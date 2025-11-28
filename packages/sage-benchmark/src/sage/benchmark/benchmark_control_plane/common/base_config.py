# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Base Configuration Module
=========================

Provides base configuration classes that can be extended for both
LLM-only and hybrid scheduling benchmarks.

This module provides:
- BaseSLOConfig: SLO deadline settings by priority
- ArrivalPattern: Request arrival pattern types
- SchedulingPolicy: Supported scheduling policies
- BaseBenchmarkConfig: Common configuration parameters
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ArrivalPattern(str, Enum):
    """Request arrival pattern types."""

    UNIFORM = "uniform"
    POISSON = "poisson"
    BURST = "burst"


class SchedulingPolicy(str, Enum):
    """Supported scheduling policies.

    These map to the strategies defined in:
    sage.common.components.sage_llm.sageLLM.control_plane.strategies
    """

    FIFO = "fifo"
    PRIORITY = "priority"
    SLO_AWARE = "slo_aware"
    COST_OPTIMIZED = "cost_optimized"
    ADAPTIVE = "adaptive"
    AEGAEON = "aegaeon"
    HYBRID = "hybrid"  # For HybridSchedulingPolicy


@dataclass
class BaseSLOConfig:
    """Base SLO configuration by priority level.

    Attributes:
        high_priority_deadline_ms: Deadline for high priority requests
        normal_priority_deadline_ms: Deadline for normal priority requests
        low_priority_deadline_ms: Deadline for low priority requests
    """

    high_priority_deadline_ms: int = 500
    normal_priority_deadline_ms: int = 1000
    low_priority_deadline_ms: int = 2000

    def get_deadline_for_priority(self, priority: str) -> int:
        """Get SLO deadline for a given priority level.

        Args:
            priority: Priority level (HIGH, NORMAL, LOW)

        Returns:
            SLO deadline in milliseconds
        """
        priority_map = {
            "HIGH": self.high_priority_deadline_ms,
            "NORMAL": self.normal_priority_deadline_ms,
            "LOW": self.low_priority_deadline_ms,
        }
        return priority_map.get(priority.upper(), self.normal_priority_deadline_ms)

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary."""
        return {
            "high_priority_deadline_ms": self.high_priority_deadline_ms,
            "normal_priority_deadline_ms": self.normal_priority_deadline_ms,
            "low_priority_deadline_ms": self.low_priority_deadline_ms,
        }


@dataclass
class BaseBenchmarkConfig(ABC):
    """Base benchmark configuration.

    Provides common configuration parameters for all benchmark types.
    Subclasses should add type-specific parameters.

    Attributes:
        control_plane_url: HTTP URL of the Control Plane service
        policies: List of scheduling policies to benchmark
        num_requests: Total number of requests to send per benchmark run
        request_rate: Target request rate in requests per second
        arrival_pattern: Request arrival pattern (uniform, poisson, burst)
        priority_distribution: Distribution of request priorities
        slo_config: SLO deadline configuration
        timeout_seconds: Request timeout in seconds
        warmup_requests: Number of warmup requests before measurement
        output_dir: Directory for benchmark results
        concurrent_requests: Maximum concurrent requests
    """

    # Control Plane connection
    control_plane_url: str = "http://localhost:8080"

    # Policies to benchmark
    policies: list[str] = field(default_factory=lambda: ["fifo", "priority", "slo_aware"])

    # Request configuration
    num_requests: int = 100
    request_rate: float = 10.0  # requests per second
    arrival_pattern: ArrivalPattern = ArrivalPattern.POISSON

    # Priority distribution: priority -> probability
    priority_distribution: dict[str, float] = field(
        default_factory=lambda: {"HIGH": 0.2, "NORMAL": 0.6, "LOW": 0.2}
    )

    # SLO configuration
    slo_config: BaseSLOConfig = field(default_factory=BaseSLOConfig)

    # Execution parameters
    timeout_seconds: float = 60.0
    warmup_requests: int = 10
    concurrent_requests: int = 50

    # Output configuration
    output_dir: Path = field(default_factory=lambda: Path("./benchmark_results"))

    # Auto visualization after benchmark
    auto_visualize: bool = True

    def validate_base(self) -> list[str]:
        """Validate base configuration and return list of errors.

        Returns:
            List of validation error messages
        """
        errors = []

        if self.num_requests <= 0:
            errors.append("num_requests must be positive")

        if self.request_rate <= 0:
            errors.append("request_rate must be positive")

        if self.warmup_requests < 0:
            errors.append("warmup_requests cannot be negative")

        if self.warmup_requests >= self.num_requests:
            errors.append("warmup_requests should be less than num_requests")

        if self.timeout_seconds <= 0:
            errors.append("timeout_seconds must be positive")

        if self.concurrent_requests <= 0:
            errors.append("concurrent_requests must be positive")

        # Validate priority distribution sums to ~1.0
        priority_prob_sum = sum(self.priority_distribution.values())
        if abs(priority_prob_sum - 1.0) > 0.01:
            errors.append(
                f"priority_distribution probabilities should sum to 1.0 (got {priority_prob_sum})"
            )

        # Validate policies
        valid_policies = {p.value for p in SchedulingPolicy}
        for policy in self.policies:
            if policy not in valid_policies:
                errors.append(f"Unknown policy: {policy}. Valid: {valid_policies}")

        return errors

    @abstractmethod
    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Subclasses should call validate_base() and add type-specific validation.

        Returns:
            List of validation error messages
        """
        pass

    def to_base_dict(self) -> dict[str, Any]:
        """Convert base configuration to dictionary.

        Returns:
            Dictionary representation of base config
        """
        return {
            "control_plane_url": self.control_plane_url,
            "policies": self.policies,
            "num_requests": self.num_requests,
            "request_rate": self.request_rate,
            "arrival_pattern": self.arrival_pattern.value,
            "priority_distribution": self.priority_distribution,
            "slo_config": self.slo_config.to_dict(),
            "timeout_seconds": self.timeout_seconds,
            "warmup_requests": self.warmup_requests,
            "concurrent_requests": self.concurrent_requests,
            "output_dir": str(self.output_dir),
            "auto_visualize": self.auto_visualize,
        }

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert full configuration to dictionary.

        Returns:
            Dictionary representation of full config
        """
        pass
