"""Demo: Speculative Decoding Strategies in SAGE.

This example demonstrates how to use different speculative decoding strategies
with vLLM engines through the Control Plane.

Layer: L1 (sage-llm-core)
"""

import logging

from sage.llm import (
    DraftModelStrategy,
    DynamicLookaheadStrategy,
    NgramStrategy,
    VLLMService,
    VLLMServiceConfig,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_ngram_strategy():
    """Demo 1: N-gram based speculative decoding (lightweight)."""
    logger.info("\n" + "=" * 70)
    logger.info("Demo 1: N-gram Strategy (No draft model required)")
    logger.info("=" * 70)

    strategy = NgramStrategy(n=5, num_speculative_tokens=5)

    config = VLLMServiceConfig(
        model_id="Qwen/Qwen2.5-7B-Instruct",
        auto_download=True,
        speculative_strategy=strategy,
    )

    _ = VLLMService(config)
    # Initialize service for demonstration
    # In production: service.setup() and use...


def demo_draft_model_strategy():
    """Demo 2: Draft model based speculative decoding."""
    logger.info("\n" + "=" * 70)
    logger.info("Demo 2: Draft Model Strategy (Requires vLLM >= 0.14.0)")
    logger.info("=" * 70)

    # Use a smaller model as draft for faster speculation
    strategy = DraftModelStrategy(
        draft_model_id="Qwen/Qwen2.5-0.5B-Instruct",
        num_speculative_tokens=5,
        auto_download=True,
    )

    config = VLLMServiceConfig(
        model_id="Qwen/Qwen2.5-7B-Instruct",
        auto_download=True,
        speculative_strategy=strategy,
    )

    _ = VLLMService(config)
    # Initialize service for demonstration
    # In production: service.setup() and use...


def demo_dynamic_lookahead_strategy():
    """Demo 3: Dynamic lookahead strategy (research-grade)."""
    logger.info("\n" + "=" * 70)
    logger.info("Demo 3: Dynamic Lookahead Strategy (Adaptive)")
    logger.info("=" * 70)

    # Advanced strategy that can be extended for research
    strategy = DynamicLookaheadStrategy(min_tokens=3, max_tokens=10)

    config = VLLMServiceConfig(
        model_id="Qwen/Qwen2.5-7B-Instruct",
        auto_download=True,
        speculative_strategy=strategy,
    )

    _ = VLLMService(config)
    # Initialize service for demonstration
    # In production: service.setup() and use...


def demo_control_plane_integration():
    """Demo 4: Speculative decoding through Control Plane."""
    logger.info("\n" + "=" * 70)
    logger.info("Demo 4: Control Plane Integration")
    logger.info("=" * 70)

    # When starting engines through Control Plane, you can pass strategies
    # via the engine configuration

    from sage.llm.control_plane import ControlPlaneManager

    _ = ControlPlaneManager(scheduling_policy="adaptive")

    # Example: Start engine with N-gram speculative decoding
    # (This would be integrated into the start_engine method)
    engine_config = {
        "model_id": "Qwen/Qwen2.5-7B-Instruct",
        "speculative_strategy": NgramStrategy(n=5),
        # Other config...
    }

    logger.info("Engine config prepared with speculative strategy")
    logger.info(f"Strategy: {engine_config['speculative_strategy']}")


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("Speculative Decoding Strategies Demo")
    logger.info("=" * 70)

    # Run demos (commented out to avoid actual model loading)
    # demo_ngram_strategy()
    # demo_draft_model_strategy()
    # demo_dynamic_lookahead_strategy()
    demo_control_plane_integration()

    logger.info("\n✅ All demos completed")
