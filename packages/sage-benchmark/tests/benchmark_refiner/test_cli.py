# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Unit tests for benchmark_refiner CLI.

Tests cover:
- CLI argument parsing
- Command dispatch
- Config generation
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sage.benchmark.benchmark_refiner.cli import (
    cmd_config,
    create_parser,
    main,
)


# =============================================================================
# Tests for Argument Parser
# =============================================================================
class TestArgumentParser:
    """Tests for CLI argument parser."""

    def test_parser_creation(self) -> None:
        """Test parser creation."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "sage-refiner-bench"

    def test_compare_command(self) -> None:
        """Test compare command parsing."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "compare",
                "--algorithms",
                "baseline,longrefiner",
                "--samples",
                "50",
                "--budget",
                "1024",
            ]
        )
        assert args.command == "compare"
        assert args.algorithms == "baseline,longrefiner"
        assert args.samples == 50
        assert args.budget == 1024

    def test_compare_defaults(self) -> None:
        """Test compare command defaults."""
        parser = create_parser()
        args = parser.parse_args(["compare"])
        assert args.command == "compare"
        assert args.algorithms == "baseline,longrefiner,reform,provence"
        assert args.samples == 50
        assert args.budget == 2048

    def test_run_command(self) -> None:
        """Test run command parsing."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "run",
                "--config",
                "experiment.yaml",
                "--type",
                "quality",
            ]
        )
        assert args.command == "run"
        assert args.config == "experiment.yaml"
        assert args.type == "quality"

    def test_sweep_command(self) -> None:
        """Test sweep command parsing."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "sweep",
                "--algorithm",
                "longrefiner",
                "--budgets",
                "512,1024,2048",
                "--samples",
                "100",
            ]
        )
        assert args.command == "sweep"
        assert args.algorithm == "longrefiner"
        assert args.budgets == "512,1024,2048"
        assert args.samples == 100

    def test_config_command(self) -> None:
        """Test config command parsing."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "config",
                "--output",
                "my_config.yaml",
            ]
        )
        assert args.command == "config"
        assert args.output == "my_config.yaml"

    def test_heads_command(self) -> None:
        """Test heads command parsing."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "heads",
                "--model",
                "/path/to/model",
                "--dataset",
                "hotpotqa",
                "--samples",
                "200",
            ]
        )
        assert args.command == "heads"
        assert args.model == "/path/to/model"
        assert args.dataset == "hotpotqa"
        assert args.samples == 200


# =============================================================================
# Tests for Commands
# =============================================================================
class TestCommands:
    """Tests for CLI commands."""

    def test_cmd_config(self) -> None:
        """Test config command generates valid YAML."""
        parser = create_parser()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            args = parser.parse_args(["config", "--output", f.name])
            result = cmd_config(args)

            assert result == 0
            assert Path(f.name).exists()

            # Verify it's valid YAML
            import yaml

            with open(f.name) as yaml_file:
                config = yaml.safe_load(yaml_file)
                assert "experiment" in config
                assert "algorithms" in config["experiment"]

    def test_main_no_command(self) -> None:
        """Test main with no command shows help."""
        with patch("sys.argv", ["sage-refiner-bench"]):
            result = main()
            assert result == 0

    def test_main_help(self) -> None:
        """Test main with --help."""
        with patch("sys.argv", ["sage-refiner-bench", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
