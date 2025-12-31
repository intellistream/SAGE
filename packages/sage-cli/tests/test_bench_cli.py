"""Tests for sage bench CLI commands.

This module tests the refactored `sage bench` CLI structure:
- Top-level bench commands
- Agent benchmark commands (paper1, paper2)
- Control Plane benchmark commands
- Quick access shortcuts
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from sage.cli.commands.apps.bench import app

runner = CliRunner()


# =========================================================================
# Top-level help tests
# =========================================================================


@pytest.mark.cli
def test_bench_help():
    """Test top-level bench help displays all subcommands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "agent" in result.output
    assert "control-plane" in result.output
    # Quick access commands
    assert "run" in result.output
    assert "eval" in result.output
    assert "train" in result.output


@pytest.mark.cli
def test_agent_help():
    """Test agent help displays paper1 and paper2."""
    result = runner.invoke(app, ["agent", "--help"])
    assert result.exit_code == 0
    assert "paper1" in result.output
    assert "paper2" in result.output
    assert "list" in result.output


@pytest.mark.cli
def test_paper1_help():
    """Test paper1 help displays all commands."""
    result = runner.invoke(app, ["agent", "paper1", "--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "eval" in result.output
    assert "train" in result.output
    assert "list" in result.output
    assert "llm" in result.output


@pytest.mark.cli
def test_paper2_help():
    """Test paper2 help displays status command."""
    result = runner.invoke(app, ["agent", "paper2", "--help"])
    assert result.exit_code == 0
    assert "status" in result.output


@pytest.mark.cli
def test_control_plane_help():
    """Test control-plane help displays all commands."""
    result = runner.invoke(app, ["control-plane", "--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "compare" in result.output
    assert "sweep" in result.output


# =========================================================================
# Agent list command tests
# =========================================================================


@pytest.mark.cli
def test_agent_list():
    """Test agent list shows available papers."""
    result = runner.invoke(app, ["agent", "list"])
    assert result.exit_code == 0
    assert "paper1" in result.output
    assert "paper2" in result.output
    # Status indicators
    assert "Ready" in result.output or "WIP" in result.output


# =========================================================================
# Paper 1 command tests
# =========================================================================


@pytest.mark.cli
def test_paper1_list_experiments():
    """Test paper1 list experiments."""
    result = runner.invoke(app, ["agent", "paper1", "list", "experiments"])
    assert result.exit_code == 0
    assert "timing" in result.output
    assert "planning" in result.output
    assert "selection" in result.output


@pytest.mark.cli
def test_paper1_list_datasets():
    """Test paper1 list datasets."""
    result = runner.invoke(app, ["agent", "paper1", "list", "datasets"])
    assert result.exit_code == 0
    assert "sage" in result.output


@pytest.mark.cli
def test_paper1_list_methods():
    """Test paper1 list methods."""
    result = runner.invoke(app, ["agent", "paper1", "list", "methods"])
    assert result.exit_code == 0
    assert "keyword" in result.output or "embedding" in result.output


@pytest.mark.cli
def test_paper1_run_help():
    """Test paper1 run help."""
    result = runner.invoke(app, ["agent", "paper1", "run", "--help"])
    assert result.exit_code == 0
    assert "--quick" in result.output
    assert "--skip-llm" in result.output


@pytest.mark.cli
def test_paper1_eval_help():
    """Test paper1 eval help."""
    result = runner.invoke(app, ["agent", "paper1", "eval", "--help"])
    assert result.exit_code == 0
    assert "--dataset" in result.output
    assert "--samples" in result.output


@pytest.mark.cli
def test_paper1_train_dry_run():
    """Test paper1 train with --dry-run."""
    result = runner.invoke(app, ["agent", "paper1", "train", "--dry-run"])
    assert result.exit_code == 0
    assert "Training" in result.output or "Dry run" in result.output


@pytest.mark.cli
def test_paper1_llm_status():
    """Test paper1 llm status."""
    result = runner.invoke(app, ["agent", "paper1", "llm", "status"])
    assert result.exit_code == 0
    assert "LLM" in result.output or "Port" in result.output


# =========================================================================
# Paper 2 tests
# =========================================================================


@pytest.mark.cli
def test_paper2_info():
    """Test paper2 displays info message."""
    result = runner.invoke(app, ["agent", "paper2"])
    assert result.exit_code == 0
    assert "SAGE-Agent" in result.output or "Coming" in result.output or "即将" in result.output


@pytest.mark.cli
def test_paper2_status():
    """Test paper2 status shows implementation status."""
    result = runner.invoke(app, ["agent", "paper2", "status"])
    assert result.exit_code == 0
    assert "状态" in result.output or "Status" in result.output


# =========================================================================
# Quick access (shortcuts) tests
# =========================================================================


@pytest.mark.cli
def test_shortcut_run_help():
    """Test sage bench run shortcut."""
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--quick" in result.output


@pytest.mark.cli
def test_shortcut_eval_help():
    """Test sage bench eval shortcut."""
    result = runner.invoke(app, ["eval", "--help"])
    assert result.exit_code == 0
    assert "--dataset" in result.output


@pytest.mark.cli
def test_shortcut_train_help():
    """Test sage bench train shortcut."""
    result = runner.invoke(app, ["train", "--help"])
    assert result.exit_code == 0
    assert "--dry-run" in result.output


@pytest.mark.cli
def test_shortcut_list_experiments():
    """Test sage bench list experiments shortcut."""
    result = runner.invoke(app, ["list", "experiments"])
    assert result.exit_code == 0
    assert "timing" in result.output


@pytest.mark.cli
def test_shortcut_figures_help():
    """Test sage bench figures shortcut."""
    result = runner.invoke(app, ["figures", "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output


@pytest.mark.cli
def test_shortcut_tables_help():
    """Test sage bench tables shortcut."""
    result = runner.invoke(app, ["tables", "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output


# =========================================================================
# Control Plane alias tests
# =========================================================================


@pytest.mark.cli
def test_cp_alias_help():
    """Test cp alias for control-plane."""
    result = runner.invoke(app, ["cp", "--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "compare" in result.output


@pytest.mark.cli
def test_cp_alias_run_help():
    """Test cp run alias."""
    result = runner.invoke(app, ["cp", "run", "--help"])
    assert result.exit_code == 0
    assert "--policy" in result.output


# =========================================================================
# Error handling tests
# =========================================================================


@pytest.mark.cli
def test_invalid_command():
    """Test invalid command shows error."""
    result = runner.invoke(app, ["invalid"])
    assert result.exit_code != 0
    assert "No such command" in result.output


@pytest.mark.cli
def test_invalid_option():
    """Test invalid option shows error."""
    result = runner.invoke(app, ["agent", "paper1", "run", "--invalid-option"])
    assert result.exit_code != 0
    assert "No such option" in result.output


@pytest.mark.cli
def test_missing_option_value():
    """Test missing option value shows error."""
    result = runner.invoke(app, ["agent", "paper1", "eval", "--dataset"])
    assert result.exit_code != 0
    assert "requires an argument" in result.output
