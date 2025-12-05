# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
LLM Benchmark Configuration Module
==================================

Defines configuration parameters for LLM-only scheduling policy benchmarks.

This module provides:
- LLMSLOConfig: SLO deadline settings by priority
- LLMBenchmarkConfig: LLM-specific benchmark configuration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.base_config import (
    ArrivalPattern,
    BaseBenchmarkConfig,
    BaseSLOConfig,
    SchedulingPolicy,
)


@dataclass
class LLMSLOConfig(BaseSLOConfig):
    """SLO configuration for LLM requests.

    Inherits from BaseSLOConfig with no additional fields.
    Provided for type clarity and future extensibility.
    """

    pass


@dataclass
class LLMBenchmarkConfig(BaseBenchmarkConfig):
    """LLM-specific benchmark configuration.

    Extends BaseBenchmarkConfig with LLM-specific parameters.

    Attributes:
        model_distribution: Distribution of requests across models
        prompt_len_range: Range of prompt lengths (min, max) in tokens
        output_len_range: Range of output lengths (min, max) in tokens
        dataset_path: Optional path to dataset for realistic prompts
        enable_streaming: Whether to use streaming responses
    """

    # Note: slo_config is inherited from BaseBenchmarkConfig
    # LLMSLOConfig is compatible with BaseSLOConfig

    # Model distribution: model_name -> probability
    model_distribution: dict[str, float] = field(
        default_factory=lambda: {"llama-7b": 0.5, "llama-13b": 0.3, "mistral-7b": 0.2}
    )

    # Content generation parameters
    prompt_len_range: tuple[int, int] = (50, 500)
    output_len_range: tuple[int, int] = (50, 200)

    # Data source
    dataset_path: Path | None = None

    # Streaming configuration
    enable_streaming: bool = True

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = self.validate_base()

        # Validate model distribution sums to ~1.0
        model_prob_sum = sum(self.model_distribution.values())
        if abs(model_prob_sum - 1.0) > 0.01:
            errors.append(
                f"model_distribution probabilities should sum to 1.0 (got {model_prob_sum})"
            )

        # Validate prompt length range
        if self.prompt_len_range[0] > self.prompt_len_range[1]:
            errors.append("prompt_len_range min should not exceed max")

        # Validate output length range
        if self.output_len_range[0] > self.output_len_range[1]:
            errors.append("output_len_range min should not exceed max")

        # Validate policies are LLM-compatible
        from ..common.strategy_adapter import StrategyAdapter

        llm_strategies = StrategyAdapter.list_llm_strategies()
        for policy in self.policies:
            if policy not in llm_strategies and policy != "hybrid":
                errors.append(
                    f"Policy {policy} may not support LLM requests. Recommended: {llm_strategies}"
                )

        return errors

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LLMBenchmarkConfig:
        """Create configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            LLMBenchmarkConfig instance
        """
        # Handle SLO config
        slo_data = data.get("slo_config", {})
        slo_config = LLMSLOConfig(**slo_data) if slo_data else LLMSLOConfig()

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
            control_plane_url=data.get("control_plane_url", "http://localhost:8000"),
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
            auto_visualize=data.get("auto_visualize", True),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        base_dict = self.to_base_dict()
        base_dict.update(
            {
                "model_distribution": self.model_distribution,
                "prompt_len_range": list(self.prompt_len_range),
                "output_len_range": list(self.output_len_range),
                "dataset_path": str(self.dataset_path) if self.dataset_path else None,
                "enable_streaming": self.enable_streaming,
            }
        )
        return base_dict


# Backward compatibility aliases
SLOConfig = LLMSLOConfig
BenchmarkConfig = LLMBenchmarkConfig

# Re-export from base for convenience
__all__ = [
    "LLMBenchmarkConfig",
    "LLMSLOConfig",
    "ArrivalPattern",
    "SchedulingPolicy",
    # Backward compatibility
    "SLOConfig",
    "BenchmarkConfig",
]
