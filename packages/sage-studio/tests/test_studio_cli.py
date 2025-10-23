"""Test cases for ``sage studio`` command group."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

# Import from sage-tools CLI (which still hosts the studio command integration)
from sage.tools.cli.main import app as sage_app

# Test runner
runner = CliRunner()


class FakeStudioManager:
    """Mock StudioManager for testing."""

    def __init__(self):
        self._running = False
        self._config = {"host": "127.0.0.1", "port": 7788}

    def is_running(self):
        return self._config["port"] if self._running else None

    def load_config(self):
        return dict(self._config)

    def start(self, port=None, host=None, dev=False):
        if port:
            self._config["port"] = port
        if host:
            self._config["host"] = host
        self._running = True
        return True

    def stop(self):
        was_running = self._running
        self._running = False
        return was_running

    def status(self):
        return {"running": self._running, "config": self._config}

    def logs(self, **kwargs):
        return []

    def install(self):
        return True

    def build(self):
        return True

    def open(self):
        return True

    def clean(self):
        return True


@pytest.fixture
def mock_studio_manager():
    """Fixture to provide a mocked StudioManager."""
    return FakeStudioManager()


def test_studio_start_command(mock_studio_manager):
    """Test that 'sage studio start' command works."""
    with patch("sage.tools.cli.commands.studio.studio_manager", mock_studio_manager):
        result = runner.invoke(sage_app, ["studio", "start", "--host", "127.0.0.1", "--port", "9001"])
        assert result.exit_code == 0
        assert mock_studio_manager._running is True
        assert mock_studio_manager._config["port"] == 9001
        assert mock_studio_manager._config["host"] == "127.0.0.1"


def test_studio_status_command(mock_studio_manager):
    """Test that 'sage studio status' command works."""
    with patch("sage.tools.cli.commands.studio.studio_manager", mock_studio_manager):
        result = runner.invoke(sage_app, ["studio", "status"])
        assert result.exit_code == 0


def test_studio_stop_command(mock_studio_manager):
    """Test that 'sage studio stop' command works."""
    # Start the manager first
    mock_studio_manager._running = True

    with patch("sage.tools.cli.commands.studio.studio_manager", mock_studio_manager):
        result = runner.invoke(sage_app, ["studio", "stop"])
        assert result.exit_code == 0
        assert mock_studio_manager._running is False


def test_studio_install_command(mock_studio_manager):
    """Test that 'sage studio install' command works."""
    with patch("sage.tools.cli.commands.studio.studio_manager", mock_studio_manager):
        result = runner.invoke(sage_app, ["studio", "install"])
        assert result.exit_code == 0


def test_studio_build_command(mock_studio_manager):
    """Test that 'sage studio build' command works."""
    with patch("sage.tools.cli.commands.studio.studio_manager", mock_studio_manager):
        result = runner.invoke(sage_app, ["studio", "build"])
        assert result.exit_code == 0


def test_studio_help_command():
    """Test that 'sage studio --help' command works."""
    result = runner.invoke(sage_app, ["studio", "--help"])
    assert result.exit_code == 0
    assert "Studio" in result.stdout or "studio" in result.stdout

