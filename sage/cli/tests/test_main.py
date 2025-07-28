"""
Tests for sage.cli.main (updated for new CLI structure)
"""
import subprocess
import sys
from typer.testing import CliRunner
from unittest import mock
from unittest.mock import patch

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
    assert "Current SAGE Configuration" in result.stdout

def test_main_help():
    """Test the main help output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "SAGE - Stream Analysis and Graph Engine CLI" in result.stdout
    assert "cluster" in result.stdout
    assert "head" in result.stdout
    assert "worker" in result.stdout

def test_cluster_subcommand_help():
    """Test cluster subcommand help."""
    result = runner.invoke(app, ["cluster", "--help"])
    assert result.exit_code == 0
    assert "集群管理" in result.stdout

def test_head_subcommand_help():
    """Test head subcommand help."""
    result = runner.invoke(app, ["head", "--help"])
    assert result.exit_code == 0
    assert "Head节点管理" in result.stdout

def test_worker_subcommand_help():
    """Test worker subcommand help."""
    result = runner.invoke(app, ["worker", "--help"])
    assert result.exit_code == 0
    assert "Worker管理" in result.stdout

@mock.patch('tempfile.NamedTemporaryFile')
@mock.patch('os.path.expanduser')
@mock.patch('sage.cli.config_manager.ConfigManager.load_config')
def test_config_with_existing_config(mock_load_config, mock_expanduser, mock_tempfile):
    """Test config command with existing configuration."""
    # Mock the config
    mock_config = {
        'head': {'host': 'test-host', 'port': 6379},
        'workers_ssh_hosts': 'worker1:22,worker2:22'
    }
    mock_load_config.return_value = mock_config
    
    # Run the config command
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "Current SAGE Configuration" in result.stdout

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
