"""
Tests for sage.cli.setup
"""
import sys
from unittest.mock import patch, call
import subprocess
from pathlib import Path

from sage.cli.setup import install_cli_dependencies, create_config_directory, main

@patch('subprocess.check_call')
def test_install_dependencies_success(mock_check_call):
    """Test successful installation of dependencies."""
    success = install_cli_dependencies()
    assert success is True
    
    expected_calls = [
        call([sys.executable, "-m", "pip", "install", "typer>=0.9.0"]),
        call([sys.executable, "-m", "pip", "install", "colorama>=0.4.0"]),
        call([sys.executable, "-m", "pip", "install", "tabulate>=0.9.0"]),
        call([sys.executable, "-m", "pip", "install", "pyyaml>=6.0"]),
    ]
    mock_check_call.assert_has_calls(expected_calls, any_order=True)

@patch('subprocess.check_call', side_effect=subprocess.CalledProcessError(1, 'cmd'))
def test_install_dependencies_failure(mock_check_call):
    """Test failed installation of a dependency."""
    success = install_cli_dependencies()
    assert success is False

@patch('pathlib.Path.write_text')
@patch('pathlib.Path.exists', return_value=False)
@patch('pathlib.Path.mkdir')
def test_create_config_directory_new(mock_mkdir, mock_exists, mock_write_text):
    """Test creating a new config directory and file."""
    create_config_directory()
    
    config_dir = Path.home() / ".sage"
    mock_mkdir.assert_called_once_with(exist_ok=True)
    mock_exists.assert_called_once()
    mock_write_text.assert_called_once()

@patch('pathlib.Path.write_text')
@patch('pathlib.Path.exists', return_value=True)
@patch('pathlib.Path.mkdir')
def test_create_config_directory_existing(mock_mkdir, mock_exists, mock_write_text):
    """Test when the config directory and file already exist."""
    create_config_directory()
    
    mock_mkdir.assert_called_once_with(exist_ok=True)
    mock_exists.assert_called_once()
    mock_write_text.assert_not_called()

@patch('sage.cli.setup.install_cli_dependencies', return_value=True)
@patch('sage.cli.setup.create_config_directory')
def test_main_flow(mock_create_config, mock_install_deps):
    """Test the main function of the setup script."""
    with patch('sys.exit') as mock_exit:
        main()
        mock_install_deps.assert_called_once()
        mock_create_config.assert_called_once()
        mock_exit.assert_not_called()

@patch('sage.cli.setup.install_cli_dependencies', return_value=False)
@patch('sys.exit')
def test_main_flow_install_fail(mock_exit, mock_install_deps):
    """Test the main function when dependency installation fails."""
    main()
    mock_install_deps.assert_called_once()
    mock_exit.assert_called_with(1)
