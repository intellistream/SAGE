"""
Benchmark Configuration Module
==============================

Defines configuration parameters for Control Plane scheduling policy benchmarks.

This module provides:
- BenchmarkConfig: Main configuration dataclass
- SLOConfig: SLO deadline settings by priority
- ArrivalPattern: Request arrival pattern types
- SchedulingPolicy: Supported scheduling policies
"""

from __future__ import annotations

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
    """Supported scheduling policies."""

    FIFO = "fifo"
    PRIORITY = "priority"
    SLO_AWARE = "slo_aware"
    COST_OPTIMIZED = "cost_optimized"
    ADAPTIVE = "adaptive"
    AEGAEON = "aegaeon"


@dataclass
class SLOConfig:
    """SLO configuration by priority level.

    Attributes:
        high_priority_deadline_ms: Deadline for high priority requests
        normal_priority_deadline_ms: Deadline for normal priority requests
        low_priority_deadline_ms: Deadline for low priority requests
    """

    high_priority_deadline_ms: int = 500
    normal_priority_deadline_ms: int = 1000
    low_priority_deadline_ms: int = 2000

    def get_deadline_for_priority(self, priority: str) -> int:
        """Get SLO deadline for a given priority level."""
        priority_map = {
            "HIGH": self.high_priority_deadline_ms,
            "NORMAL": self.normal_priority_deadline_ms,
            "LOW": self.low_priority_deadline_ms,
        }
        return priority_map.get(priority.upper(), self.normal_priority_deadline_ms)


@dataclass
class BenchmarkConfig:
    """Main benchmark configuration.

    Attributes:
        control_plane_url: HTTP URL of the Control Plane service
        policies: List of scheduling policies to benchmark
        num_requests: Total number of requests to send per benchmark run
        request_rate: Target request rate in requests per second
        arrival_pattern: Request arrival pattern (uniform, poisson, burst)
        model_distribution: Distribution of requests across models
        priority_distribution: Distribution of request priorities
        prompt_len_range: Range of prompt lengths (min, max) in tokens
        output_len_range: Range of output lengths (min, max) in tokens
        slo_config: SLO deadline configuration
        timeout_seconds: Request timeout in seconds
        warmup_requests: Number of warmup requests before measurement
        dataset_path: Optional path to dataset for realistic prompts
        output_dir: Directory for benchmark results
        enable_streaming: Whether to use streaming responses
        concurrent_requests: Maximum concurrent requests
    """

    # Control Plane connection
    control_plane_url: str = "http://localhost:8888"

    # Policies to benchmark
    policies: list[str] = field(default_factory=lambda: ["fifo", "priority", "slo_aware"])

    # Request configuration
    num_requests: int = 100
    request_rate: float = 10.0  # requests per second
    arrival_pattern: ArrivalPattern = ArrivalPattern.POISSON

    # Model distribution: model_name -> probability
    model_distribution: dict[str, float] = field(
        default_factory=lambda: {"llama-7b": 0.5, "llama-13b": 0.3, "mistral-7b": 0.2}
    )

    # Priority distribution: priority -> probability
    priority_distribution: dict[str, float] = field(
        default_factory=lambda: {"HIGH": 0.2, "NORMAL": 0.6, "LOW": 0.2}
    )

    # Content generation parameters
    prompt_len_range: tuple[int, int] = (50, 500)
    output_len_range: tuple[int, int] = (50, 200)

    # SLO configuration
    slo_config: SLOConfig = field(default_factory=SLOConfig)

    # Execution parameters
    timeout_seconds: float = 60.0
    warmup_requests: int = 10
    concurrent_requests: int = 50

    # Data source
    dataset_path: Path | None = None

    # Output configuration
    output_dir: Path = field(default_factory=lambda: Path("./.benchmarks"))
    enable_streaming: bool = True

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
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

        # Validate model distribution sums to ~1.0
        model_prob_sum = sum(self.model_distribution.values())
        if abs(model_prob_sum - 1.0) > 0.01:
            errors.append(
                f"model_distribution probabilities should sum to 1.0 (got {model_prob_sum})"
            )

        # Validate priority distribution sums to ~1.0
        priority_prob_sum = sum(self.priority_distribution.values())
        if abs(priority_prob_sum - 1.0) > 0.01:
            errors.append(
                f"priority_distribution probabilities should sum to 1.0 (got {priority_prob_sum})"
            )

        # Validate prompt length range
        if self.prompt_len_range[0] > self.prompt_len_range[1]:
            errors.append("prompt_len_range min should not exceed max")

        # Validate output length range
        if self.output_len_range[0] > self.output_len_range[1]:
            errors.append("output_len_range min should not exceed max")

        # Validate policies
        valid_policies = {p.value for p in SchedulingPolicy}
        for policy in self.policies:
            if policy not in valid_policies:
                errors.append(f"Unknown policy: {policy}. Valid: {valid_policies}")

        return errors

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkConfig:
        """Create configuration from dictionary."""
        # Handle SLO config
        slo_data = data.get("slo_config", {})
        slo_config = SLOConfig(**slo_data) if slo_data else SLOConfig()

        # Handle arrival pattern
        arrival_pattern = data.get("arrival_pattern", "poisson")
        if isinstance(arrival_pattern, str):
            arrival_pattern = ArrivalPattern(arrival_pattern)

        # Handle paths
        dataset_path = data.get("dataset_path")
        if dataset_path:
            dataset_path = Path(dataset_path)

        output_dir = data.get("output_dir", "./.benchmarks")
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        return cls(
            control_plane_url=data.get("control_plane_url", "http://localhost:8888"),
            policies=data.get("policies", ["fifo", "priority", "slo_aware"]),
            num_requests=data.get("num_requests", 100),
            request_rate=data.get("request_rate", 10.0),
            arrival_pattern=arrival_pattern,
            model_distribution=data.get(
                "model_distribution",
                {"llama-7b": 0.5, "llama-13b": 0.3, "mistral-7b": 0.2},
            ),
            priority_distribution=data.get(
                "priority_distribution",
                {"HIGH": 0.2, "NORMAL": 0.6, "LOW": 0.2},
            ),
            prompt_len_range=tuple(data.get("prompt_len_range", [50, 500])),
            output_len_range=tuple(data.get("output_len_range", [50, 200])),
            slo_config=slo_config,
            timeout_seconds=data.get("timeout_seconds", 60.0),
            warmup_requests=data.get("warmup_requests", 10),
            concurrent_requests=data.get("concurrent_requests", 50),
            dataset_path=dataset_path,
            output_dir=output_dir,
            enable_streaming=data.get("enable_streaming", True),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "control_plane_url": self.control_plane_url,
            "policies": self.policies,
            "num_requests": self.num_requests,
            "request_rate": self.request_rate,
            "arrival_pattern": self.arrival_pattern.value,
            "model_distribution": self.model_distribution,
            "priority_distribution": self.priority_distribution,
            "prompt_len_range": list(self.prompt_len_range),
            "output_len_range": list(self.output_len_range),
            "slo_config": {
                "high_priority_deadline_ms": self.slo_config.high_priority_deadline_ms,
                "normal_priority_deadline_ms": self.slo_config.normal_priority_deadline_ms,
                "low_priority_deadline_ms": self.slo_config.low_priority_deadline_ms,
            },
            "timeout_seconds": self.timeout_seconds,
            "warmup_requests": self.warmup_requests,
            "concurrent_requests": self.concurrent_requests,
            "dataset_path": str(self.dataset_path) if self.dataset_path else None,
            "output_dir": str(self.output_dir),
            "enable_streaming": self.enable_streaming,
        }
