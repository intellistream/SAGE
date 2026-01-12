# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Hybrid Benchmark Configuration Module
=====================================

Defines configuration parameters for hybrid (LLM + Embedding) scheduling
policy benchmarks.

This module provides:
- HybridSLOConfig: SLO deadline settings for both LLM and Embedding requests
- HybridBenchmarkConfig: Hybrid-specific benchmark configuration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from ..common.base_config import (
    ArrivalPattern,
    BaseBenchmarkConfig,
    BaseSLOConfig,
    SchedulingPolicy,
)


class RequestType(str, Enum):
    """Types of requests in hybrid workloads."""

    LLM_CHAT = "llm_chat"
    LLM_GENERATE = "llm_generate"
    EMBEDDING = "embedding"


@dataclass
class HybridSLOConfig(BaseSLOConfig):
    """SLO configuration for hybrid (LLM + Embedding) requests.

    Extends BaseSLOConfig with embedding-specific SLO deadlines.

    Attributes:
        high_priority_deadline_ms: Deadline for high priority LLM requests
        normal_priority_deadline_ms: Deadline for normal priority LLM requests
        low_priority_deadline_ms: Deadline for low priority LLM requests
        embedding_high_priority_deadline_ms: Deadline for high priority embedding requests
        embedding_normal_priority_deadline_ms: Deadline for normal priority embedding requests
        embedding_low_priority_deadline_ms: Deadline for low priority embedding requests
    """

    # Embedding requests typically have tighter SLOs (faster expected response)
    embedding_high_priority_deadline_ms: int = 100
    embedding_normal_priority_deadline_ms: int = 200
    embedding_low_priority_deadline_ms: int = 500

    def get_deadline_for_request(self, priority: str, request_type: RequestType | str) -> int:
        """Get SLO deadline for a given priority and request type.

        Args:
            priority: Priority level (HIGH, NORMAL, LOW)
            request_type: Type of request (llm_chat, llm_generate, embedding)

        Returns:
            SLO deadline in milliseconds
        """
        if isinstance(request_type, str):
            request_type = RequestType(request_type)

        if request_type == RequestType.EMBEDDING:
            priority_map = {
                "HIGH": self.embedding_high_priority_deadline_ms,
                "NORMAL": self.embedding_normal_priority_deadline_ms,
                "LOW": self.embedding_low_priority_deadline_ms,
            }
        else:
            # LLM requests use base SLO config
            priority_map = {
                "HIGH": self.high_priority_deadline_ms,
                "NORMAL": self.normal_priority_deadline_ms,
                "LOW": self.low_priority_deadline_ms,
            }

        return priority_map.get(priority.upper(), priority_map.get("NORMAL", 1000))

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "embedding_high_priority_deadline_ms": self.embedding_high_priority_deadline_ms,
                "embedding_normal_priority_deadline_ms": self.embedding_normal_priority_deadline_ms,
                "embedding_low_priority_deadline_ms": self.embedding_low_priority_deadline_ms,
            }
        )
        return base_dict


@dataclass
class HybridBenchmarkConfig(BaseBenchmarkConfig):
    """Hybrid (LLM + Embedding) benchmark configuration.

    Extends BaseBenchmarkConfig with hybrid-specific parameters for
    mixed LLM and Embedding workload benchmarking.

    Attributes:
        llm_ratio: Ratio of LLM requests (0.0 to 1.0)
        embedding_ratio: Ratio of Embedding requests (0.0 to 1.0, should sum to 1.0 with llm_ratio)

        llm_model_distribution: Distribution of LLM requests across models
        embedding_model: Embedding model to use
        embedding_batch_sizes: List of batch sizes to test for embedding requests

        prompt_len_range: Range of prompt lengths (min, max) in tokens for LLM
        output_len_range: Range of output lengths (min, max) in tokens for LLM
        embedding_text_len_range: Range of text lengths (min, max) in chars for embedding

        enable_streaming: Whether to use streaming for LLM responses
        hybrid_slo_config: SLO configuration for both LLM and Embedding

        llm_dataset_path: Optional path to LLM prompts dataset
        embedding_dataset_path: Optional path to embedding texts dataset
    """

    # Request type distribution
    llm_ratio: float = 0.5
    embedding_ratio: float = 0.5

    # LLM configuration
    llm_model_distribution: dict[str, float] = field(
        default_factory=lambda: {"Qwen/Qwen2.5-7B-Instruct": 1.0}
    )
    prompt_len_range: tuple[int, int] = (50, 500)
    output_len_range: tuple[int, int] = (50, 200)
    enable_streaming: bool = True

    # Embedding configuration
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_batch_sizes: list[int] = field(default_factory=lambda: [1, 4, 8, 16, 32])
    embedding_text_len_range: tuple[int, int] = (50, 500)

    # SLO configuration (hybrid-specific)
    hybrid_slo_config: HybridSLOConfig = field(default_factory=HybridSLOConfig)

    # Data sources
    llm_dataset_path: Path | None = None
    embedding_dataset_path: Path | None = None

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = self.validate_base()

        # Validate ratio sum
        ratio_sum = self.llm_ratio + self.embedding_ratio
        if abs(ratio_sum - 1.0) > 0.01:
            errors.append(f"llm_ratio + embedding_ratio should sum to 1.0 (got {ratio_sum})")

        # Validate ratios are non-negative
        if self.llm_ratio < 0:
            errors.append("llm_ratio must be non-negative")
        if self.embedding_ratio < 0:
            errors.append("embedding_ratio must be non-negative")

        # Validate LLM model distribution sums to ~1.0
        if self.llm_ratio > 0:
            model_prob_sum = sum(self.llm_model_distribution.values())
            if abs(model_prob_sum - 1.0) > 0.01:
                errors.append(
                    f"llm_model_distribution probabilities should sum to 1.0 (got {model_prob_sum})"
                )

        # Validate prompt length range
        if self.prompt_len_range[0] > self.prompt_len_range[1]:
            errors.append("prompt_len_range min should not exceed max")

        # Validate output length range
        if self.output_len_range[0] > self.output_len_range[1]:
            errors.append("output_len_range min should not exceed max")

        # Validate embedding text length range
        if self.embedding_text_len_range[0] > self.embedding_text_len_range[1]:
            errors.append("embedding_text_len_range min should not exceed max")

        # Validate embedding batch sizes
        if not self.embedding_batch_sizes:
            errors.append("embedding_batch_sizes cannot be empty")
        else:
            for bs in self.embedding_batch_sizes:
                if bs <= 0:
                    errors.append(f"embedding batch size must be positive (got {bs})")

        # Validate policies support hybrid scheduling
        from ..common.strategy_adapter import StrategyAdapter

        hybrid_strategies = StrategyAdapter.list_hybrid_strategies()
        for policy in self.policies:
            if policy not in hybrid_strategies:
                errors.append(
                    f"Policy '{policy}' may not support hybrid scheduling. "
                    f"Recommended: {hybrid_strategies}"
                )

        return errors

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HybridBenchmarkConfig:
        """Create configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            HybridBenchmarkConfig instance
        """
        # Handle hybrid SLO config
        hybrid_slo_data = data.get("hybrid_slo_config", data.get("slo_config", {}))
        hybrid_slo_config = (
            HybridSLOConfig(**hybrid_slo_data) if hybrid_slo_data else HybridSLOConfig()
        )

        # Handle arrival pattern
        arrival_pattern = data.get("arrival_pattern", "poisson")
        if isinstance(arrival_pattern, str):
            arrival_pattern = ArrivalPattern(arrival_pattern)

        # Handle paths
        llm_dataset_path = data.get("llm_dataset_path")
        if llm_dataset_path:
            llm_dataset_path = Path(llm_dataset_path)

        embedding_dataset_path = data.get("embedding_dataset_path")
        if embedding_dataset_path:
            embedding_dataset_path = Path(embedding_dataset_path)

        output_dir = data.get("output_dir", "./.benchmarks")
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        # Handle tuple fields
        prompt_len_range = data.get("prompt_len_range", [50, 500])
        if isinstance(prompt_len_range, list):
            prompt_len_range = tuple(prompt_len_range)

        output_len_range = data.get("output_len_range", [50, 200])
        if isinstance(output_len_range, list):
            output_len_range = tuple(output_len_range)

        embedding_text_len_range = data.get("embedding_text_len_range", [50, 500])
        if isinstance(embedding_text_len_range, list):
            embedding_text_len_range = tuple(embedding_text_len_range)

        return cls(
            # Base config
            control_plane_url=data.get("control_plane_url", "http://localhost:8888"),
            policies=data.get("policies", ["hybrid", "fifo", "priority"]),
            num_requests=data.get("num_requests", 100),
            request_rate=data.get("request_rate", 10.0),
            arrival_pattern=arrival_pattern,
            priority_distribution=data.get(
                "priority_distribution",
                {"HIGH": 0.2, "NORMAL": 0.6, "LOW": 0.2},
            ),
            slo_config=hybrid_slo_config,  # Use hybrid SLO as base SLO
            timeout_seconds=data.get("timeout_seconds", 60.0),
            warmup_requests=data.get("warmup_requests", 10),
            concurrent_requests=data.get("concurrent_requests", 50),
            output_dir=output_dir,
            auto_visualize=data.get("auto_visualize", True),
            # Hybrid-specific
            llm_ratio=data.get("llm_ratio", 0.5),
            embedding_ratio=data.get("embedding_ratio", 0.5),
            llm_model_distribution=data.get(
                "llm_model_distribution",
                {"Qwen/Qwen2.5-7B-Instruct": 1.0},
            ),
            prompt_len_range=prompt_len_range,
            output_len_range=output_len_range,
            enable_streaming=data.get("enable_streaming", True),
            embedding_model=data.get("embedding_model", "BAAI/bge-large-en-v1.5"),
            embedding_batch_sizes=data.get("embedding_batch_sizes", [1, 4, 8, 16, 32]),
            embedding_text_len_range=embedding_text_len_range,
            hybrid_slo_config=hybrid_slo_config,
            llm_dataset_path=llm_dataset_path,
            embedding_dataset_path=embedding_dataset_path,
        )

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> HybridBenchmarkConfig:
        """Create configuration from YAML file.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            HybridBenchmarkConfig instance
        """
        yaml_path = Path(yaml_path)
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        base_dict = self.to_base_dict()
        base_dict.update(
            {
                # Hybrid-specific
                "llm_ratio": self.llm_ratio,
                "embedding_ratio": self.embedding_ratio,
                "llm_model_distribution": self.llm_model_distribution,
                "prompt_len_range": list(self.prompt_len_range),
                "output_len_range": list(self.output_len_range),
                "enable_streaming": self.enable_streaming,
                "embedding_model": self.embedding_model,
                "embedding_batch_sizes": self.embedding_batch_sizes,
                "embedding_text_len_range": list(self.embedding_text_len_range),
                "hybrid_slo_config": self.hybrid_slo_config.to_dict(),
                "llm_dataset_path": str(self.llm_dataset_path) if self.llm_dataset_path else None,
                "embedding_dataset_path": (
                    str(self.embedding_dataset_path) if self.embedding_dataset_path else None
                ),
            }
        )
        return base_dict

    def to_yaml(self, yaml_path: str | Path) -> None:
        """Save configuration to YAML file.

        Args:
            yaml_path: Path to save YAML configuration
        """
        yaml_path = Path(yaml_path)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        with open(yaml_path, "w") as f:
            yaml.safe_dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)


# Re-export from base for convenience
__all__ = [
    "HybridBenchmarkConfig",
    "HybridSLOConfig",
    "RequestType",
    "ArrivalPattern",
    "SchedulingPolicy",
]
