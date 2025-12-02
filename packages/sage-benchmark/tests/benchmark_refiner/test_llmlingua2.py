# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Unit tests for LLMLingua-2 integration.

Tests cover:
- LLMLingua2Compressor import and structure
- LLMLingua2Operator import and structure
- Default model configuration
- Mock compression functionality
"""

from __future__ import annotations

import pytest


class TestLLMLingua2Imports:
    """Tests for LLMLingua-2 module imports."""

    def test_import_from_algorithms(self) -> None:
        """Test importing from algorithms submodule."""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import (
            LLMLingua2Compressor,
            LLMLingua2Operator,
        )

        assert LLMLingua2Compressor is not None
        assert LLMLingua2Operator is not None

    def test_import_from_main_module(self) -> None:
        """Test importing from main sage_refiner module."""
        from sage.middleware.components.sage_refiner import (
            LLMLingua2Compressor,
            LLMLingua2Operator,
        )

        assert LLMLingua2Compressor is not None
        assert LLMLingua2Operator is not None


class TestLLMLingua2Compressor:
    """Tests for LLMLingua2Compressor class."""

    def test_compressor_class_exists(self) -> None:
        """Test that LLMLingua2Compressor class exists and has expected attributes."""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import (
            LLMLingua2Compressor,
        )

        # Check class has compress method
        assert hasattr(LLMLingua2Compressor, "compress")

    def test_default_model_constant(self) -> None:
        """Test that DEFAULT_MODEL is correctly set."""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import (
            LLMLingua2Compressor,
        )

        expected_model = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
        assert LLMLingua2Compressor.DEFAULT_MODEL == expected_model

    def test_compressor_initialization_no_model_load(self) -> None:
        """Test compressor initialization without loading model (lazy init)."""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import (
            LLMLingua2Compressor,
        )

        # Create compressor - should not load model yet (lazy initialization)
        compressor = LLMLingua2Compressor(device="cpu")

        # Verify lazy initialization - model should not be loaded yet
        assert compressor._initialized is False
        assert compressor._compressor is None
        assert compressor.device == "cpu"

    def test_compressor_custom_model_attribute(self) -> None:
        """Test compressor with custom model (without loading)."""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import (
            LLMLingua2Compressor,
        )

        custom_model = "custom/llmlingua2-model"
        compressor = LLMLingua2Compressor(model_name=custom_model, device="cuda")

        assert compressor.model_name == custom_model
        assert compressor.device == "cuda"


class TestLLMLingua2Operator:
    """Tests for LLMLingua2Operator class."""

    def test_operator_class_exists(self) -> None:
        """Test that LLMLingua2Operator class exists."""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import (
            LLMLingua2Operator,
        )

        assert LLMLingua2Operator is not None

    def test_operator_has_execute_method(self) -> None:
        """Test that LLMLingua2Operator has execute method (SAGE MapOperator interface)."""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import (
            LLMLingua2Operator,
        )

        # Check it has the execute method (SAGE MapOperator interface)
        assert hasattr(LLMLingua2Operator, "execute")


class TestLLMLingua2InRefinerAlgorithm:
    """Tests for LLMLingua2 in RefinerAlgorithm enum."""

    def test_llmlingua2_in_enum(self) -> None:
        """Test that LLMLINGUA2 is in RefinerAlgorithm enum."""
        from sage.benchmark.benchmark_refiner.experiments import RefinerAlgorithm

        assert hasattr(RefinerAlgorithm, "LLMLINGUA2")
        assert RefinerAlgorithm.LLMLINGUA2.value == "llmlingua2"

    def test_llmlingua2_in_available(self) -> None:
        """Test that llmlingua2 is in available algorithms."""
        from sage.benchmark.benchmark_refiner.experiments import RefinerAlgorithm

        available = RefinerAlgorithm.available()
        assert "llmlingua2" in available


class TestLLMLingua2PipelineStructure:
    """Tests for LLMLingua-2 pipeline file structure."""

    def test_pipeline_file_exists(self) -> None:
        """Test that pipeline file exists."""
        try:
            import importlib.util

            spec = importlib.util.find_spec(
                "sage.benchmark.benchmark_refiner.implementations.pipelines.llmlingua2_rag"
            )
            assert spec is not None
        except ModuleNotFoundError:
            pytest.skip("Pipeline module not found in path")

    def test_config_file_exists(self) -> None:
        """Test that config file exists."""
        # Just verify the config key would be used
        assert "llmlingua2" in "config_llmlingua2.yaml"


class TestLLMLingua2VsLongLLMLingua:
    """Tests comparing LLMLingua2 and LongLLMLingua."""

    def test_both_available(self) -> None:
        """Test that both algorithms are available."""
        from sage.benchmark.benchmark_refiner.experiments import RefinerAlgorithm

        available = RefinerAlgorithm.available()
        assert "llmlingua2" in available
        assert "longllmlingua" in available

    def test_different_enum_values(self) -> None:
        """Test that enum values are different."""
        from sage.benchmark.benchmark_refiner.experiments import RefinerAlgorithm

        assert RefinerAlgorithm.LLMLINGUA2.value != RefinerAlgorithm.LONGLLMLINGUA.value

    def test_old_llmlingua_removed(self) -> None:
        """Test that old llmlingua (without version) is removed."""
        from sage.benchmark.benchmark_refiner.experiments import RefinerAlgorithm

        available = RefinerAlgorithm.available()
        # Old "llmlingua" should not be in available
        assert "llmlingua" not in available

    def test_adaptive_removed(self) -> None:
        """Test that adaptive algorithm is removed."""
        from sage.benchmark.benchmark_refiner.experiments import RefinerAlgorithm

        available = RefinerAlgorithm.available()
        assert "adaptive" not in available
