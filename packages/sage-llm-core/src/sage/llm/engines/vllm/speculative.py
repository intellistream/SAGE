"""Speculative Decoding Strategies for SAGE LLM Service.

Layer: L1 (sage-llm-core)

This module defines the interface and implementations for speculative decoding strategies.
It allows researchers and developers to easily plug in different draft models or
algorithms (like N-gram, Eagle, Medusa) by implementing the `SpeculativeStrategy` interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from sage.common.model_registry import vllm_registry

logger = logging.getLogger(__name__)


class SpeculativeStrategy(ABC):
    """Abstract base class for speculative decoding strategies."""

    @abstractmethod
    def apply(self, engine_config: dict[str, Any]) -> None:
        """Apply the strategy to the vLLM engine configuration.

        Args:
            engine_config: The dictionary of arguments that will be passed to vLLM's LLM constructor.
                           Implementations should modify this dictionary in-place.
        """
        pass


class DraftModelStrategy(SpeculativeStrategy):
    """Standard speculative decoding using a separate draft model (e.g., Qwen-0.5B for Qwen-7B)."""

    def __init__(
        self,
        draft_model_id: str,
        num_speculative_tokens: int = 5,
        auto_download: bool = True,
    ):
        self.draft_model_id = draft_model_id
        self.num_speculative_tokens = num_speculative_tokens
        self.auto_download = auto_download

    def apply(self, engine_config: dict[str, Any]) -> None:
        logger.info(f"Preparing draft model for speculative decoding: {self.draft_model_id}")

        # Check vLLM version for compatibility
        try:
            import vllm
            from packaging import version

            vllm_version = version.parse(vllm.__version__)
            # vLLM 0.12.0 does not support generic draft models via 'speculative_model'
            # It requires specific implementations like Eagle, Medusa, etc.
            # Generic draft model support is expected in future versions (e.g. >= 0.14.0)
            if vllm_version < version.parse("0.14.0"):
                logger.warning(
                    f"vLLM version {vllm_version} does not support generic draft model speculative decoding "
                    "(requires >= 0.14.0). Falling back to standard decoding."
                )
                return
        except ImportError:
            pass

        # Ensure the draft model is available locally
        path = vllm_registry.ensure_model_available(
            self.draft_model_id,
            auto_download=self.auto_download,
        )

        # Configure vLLM arguments
        engine_config["speculative_model"] = str(path)
        engine_config["num_speculative_tokens"] = self.num_speculative_tokens

        logger.info(
            f"Speculative decoding enabled. "
            f"Draft model: {self.draft_model_id}, "
            f"Lookahead: {self.num_speculative_tokens}"
        )


class NgramStrategy(SpeculativeStrategy):
    """N-gram based speculative decoding (lightweight, no extra model required)."""

    def __init__(self, n: int = 5, num_speculative_tokens: int = 5):
        self.n = n
        self.num_speculative_tokens = num_speculative_tokens

    def apply(self, engine_config: dict[str, Any]) -> None:
        logger.info(f"Enabling N-gram speculative decoding (n={self.n})")

        # Use speculative_config for vLLM (supports both legacy and new versions via dict)
        engine_config["speculative_config"] = {
            "method": "ngram",
            "ngram_prompt_lookup_max": self.n,
            "ngram_prompt_lookup_min": 1,
            "num_speculative_tokens": self.num_speculative_tokens,
        }

        logger.info("N-gram speculative decoding enabled.")


class DynamicLookaheadStrategy(SpeculativeStrategy):
    """Advanced strategy that adjusts lookahead based on system load.

    This is a research-grade implementation that can be extended to incorporate
    runtime metrics, adaptive algorithms, or custom draft model selection logic.

    Args:
        min_tokens: Minimum number of speculative tokens (default: 3)
        max_tokens: Maximum number of speculative tokens (default: 10)
    """

    def __init__(self, min_tokens: int = 3, max_tokens: int = 10):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens

    def apply(self, engine_config: dict[str, Any]) -> None:
        """Apply dynamic lookahead strategy to engine configuration.

        In a real research scenario, this might involve:
        - Monitoring system load and GPU utilization
        - Adjusting speculative tokens based on request patterns
        - Runtime hooks for adaptive optimization

        Currently implements a simplified version for demonstration.
        """
        logger.info("Applying DynamicLookaheadStrategy (Research Demo)")

        # Simulate "research" logic - in practice, this could query metrics,
        # analyze request patterns, or use ML models to optimize k
        optimal_k = (self.min_tokens + self.max_tokens) // 2

        engine_config["num_speculative_tokens"] = optimal_k
        # Maybe enable some experimental vLLM flags for better performance
        engine_config["enable_chunked_prefill"] = True

        logger.info(
            f"DynamicLookaheadStrategy configured: k={optimal_k}, "
            f"range=[{self.min_tokens}, {self.max_tokens}]"
        )


__all__ = [
    "SpeculativeStrategy",
    "DraftModelStrategy",
    "NgramStrategy",
    "DynamicLookaheadStrategy",
]
