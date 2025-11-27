# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Unit tests for the inference CLI command.

This module tests the inference command which manages the unified
inference service (LLM + Embedding).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from sage.cli.commands.apps.inference import (
    _get_running_pid,
    _is_port_in_use,
    _load_config,
    _save_config,
    _save_pid,
    _test_api_health,
    app,
    CONFIG_FILE,
    LOG_FILE,
    PID_FILE,
)

runner = CliRunner()


# =============================================================================
# Test Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_is_port_in_use_free_port(self) -> None:
        """Test that a free port returns False."""
        # Use a high port that's unlikely to be in use
        result = _is_port_in_use(59999)
        assert result is False

    @patch("socket.socket")
    def test_is_port_in_use_occupied_port(self, mock_socket: MagicMock) -> None:
        """Test that an occupied port returns True."""
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Connected successfully
        mock_socket.return_value.__enter__.return_value = mock_sock

        result = _is_port_in_use(8000)
        assert result is True

    def test_save_and_load_config(self, tmp_path: Path) -> None:
        """Test saving and loading configuration."""
        test_config = {
            "host": "127.0.0.1",
            "port": 9000,
            "llm_model": "test-model",
        }

        # Use temporary path
        config_file = tmp_path / "test_config.json"
        with patch("sage.cli.commands.apps.inference.CONFIG_FILE", config_file):
            _save_config(test_config)
            loaded = _load_config()

        assert loaded == test_config

    def test_load_config_missing_file(self, tmp_path: Path) -> None:
        """Test loading config when file doesn't exist."""
        config_file = tmp_path / "nonexistent.json"
        with patch("sage.cli.commands.apps.inference.CONFIG_FILE", config_file):
            result = _load_config()
        assert result is None

    def test_save_and_get_pid(self, tmp_path: Path) -> None:
        """Test saving and retrieving PID."""
        pid_file = tmp_path / "test.pid"
        with patch("sage.cli.commands.apps.inference.PID_FILE", pid_file):
            _save_pid(12345)
            # Since we're not running a real process, _get_running_pid will clean up
            # Just verify the file was created
            assert pid_file.exists()
            assert pid_file.read_text().strip() == "12345"

    @patch("urllib.request.urlopen")
    def test_test_api_health_success(self, mock_urlopen: MagicMock) -> None:
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "healthy"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = _test_api_health(8000)
        assert result == {"status": "healthy"}

    @patch("urllib.request.urlopen")
    def test_test_api_health_failure(self, mock_urlopen: MagicMock) -> None:
        """Test health check when server is down."""
        mock_urlopen.side_effect = Exception("Connection refused")

        result = _test_api_health(8000)
        assert result is None


# =============================================================================
# Test CLI Commands
# =============================================================================


class TestStartCommand:
    """Tests for the start command."""

    def test_start_help(self) -> None:
        """Test start command help."""
        result = runner.invoke(app, ["start", "--help"])
        assert result.exit_code == 0
        assert "启动统一推理服务" in result.stdout
        assert "--llm-model" in result.stdout
        assert "--embedding-model" in result.stdout
        assert "--port" in result.stdout
        assert "--scheduling-policy" in result.stdout

    @patch("sage.cli.commands.apps.inference._get_running_pid")
    def test_start_already_running(self, mock_get_pid: MagicMock) -> None:
        """Test start when server is already running."""
        mock_get_pid.return_value = 12345

        result = runner.invoke(app, ["start"])
        assert result.exit_code == 1
        assert "服务已在运行中" in result.stdout

    @patch("sage.cli.commands.apps.inference._get_running_pid")
    @patch("sage.cli.commands.apps.inference._is_port_in_use")
    def test_start_port_in_use(
        self, mock_port_check: MagicMock, mock_get_pid: MagicMock
    ) -> None:
        """Test start when port is already in use."""
        mock_get_pid.return_value = None
        mock_port_check.return_value = True

        result = runner.invoke(app, ["start", "--port", "8000"])
        assert result.exit_code == 1
        assert "端口 8000 已被占用" in result.stdout


class TestStopCommand:
    """Tests for the stop command."""

    def test_stop_help(self) -> None:
        """Test stop command help."""
        result = runner.invoke(app, ["stop", "--help"])
        assert result.exit_code == 0
        assert "停止统一推理服务" in result.stdout
        assert "--force" in result.stdout

    @patch("sage.cli.commands.apps.inference._get_running_pid")
    def test_stop_not_running(self, mock_get_pid: MagicMock) -> None:
        """Test stop when server is not running."""
        mock_get_pid.return_value = None

        result = runner.invoke(app, ["stop"])
        assert result.exit_code == 0
        assert "未找到运行中的服务" in result.stdout


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_help(self) -> None:
        """Test status command help."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "查看统一推理服务状态" in result.stdout
        assert "--json" in result.stdout

    @patch("sage.cli.commands.apps.inference._get_running_pid")
    @patch("sage.cli.commands.apps.inference._load_config")
    @patch("sage.cli.commands.apps.inference._is_port_in_use")
    def test_status_not_running(
        self,
        mock_port_check: MagicMock,
        mock_load_config: MagicMock,
        mock_get_pid: MagicMock,
    ) -> None:
        """Test status when server is not running."""
        mock_get_pid.return_value = None
        mock_load_config.return_value = None
        mock_port_check.return_value = False

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "未运行" in result.stdout

    @patch("sage.cli.commands.apps.inference._get_running_pid")
    @patch("sage.cli.commands.apps.inference._load_config")
    @patch("sage.cli.commands.apps.inference._is_port_in_use")
    @patch("sage.cli.commands.apps.inference._test_api_health")
    def test_status_json_output(
        self,
        mock_health: MagicMock,
        mock_port_check: MagicMock,
        mock_load_config: MagicMock,
        mock_get_pid: MagicMock,
    ) -> None:
        """Test status with JSON output."""
        mock_get_pid.return_value = None
        mock_load_config.return_value = {"port": 8000}
        mock_port_check.return_value = False
        mock_health.return_value = None

        result = runner.invoke(app, ["status", "--json"])
        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert "running" in data
        assert "port" in data


class TestConfigCommand:
    """Tests for the config command."""

    def test_config_help(self) -> None:
        """Test config command help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "显示当前配置" in result.stdout

    @patch("sage.cli.commands.apps.inference._load_config")
    def test_config_no_config(self, mock_load_config: MagicMock) -> None:
        """Test config when no config exists."""
        mock_load_config.return_value = None

        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "暂无保存的配置" in result.stdout

    @patch("sage.cli.commands.apps.inference._load_config")
    def test_config_json_output(self, mock_load_config: MagicMock) -> None:
        """Test config with JSON output."""
        mock_load_config.return_value = {
            "host": "0.0.0.0",
            "port": 8000,
            "llm_model": "test-model",
        }

        result = runner.invoke(app, ["config", "--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["port"] == 8000


class TestLogsCommand:
    """Tests for the logs command."""

    def test_logs_help(self) -> None:
        """Test logs command help."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "查看服务日志" in result.stdout
        assert "--follow" in result.stdout
        assert "--lines" in result.stdout

    def test_logs_no_file(self, tmp_path: Path) -> None:
        """Test logs when log file doesn't exist."""
        log_file = tmp_path / "nonexistent.log"
        with patch("sage.cli.commands.apps.inference.LOG_FILE", log_file):
            result = runner.invoke(app, ["logs"])
        assert result.exit_code == 0
        assert "日志文件不存在" in result.stdout

    def test_logs_with_file(self, tmp_path: Path) -> None:
        """Test logs with existing log file."""
        log_file = tmp_path / "test.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\n")

        with patch("sage.cli.commands.apps.inference.LOG_FILE", log_file):
            result = runner.invoke(app, ["logs", "--lines", "2"])
        assert result.exit_code == 0
        assert "Line 2" in result.stdout
        assert "Line 3" in result.stdout


# =============================================================================
# Integration Tests
# =============================================================================


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def test_commands_registered(self) -> None:
        """Test that all commands are registered."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "start" in result.stdout
        assert "stop" in result.stdout
        assert "status" in result.stdout
        assert "config" in result.stdout
        assert "logs" in result.stdout

    def test_full_workflow_simulation(self, tmp_path: Path) -> None:
        """Test simulated full workflow."""
        pid_file = tmp_path / "test.pid"
        config_file = tmp_path / "test_config.json"

        with (
            patch("sage.cli.commands.apps.inference.PID_FILE", pid_file),
            patch("sage.cli.commands.apps.inference.CONFIG_FILE", config_file),
            patch("sage.cli.commands.apps.inference._get_running_pid", return_value=None),
            patch("sage.cli.commands.apps.inference._is_port_in_use", return_value=False),
            patch("sage.cli.commands.apps.inference._load_config", return_value=None),
        ):
            # Check initial status
            result = runner.invoke(app, ["status"])
            assert "未运行" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
