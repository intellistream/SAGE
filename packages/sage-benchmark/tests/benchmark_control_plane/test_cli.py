# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Unit tests for the benchmark CLI module.

Tests cover:
- CLI app creation
- Configuration loading
- BenchmarkMode enum
- Helper functions
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sage.benchmark.benchmark_control_plane.cli import (
    BenchmarkMode,
    load_config_file,
)


# =============================================================================
# Tests for BenchmarkMode
# =============================================================================
class TestBenchmarkMode:
    """Tests for BenchmarkMode enum."""

    def test_llm_mode(self) -> None:
        """Test LLM mode."""
        assert BenchmarkMode.LLM == "llm"
        assert BenchmarkMode.LLM.value == "llm"

    def test_hybrid_mode(self) -> None:
        """Test Hybrid mode."""
        assert BenchmarkMode.HYBRID == "hybrid"
        assert BenchmarkMode.HYBRID.value == "hybrid"

    def test_all_modes(self) -> None:
        """Test all available modes."""
        modes = list(BenchmarkMode)
        assert len(modes) == 2
        assert BenchmarkMode.LLM in modes
        assert BenchmarkMode.HYBRID in modes


# =============================================================================
# Tests for load_config_file
# =============================================================================
class TestLoadConfigFile:
    """Tests for load_config_file function."""

    def test_load_json_config(self) -> None:
        """Test loading JSON configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_data = {
                "control_plane_url": "http://localhost:8889",
                "num_requests": 100,
                "request_rate": 10.0,
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            loaded = load_config_file(config_path)

            assert loaded["control_plane_url"] == "http://localhost:8889"
            assert loaded["num_requests"] == 100
            assert loaded["request_rate"] == 10.0

    def test_load_yaml_config(self) -> None:
        """Test loading YAML configuration."""
        pytest.importorskip("yaml")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            yaml_content = """
control_plane_url: http://localhost:8889
num_requests: 100
request_rate: 10.0
policies:
  - fifo
  - priority
"""
            with open(config_path, "w") as f:
                f.write(yaml_content)

            loaded = load_config_file(config_path)

            assert loaded["control_plane_url"] == "http://localhost:8889"
            assert loaded["num_requests"] == 100
            assert loaded["policies"] == ["fifo", "priority"]

    def test_load_yml_extension(self) -> None:
        """Test loading YAML with .yml extension."""
        pytest.importorskip("yaml")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            yaml_content = "test_key: test_value\n"
            with open(config_path, "w") as f:
                f.write(yaml_content)

            loaded = load_config_file(config_path)
            assert loaded["test_key"] == "test_value"

    def test_file_not_found(self) -> None:
        """Test error when file not found."""
        with pytest.raises(ValueError, match="Config file not found"):
            load_config_file(Path("/nonexistent/config.json"))

    def test_unsupported_format(self) -> None:
        """Test error for unsupported file format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.txt"
            config_path.touch()

            with pytest.raises(ValueError, match="Unsupported config file format"):
                load_config_file(config_path)


# =============================================================================
# Tests for CLI App Creation
# =============================================================================
class TestCLIAppCreation:
    """Tests for CLI app creation."""

    def test_create_app_with_typer(self) -> None:
        """Test app creation when typer is available."""
        pytest.importorskip("typer")

        from sage.benchmark.benchmark_control_plane.cli import create_app

        app = create_app()
        assert app is not None

    def test_typer_availability_flag(self) -> None:
        """Test TYPER_AVAILABLE flag."""
        import importlib.util

        from sage.benchmark.benchmark_control_plane import cli

        # If typer is available, the flag should be True
        typer_available = importlib.util.find_spec("typer") is not None
        if typer_available:
            assert cli.TYPER_AVAILABLE is True
        else:
            assert cli.TYPER_AVAILABLE is False


# =============================================================================
# Tests for CLI Helper Functions
# =============================================================================
class TestCLIHelperFunctions:
    """Tests for CLI internal helper functions."""

    def test_rate_sweep_results_structure(self) -> None:
        """Test rate sweep results structure for saving."""
        # Simulate rate sweep results structure
        results = {
            10.0: MagicMock(
                to_dict=lambda: {
                    "rate": 10.0,
                    "metrics": {"throughput": 9.5},
                }
            ),
            50.0: MagicMock(
                to_dict=lambda: {
                    "rate": 50.0,
                    "metrics": {"throughput": 45.0},
                }
            ),
        }

        # Verify structure matches expected format
        sweep_results = {str(rate): result.to_dict() for rate, result in results.items()}

        assert "10.0" in sweep_results
        assert "50.0" in sweep_results
        assert sweep_results["10.0"]["rate"] == 10.0
        assert sweep_results["50.0"]["metrics"]["throughput"] == 45.0


# =============================================================================
# Tests for Config Command Integration
# =============================================================================
class TestConfigCommandIntegration:
    """Tests for config command integration."""

    def test_llm_config_to_dict(self) -> None:
        """Test LLM config conversion to dict."""
        from sage.benchmark.benchmark_control_plane.llm_scheduler import LLMBenchmarkConfig

        cfg = LLMBenchmarkConfig(
            num_requests=100,
            request_rate=10.0,
        )
        config_dict = cfg.to_dict()

        assert "num_requests" in config_dict
        assert "request_rate" in config_dict

    def test_hybrid_config_to_dict(self) -> None:
        """Test Hybrid config conversion to dict."""
        from sage.benchmark.benchmark_control_plane.hybrid_scheduler import (
            HybridBenchmarkConfig,
        )

        cfg = HybridBenchmarkConfig(
            num_requests=100,
            request_rate=10.0,
            llm_ratio=0.7,
        )
        config_dict = cfg.to_dict()

        assert "num_requests" in config_dict
        assert "llm_ratio" in config_dict


# =============================================================================
# Tests for Validate Command Integration
# =============================================================================
class TestValidateCommandIntegration:
    """Tests for validate command integration."""

    def test_validate_llm_config(self) -> None:
        """Test validating LLM configuration."""
        from sage.benchmark.benchmark_control_plane.llm_scheduler import LLMBenchmarkConfig

        config_data = {
            "control_plane_url": "http://localhost:8889",
            "num_requests": 100,
            "request_rate": 10.0,
        }

        cfg = LLMBenchmarkConfig.from_dict(config_data)
        errors = cfg.validate()

        # Should be valid
        assert errors is None or len(errors) == 0

    def test_validate_hybrid_config(self) -> None:
        """Test validating Hybrid configuration."""
        from sage.benchmark.benchmark_control_plane.hybrid_scheduler import (
            HybridBenchmarkConfig,
        )

        config_data = {
            "control_plane_url": "http://localhost:8889",
            "num_requests": 100,
            "request_rate": 10.0,
            "llm_ratio": 0.7,
            "embedding_ratio": 0.3,  # Must sum to 1.0 with llm_ratio
            "policies": ["hybrid"],  # Use hybrid policy for hybrid config
        }

        cfg = HybridBenchmarkConfig.from_dict(config_data)
        errors = cfg.validate()

        # Should be valid
        assert errors is None or len(errors) == 0

    def test_validate_invalid_config(self) -> None:
        """Test validating invalid configuration."""
        from sage.benchmark.benchmark_control_plane.llm_scheduler import LLMBenchmarkConfig

        config_data = {
            "num_requests": -100,  # Invalid: negative
            "request_rate": 0.0,  # Invalid: zero
        }

        cfg = LLMBenchmarkConfig.from_dict(config_data)
        errors = cfg.validate()

        # Should have validation errors
        assert errors is not None
        assert len(errors) > 0


# =============================================================================
# Tests for Experiment Command Integration
# =============================================================================
class TestExperimentCommandIntegration:
    """Tests for experiment command integration."""

    def test_experiment_classes_available(self) -> None:
        """Test that experiment classes are importable."""
        from sage.benchmark.benchmark_control_plane.experiments import (
            LatencyExperiment,
            MixedRatioExperiment,
            SLOComplianceExperiment,
            ThroughputExperiment,
        )

        # Verify classes exist
        assert ThroughputExperiment is not None
        assert LatencyExperiment is not None
        assert SLOComplianceExperiment is not None
        assert MixedRatioExperiment is not None

    def test_scheduling_policy_enum(self) -> None:
        """Test SchedulingPolicy enum for experiment command."""
        from sage.benchmark.benchmark_control_plane.common.base_config import (
            SchedulingPolicy,
        )

        # Test common policies
        assert SchedulingPolicy("fifo") == SchedulingPolicy.FIFO
        assert SchedulingPolicy("priority") == SchedulingPolicy.PRIORITY
        assert SchedulingPolicy("slo_aware") == SchedulingPolicy.SLO_AWARE


# =============================================================================
# Tests for Visualize Command Integration
# =============================================================================
class TestVisualizeCommandIntegration:
    """Tests for visualize command integration."""

    def test_visualization_classes_available(self) -> None:
        """Test that visualization classes are importable."""
        from sage.benchmark.benchmark_control_plane.visualization import (
            BenchmarkCharts,
            ReportGenerator,
        )

        assert BenchmarkCharts is not None
        assert ReportGenerator is not None

    def test_load_results_json(self) -> None:
        """Test loading results from JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_path = Path(tmpdir) / "results.json"
            results_data = {
                "benchmark_type": "llm",
                "policy_results": {
                    "fifo": {
                        "metrics": {"throughput_rps": 95.0},
                    },
                },
            }
            with open(results_path, "w") as f:
                json.dump(results_data, f)

            # Load and verify
            with open(results_path) as f:
                loaded = json.load(f)

            assert loaded["benchmark_type"] == "llm"
            assert "fifo" in loaded["policy_results"]


# =============================================================================
# Tests for YAML Availability
# =============================================================================
class TestYAMLAvailability:
    """Tests for YAML support detection."""

    def test_yaml_available_flag(self) -> None:
        """Test YAML_AVAILABLE flag."""
        from sage.benchmark.benchmark_control_plane import cli

        # Test actual state
        try:
            import yaml  # noqa: F401

            assert cli.YAML_AVAILABLE is True
        except ImportError:
            assert cli.YAML_AVAILABLE is False


# =============================================================================
# Tests for Main Entry Point
# =============================================================================
class TestMainEntryPoint:
    """Tests for main entry point."""

    def test_main_function_exists(self) -> None:
        """Test main function exists."""
        from sage.benchmark.benchmark_control_plane.cli import main

        assert callable(main)

    def test_app_creation_safety(self) -> None:
        """Test app is created safely."""
        from sage.benchmark.benchmark_control_plane import cli

        # app might be None if typer is not available
        if cli.TYPER_AVAILABLE:
            assert cli.app is not None
        else:
            assert cli.app is None
