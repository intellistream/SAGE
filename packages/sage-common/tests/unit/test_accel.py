# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Tests for acceleration module (quantization, sparsity, cost model)."""

import pytest

pytest.importorskip("torch")

import torch

from sage.common.components.sage_llm.sageLLM.accel import (
    CostEstimator,
    FP8E4M3Quantizer,
    INT4Quantizer,
    INT8Quantizer,
    LayerQuantizationPolicy,
    MixedPrecisionQuantizer,
    ModelProfile,
    NF4Quantizer,
    NMPattern,
    QuantizationConfig,
    QuantizationGranularity,
    QuantizationType,
    QuantizerRegistry,
    StructuredPruner,
)


@pytest.fixture()
def fp8_gpu_mock(monkeypatch):
    """Mock CUDA availability/capability for FP8 tests on CPU-only envs."""

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "get_device_capability", lambda *_args, **_kwargs: (8, 0))


class TestQuantization:
    """Test quantization functionality."""

    def test_fp8_e4m3_quantization(self, fp8_gpu_mock):
        """Test FP8 E4M3 quantization."""
        weight = torch.randn(128, 512)
        quantizer = QuantizerRegistry.get(QuantizationType.FP8_E4M3)
        config = QuantizationConfig(
            quant_type=QuantizationType.FP8_E4M3,
            granularity=QuantizationGranularity.PER_TENSOR,
        )

        output = quantizer.quantize(weight, config)
        reconstructed = quantizer.dequantize(output)

        assert output.quantized_weight.dtype == torch.float16  # Simulated FP8 (uses FP16)
        assert output.scales is not None
        assert reconstructed.shape == weight.shape

        # Check quantization error is bounded
        error = (reconstructed - weight).abs().mean()
        assert error < 0.1 * weight.abs().mean()

    def test_int4_quantization(self):
        """Test INT4 quantization."""
        weight = torch.randn(256, 1024)
        quantizer = INT4Quantizer()
        config = QuantizationConfig(
            quant_type=QuantizationType.INT4,
            granularity=QuantizationGranularity.PER_GROUP,
            group_size=128,
            use_symmetric=False,
        )

        output = quantizer.quantize(weight, config)
        reconstructed = quantizer.dequantize(output)

        assert output.quantized_weight.dtype == torch.int8
        assert output.scales.shape[1] == (1024 + 127) // 128  # num_groups
        assert reconstructed.shape == weight.shape

    def test_int8_quantization(self):
        """Test INT8 quantization."""
        weight = torch.randn(128, 256)
        quantizer = INT8Quantizer()
        config = QuantizationConfig(
            quant_type=QuantizationType.INT8,
            granularity=QuantizationGranularity.PER_CHANNEL,
        )

        output = quantizer.quantize(weight, config)
        reconstructed = quantizer.dequantize(output)

        assert output.quantized_weight.dtype == torch.int8
        assert output.scales.shape[0] == 128  # per output channel
        assert reconstructed.shape == weight.shape

    def test_nf4_quantization(self):
        """Test NF4 quantization."""
        weight = torch.randn(64, 128)
        quantizer = NF4Quantizer()
        config = QuantizationConfig(quant_type=QuantizationType.NF4)

        output = quantizer.quantize(weight, config)
        reconstructed = quantizer.dequantize(output)

        assert output.quantized_weight.dtype == torch.int8
        assert 0 <= output.quantized_weight.max() <= 15  # 16 grid points
        assert reconstructed.shape == weight.shape

    def test_registry(self, fp8_gpu_mock):
        """Test quantizer registry."""
        fp8_quantizer = QuantizerRegistry.get(QuantizationType.FP8_E4M3)
        assert isinstance(fp8_quantizer, FP8E4M3Quantizer)

        int4_quantizer = QuantizerRegistry.get(QuantizationType.INT4)
        assert isinstance(int4_quantizer, INT4Quantizer)


class TestMixedPrecision:
    """Test mixed precision quantization."""

    def test_mixed_precision_policy(self, fp8_gpu_mock):
        """Test mixed precision quantization."""
        policies = [
            LayerQuantizationPolicy(
                "embed",
                QuantizationType.FP8_E4M3,
                QuantizationConfig(quant_type=QuantizationType.FP8_E4M3),
            ),
            LayerQuantizationPolicy(
                "attention",
                QuantizationType.INT8,
                QuantizationConfig(quant_type=QuantizationType.INT8),
            ),
            LayerQuantizationPolicy(
                "mlp",
                QuantizationType.INT4,
                QuantizationConfig(
                    quant_type=QuantizationType.INT4,
                    group_size=128,
                ),
            ),
        ]

        quantizer = MixedPrecisionQuantizer(policies)

        # Mock model state dict
        state_dict = {
            "embed.weight": torch.randn(32000, 4096),
            "attention.query.weight": torch.randn(4096, 4096),
            "mlp.gate.weight": torch.randn(11008, 4096),
        }

        quantized_state = quantizer.quantize_model(state_dict)

        assert "embed.weight" in quantized_state
        assert "attention.query.weight" in quantized_state
        assert "mlp.gate.weight" in quantized_state


class TestSparsity:
    """Test structured sparsity."""

    def test_2_4_sparsity(self):
        """Test 2:4 structured sparsity."""
        weight = torch.randn(128, 512)
        pruner = StructuredPruner(NMPattern.TWO_FOUR)

        output = pruner.prune(weight)

        assert output.pattern == NMPattern.TWO_FOUR
        assert 0.45 < output.sparsity_ratio < 0.55  # ~50% sparse

        # Check 2:4 pattern: every 4 elements has 2 non-zeros
        flattened = output.sparse_weight.view(-1, 4)
        non_zeros_per_group = (flattened != 0).sum(dim=-1)
        assert (non_zeros_per_group == 2).all()

    def test_prune_model(self):
        """Test model-level pruning."""
        state_dict = {
            "layer1.weight": torch.randn(256, 512),
            "layer2.weight": torch.randn(128, 256),
            "layer3.bias": torch.randn(128),  # Should not be pruned
        }

        pruner = StructuredPruner(NMPattern.TWO_FOUR)
        sparse_state = pruner.prune_model(state_dict)

        assert "layer1.weight" in sparse_state
        assert "layer2.weight" in sparse_state
        assert "layer3.bias" in sparse_state

        # Bias should remain unchanged
        assert torch.equal(sparse_state["layer3.bias"], state_dict["layer3.bias"])


class TestCostModel:
    """Test cost modeling."""

    def test_cost_estimation_fp16(self):
        """Test cost estimation for FP16 model."""
        profile = ModelProfile(
            num_layers=32,
            hidden_size=4096,
            num_attention_heads=32,
            intermediate_size=11008,
            vocab_size=32000,
        )

        estimator = CostEstimator(profile)
        metrics = estimator.estimate(
            batch_size=8,
            seq_length=2048,
            quant_type=QuantizationType.FP16,
        )

        # Check basic properties
        assert metrics.weight_memory > 0
        assert metrics.kv_cache_memory > 0
        assert metrics.prefill_latency_per_token > 0
        assert metrics.decode_latency_per_token > 0
        assert metrics.max_throughput_tokens_per_sec > 0

        # FP16 should use 2 bytes per parameter
        assert 10 < metrics.weight_memory < 20  # ~7B model

    def test_cost_estimation_int4(self):
        """Test cost estimation for INT4 model."""
        profile = ModelProfile(
            num_layers=32,
            hidden_size=4096,
            num_attention_heads=32,
            intermediate_size=11008,
            vocab_size=32000,
        )

        estimator = CostEstimator(profile)
        metrics_fp16 = estimator.estimate(quant_type=QuantizationType.FP16)
        metrics_int4 = estimator.estimate(quant_type=QuantizationType.INT4)

        # INT4 should use 4x less memory than FP16
        assert metrics_int4.weight_memory < metrics_fp16.weight_memory / 3.5

    def test_param_counting(self):
        """Test parameter counting."""
        profile = ModelProfile(
            num_layers=2,
            hidden_size=512,
            num_attention_heads=8,
            intermediate_size=2048,
            vocab_size=10000,
        )

        estimator = CostEstimator(profile)

        # Manual calculation
        embed_params = 10000 * 512
        layer_params = (
            4 * 512 * 512  # Attention
            + 2 * 512 * 2048  # MLP
            + 2 * 512  # LayerNorm
        ) * 2
        lm_head_params = 512 * 10000

        expected_params = embed_params + layer_params + lm_head_params
        actual_params = estimator._count_params()

        assert actual_params == expected_params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
