"""
Tests for sage.cli.deploy
"""
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from sage.cli.deploy import app

runner = CliRunner()

@patch('sage.cli.deploy.subprocess.run')
def test_start(mock_subprocess):
    """Test the start command."""
    mock_subprocess.return_value = MagicMock(returncode=0)
    
    result = runner.invoke(app, ["start"])
    
    assert result.exit_code == 0
    mock_subprocess.assert_called_once()

@patch('sage.cli.deploy.subprocess.run')
def test_stop(mock_subprocess):
    """Test the stop command."""
    mock_subprocess.return_value = MagicMock(returncode=0)
    
    result = runner.invoke(app, ["stop"])
    
    assert result.exit_code == 0
    mock_subprocess.assert_called_once()

@patch('sage.cli.deploy.subprocess.run')
def test_restart(mock_subprocess):
    """Test the restart command."""
    mock_subprocess.return_value = MagicMock(returncode=0)
    
    result = runner.invoke(app, ["restart"])
    
    assert result.exit_code == 0
    mock_subprocess.assert_called_once()

@patch('sage.cli.deploy.subprocess.run')
def test_status(mock_subprocess):
    """Test the status command."""
    mock_subprocess.return_value = MagicMock(returncode=0)
    
    result = runner.invoke(app, ["status"])
    
    assert result.exit_code == 0
    mock_subprocess.assert_called_once()
    mock_instance.status.return_value = True
    
    result = runner.invoke(app, ["status"])
    
    assert result.exit_code == 0
    mock_instance.status.assert_called_once()
