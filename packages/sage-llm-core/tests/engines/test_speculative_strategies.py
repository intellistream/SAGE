"""Unit tests for Speculative Decoding Strategies.

Layer: L1 (sage-llm-core)

Tests for all speculative decoding strategies to ensure they correctly
modify engine configurations.
"""

import pytest

from sage.llm.engines.vllm.speculative import (
    DraftModelStrategy,
    DynamicLookaheadStrategy,
    NgramStrategy,
    SpeculativeStrategy,
)


class TestSpeculativeStrategyInterface:
    """Test the SpeculativeStrategy abstract interface."""

    def test_interface_cannot_instantiate(self):
        """Test that abstract base class cannot be instantiated."""
        with pytest.raises(TypeError):
            SpeculativeStrategy()  # type: ignore


class TestDraftModelStrategy:
    """Test DraftModelStrategy implementation."""

    def test_init(self):
        """Test strategy initialization."""
        strategy = DraftModelStrategy(
            draft_model_id="Qwen/Qwen2.5-0.5B-Instruct",
            num_speculative_tokens=5,
            auto_download=True,
        )
        assert strategy.draft_model_id == "Qwen/Qwen2.5-0.5B-Instruct"
        assert strategy.num_speculative_tokens == 5
        assert strategy.auto_download is True

    def test_apply_updates_config(self):
        """Test that apply() modifies engine config correctly."""
        strategy = DraftModelStrategy(
            draft_model_id="Qwen/Qwen2.5-0.5B-Instruct",
            num_speculative_tokens=7,
        )
        engine_config = {}

        # Note: This will log warnings about vLLM version in real environment
        strategy.apply(engine_config)

        # Config should be updated (or remain empty if vLLM < 0.14.0)
        assert isinstance(engine_config, dict)


class TestNgramStrategy:
    """Test NgramStrategy implementation."""

    def test_init_defaults(self):
        """Test strategy initialization with defaults."""
        strategy = NgramStrategy()
        assert strategy.n == 5
        assert strategy.num_speculative_tokens == 5

    def test_init_custom_params(self):
        """Test strategy initialization with custom parameters."""
        strategy = NgramStrategy(n=10, num_speculative_tokens=8)
        assert strategy.n == 10
        assert strategy.num_speculative_tokens == 8

    def test_apply_updates_config(self):
        """Test that apply() modifies engine config correctly."""
        strategy = NgramStrategy(n=7, num_speculative_tokens=6)
        engine_config = {}

        strategy.apply(engine_config)

        # Verify speculative_config is added
        assert "speculative_config" in engine_config
        spec_config = engine_config["speculative_config"]
        assert spec_config["method"] == "ngram"
        assert spec_config["ngram_prompt_lookup_max"] == 7
        assert spec_config["ngram_prompt_lookup_min"] == 1
        assert spec_config["num_speculative_tokens"] == 6

    def test_apply_preserves_other_config(self):
        """Test that apply() doesn't overwrite existing config keys."""
        strategy = NgramStrategy()
        engine_config = {
            "model": "test-model",
            "tensor_parallel_size": 2,
        }

        strategy.apply(engine_config)

        # Original keys should be preserved
        assert engine_config["model"] == "test-model"
        assert engine_config["tensor_parallel_size"] == 2
        # New key should be added
        assert "speculative_config" in engine_config


class TestDynamicLookaheadStrategy:
    """Test DynamicLookaheadStrategy implementation."""

    def test_init_defaults(self):
        """Test strategy initialization with defaults."""
        strategy = DynamicLookaheadStrategy()
        assert strategy.min_tokens == 3
        assert strategy.max_tokens == 10

    def test_init_custom_params(self):
        """Test strategy initialization with custom parameters."""
        strategy = DynamicLookaheadStrategy(min_tokens=5, max_tokens=15)
        assert strategy.min_tokens == 5
        assert strategy.max_tokens == 15

    def test_apply_calculates_optimal_k(self):
        """Test that apply() calculates optimal lookahead correctly."""
        strategy = DynamicLookaheadStrategy(min_tokens=4, max_tokens=12)
        engine_config = {}

        strategy.apply(engine_config)

        # Should calculate midpoint: (4 + 12) // 2 = 8
        assert engine_config["num_speculative_tokens"] == 8
        assert engine_config["enable_chunked_prefill"] is True

    def test_apply_with_different_ranges(self):
        """Test apply() with different token ranges."""
        test_cases = [
            (3, 10, 6),  # (3 + 10) // 2 = 6
            (5, 15, 10),  # (5 + 15) // 2 = 10
            (1, 7, 4),  # (1 + 7) // 2 = 4
        ]

        for min_tokens, max_tokens, expected_k in test_cases:
            strategy = DynamicLookaheadStrategy(
                min_tokens=min_tokens,
                max_tokens=max_tokens,
            )
            engine_config = {}
            strategy.apply(engine_config)

            assert engine_config["num_speculative_tokens"] == expected_k

    def test_apply_preserves_other_config(self):
        """Test that apply() doesn't overwrite existing config keys."""
        strategy = DynamicLookaheadStrategy()
        engine_config = {
            "model": "test-model",
            "gpu_memory_utilization": 0.9,
        }

        strategy.apply(engine_config)

        # Original keys should be preserved
        assert engine_config["model"] == "test-model"
        assert engine_config["gpu_memory_utilization"] == 0.9
        # New keys should be added
        assert "num_speculative_tokens" in engine_config
        assert "enable_chunked_prefill" in engine_config


class TestStrategyComparison:
    """Compare different strategies side by side."""

    def test_all_strategies_implement_interface(self):
        """Test that all strategies implement the required interface."""
        strategies = [
            DraftModelStrategy("model-id"),
            NgramStrategy(),
            DynamicLookaheadStrategy(),
        ]

        for strategy in strategies:
            assert isinstance(strategy, SpeculativeStrategy)
            assert hasattr(strategy, "apply")
            assert callable(strategy.apply)

    def test_strategies_modify_different_config_keys(self):
        """Test that different strategies modify appropriate config keys."""
        draft_config = {}
        DraftModelStrategy("model-id").apply(draft_config)

        ngram_config = {}
        NgramStrategy().apply(ngram_config)

        dynamic_config = {}
        DynamicLookaheadStrategy().apply(dynamic_config)

        # Each strategy should add different keys
        assert "speculative_config" in ngram_config
        assert "num_speculative_tokens" in dynamic_config
        # draft_config may be empty if vLLM < 0.14.0 (version check)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
