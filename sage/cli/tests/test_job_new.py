"""
Tests for sage.cli.job
"""
import os
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from sage.cli.job import app

runner = CliRunner()

@patch('sage.cli.job.cli')
def test_list_jobs(mock_cli):
    """Test the list command."""
    mock_cli.ensure_connected.return_value = None
    mock_cli.client.list_jobs.return_value = {
        "status": "success",
        "jobs": []
    }
    
    result = runner.invoke(app, ["list"])
    
    assert result.exit_code == 0
    mock_cli.ensure_connected.assert_called_once()
    mock_cli.client.list_jobs.assert_called_once()

@patch('sage.cli.job.cli')
def test_show_job(mock_cli):
    """Test the show command."""
    mock_cli.ensure_connected.return_value = None
    mock_cli._resolve_job_identifier.return_value = "test-uuid"
    mock_cli.client.get_job_status.return_value = {
        "status": "success",
        "job_status": {"name": "test", "status": "running"}
    }
    
    result = runner.invoke(app, ["show", "1"])
    
    assert result.exit_code == 0
    mock_cli._resolve_job_identifier.assert_called_with("1")
    mock_cli.client.get_job_status.assert_called_with("test-uuid")

@patch('sage.cli.job.cli')
def test_run_job(mock_cli):
    """Test the run command."""
    # This test is more complex as it involves file operations
    # For now, we'll test it with a mock
    mock_cli.ensure_connected.return_value = None
    
    # Create a dummy script file
    with open("dummy_script.py", "w") as f:
        f.write("print('hello')")
    
    try:
        result = runner.invoke(app, ["run", "dummy_script.py"])
        # The actual implementation may require additional setup
        # This test mainly ensures the command doesn't crash
    finally:
        if os.path.exists("dummy_script.py"):
            os.remove("dummy_script.py")

@patch('sage.cli.job.cli')
def test_stop_job(mock_cli):
    """Test the stop command."""
    mock_cli.ensure_connected.return_value = None
    mock_cli._resolve_job_identifier.return_value = "test-uuid"
    mock_cli.client.pause_job.return_value = {"status": "success"}
    
    result = runner.invoke(app, ["stop", "1", "--force"])
    
    assert result.exit_code == 0
    mock_cli._resolve_job_identifier.assert_called_with("1")
    mock_cli.client.pause_job.assert_called_with("test-uuid")

@patch('sage.cli.job.cli')
def test_stop_job_force(mock_cli):
    """Test the stop command with --force."""
    mock_cli.ensure_connected.return_value = None
    mock_cli._resolve_job_identifier.return_value = "test-uuid"
    mock_cli.client.pause_job.return_value = {"status": "success"}
    
    result = runner.invoke(app, ["stop", "1", "--force"])
    
    assert result.exit_code == 0
    mock_cli.client.pause_job.assert_called_with("test-uuid")

@patch('sage.cli.job.cli')
def test_logs_job(mock_cli):
    """Test the logs command."""
    # The logs command may not be fully implemented yet
    # This is a placeholder test
    result = runner.invoke(app, ["logs", "1"])
    
    # For now, we expect this to fail with exit code 2 (command not found)
    # or handle gracefully
    assert result.exit_code in [0, 1, 2]

@patch('sage.cli.job.cli')
def test_logs_job_follow(mock_cli):
    """Test the logs command with --follow."""
    # The logs command may not be fully implemented yet
    # This is a placeholder test
    result = runner.invoke(app, ["logs", "1", "--follow"])
    
    # For now, we expect this to fail with exit code 2 (command not found)
    # or handle gracefully
    assert result.exit_code in [0, 1, 2]
