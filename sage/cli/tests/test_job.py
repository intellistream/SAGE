"""
Tests for sage.cli.job
"""
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from sage.cli.job import app

runner = CliRunner()

@patch('sage.cli.job.JobManagerCLI')
def test_list_jobs(MockJobManagerCLI):
    """Test the list command."""
    mock_instance = MockJobManagerCLI.return_value
    mock_instance.list_jobs.return_value = True
    
    result = runner.invoke(app, ["list"])
    
    assert result.exit_code == 0
    mock_instance.list_jobs.assert_called_once()

@patch('sage.cli.job.JobManagerCLI')
def test_show_job(MockJobManagerCLI):
    """Test the show command."""
    mock_instance = MockJobManagerCLI.return_value
    mock_instance.show_job.return_value = True
    
    result = runner.invoke(app, ["show", "1"])
    
    assert result.exit_code == 0
    mock_instance.show_job.assert_called_with("1")

@patch('sage.cli.job.JobManagerCLI')
def test_run_job(MockJobManagerCLI):
    """Test the run command."""
    mock_instance = MockJobManagerCLI.return_value
    mock_instance.run_job.return_value = True
    
    # Create a dummy script file
    with open("dummy_script.py", "w") as f:
        f.write("print('hello')")
        
    result = runner.invoke(app, ["run", "dummy_script.py"])
    
    assert result.exit_code == 0
    mock_instance.run_job.assert_called_once()

@patch('sage.cli.job.JobManagerCLI')
def test_stop_job(MockJobManagerCLI):
    """Test the stop command."""
    mock_instance = MockJobManagerCLI.return_value
    mock_instance.stop_job.return_value = True
    
    result = runner.invoke(app, ["stop", "1"])
    
    assert result.exit_code == 0
    mock_instance.stop_job.assert_called_with("1", False)

@patch('sage.cli.job.JobManagerCLI')
def test_stop_job_force(MockJobManagerCLI):
    """Test the stop command with --force."""
    mock_instance = MockJobManagerCLI.return_value
    mock_instance.stop_job.return_value = True
    
    result = runner.invoke(app, ["stop", "1", "--force"])
    
    assert result.exit_code == 0
    mock_instance.stop_job.assert_called_with("1", True)

@patch('sage.cli.job.JobManagerCLI')
def test_logs_job(MockJobManagerCLI):
    """Test the logs command."""
    mock_instance = MockJobManagerCLI.return_value
    mock_instance.get_logs.return_value = True
    
    result = runner.invoke(app, ["logs", "1"])
    
    assert result.exit_code == 0
    mock_instance.get_logs.assert_called_with("1", 100, False)

@patch('sage.cli.job.JobManagerCLI')
def test_logs_job_follow(MockJobManagerCLI):
    """Test the logs command with --follow."""
    mock_instance = MockJobManagerCLI.return_value
    mock_instance.get_logs.return_value = True
    
    result = runner.invoke(app, ["logs", "1", "--follow"])
    
    assert result.exit_code == 0
    mock_instance.get_logs.assert_called_with("1", 100, True)
