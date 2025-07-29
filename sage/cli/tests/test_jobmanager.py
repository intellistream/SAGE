"""
Tests for sage.cli.jobmanager
"""
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

from sage.cli.jobmanager import app, JobManagerController

runner = CliRunner()

def test_jobmanager_controller_init():
    """Test JobManagerController initialization."""
    controller = JobManagerController()
    assert controller.host == "127.0.0.1"
    assert controller.port == 19001
    assert "job_manager.py" in controller.process_names
    assert "jobmanager_daemon.py" in controller.process_names
    assert "sage.jobmanager.job_manager" in controller.process_names

def test_jobmanager_controller_init_custom():
    """Test JobManagerController initialization with custom parameters."""
    controller = JobManagerController(host="192.168.1.1", port=12345)
    assert controller.host == "192.168.1.1"
    assert controller.port == 12345

@patch('sage.cli.jobmanager.JobManagerController')
def test_start(MockController):
    """Test the start command."""
    mock_instance = MockController.return_value
    mock_instance.start.return_value = True
    
    result = runner.invoke(app, ["start", "--port", "12345"])
    
    assert result.exit_code == 0
    assert "Operation 'start' completed successfully" in result.stdout
    MockController.assert_called_with(host='127.0.0.1', port=12345)
    mock_instance.start.assert_called_once()

@patch('sage.cli.jobmanager.JobManagerController')
def test_stop(MockController):
    """Test the stop command."""
    mock_instance = MockController.return_value
    mock_instance.stop_gracefully.return_value = True
    
    result = runner.invoke(app, ["stop"])
    
    assert result.exit_code == 0
    assert "Operation 'stop' completed successfully" in result.stdout
    mock_instance.stop_gracefully.assert_called_once()

@patch('sage.cli.jobmanager.JobManagerController')
def test_stop_force(MockController):
    """Test the stop command with --force."""
    mock_instance = MockController.return_value
    mock_instance.force_kill.return_value = True
    
    result = runner.invoke(app, ["stop", "--force"])
    
    assert result.exit_code == 0
    assert "Operation 'stop' completed successfully" in result.stdout
    mock_instance.force_kill.assert_called_once()

@patch('sage.cli.jobmanager.JobManagerController')
def test_restart(MockController):
    """Test the restart command."""
    mock_instance = MockController.return_value
    mock_instance.restart.return_value = True
    
    result = runner.invoke(app, ["restart"])
    
    assert result.exit_code == 0
    mock_instance.restart.assert_called_once()

@patch('sage.cli.jobmanager.JobManagerController')
def test_status(MockController):
    """Test the status command."""
    mock_instance = MockController.return_value
    
    result = runner.invoke(app, ["status"])
    
    assert result.exit_code == 0
    assert "Operation 'status' completed successfully" in result.stdout
    mock_instance.status.assert_called_once()

@patch('sage.cli.jobmanager.JobManagerController')
def test_kill(MockController):
    """Test the kill command."""
    mock_instance = MockController.return_value
    mock_instance.force_kill.return_value = True
    
    result = runner.invoke(app, ["kill"])
    
    assert result.exit_code == 0
    assert "Operation 'kill' completed successfully" in result.stdout
    mock_instance.force_kill.assert_called_once()
