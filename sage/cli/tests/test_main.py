"""
Tests for sage.cli.main
"""
import subprocess
import sys
from typer.testing import CliRunner

from sage.cli.main import app

runner = CliRunner()

def test_version():
    """Test the version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "SAGE - Stream Analysis and Graph Engine" in result.stdout
    assert "Version:" in result.stdout

def test_config_info_no_file():
    """Test the config command when no config file exists."""
    # The config command shows default configuration even when no file exists
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "SAGE Configuration" in result.stdout
    assert "daemon:" in result.stdout

def test_main_script_execution():
    """Test running the CLI as a script."""
    result = subprocess.run(
        [sys.executable, "-m", "sage.cli.main", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Usage: python -m sage.cli.main [OPTIONS] COMMAND [ARGS]..." in result.stdout
    assert "SAGE - Stream Analysis and Graph Engine CLI" in result.stdout
