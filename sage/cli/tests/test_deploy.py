"""
Tests for sage.cli.deploy
"""
from typer.testing import CliRunner
from unittest.mock import patch

from sage.cli.deploy import app

runner = CliRunner()

@patch('sage.cli.deploy.DeploymentController')
def test_start(MockController):
    """Test the start command."""
    mock_instance = MockController.return_value
    mock_instance.start.return_value = True
    
    result = runner.invoke(app, ["start"])
    
    assert result.exit_code == 0
    assert "SAGE system started" in result.stdout
    mock_instance.start.assert_called_once()

@patch('sage.cli.deploy.DeploymentController')
def test_stop(MockController):
    """Test the stop command."""
    mock_instance = MockController.return_value
    mock_instance.stop.return_value = True
    
    result = runner.invoke(app, ["stop"])
    
    assert result.exit_code == 0
    assert "SAGE system stopped" in result.stdout
    mock_instance.stop.assert_called_once()

@patch('sage.cli.deploy.DeploymentController')
def test_restart(MockController):
    """Test the restart command."""
    mock_instance = MockController.return_value
    mock_instance.restart.return_value = True
    
    result = runner.invoke(app, ["restart"])
    
    assert result.exit_code == 0
    assert "SAGE system restarted" in result.stdout
    mock_instance.restart.assert_called_once()

@patch('sage.cli.deploy.DeploymentController')
def test_status(MockController):
    """Test the status command."""
    mock_instance = MockController.return_value
    mock_instance.status.return_value = True
    
    result = runner.invoke(app, ["status"])
    
    assert result.exit_code == 0
    mock_instance.status.assert_called_once()
