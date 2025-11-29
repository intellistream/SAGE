"""Test cases for ``sage head`` command group."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from sage.cli.main import app as sage_app

from .helpers import CLITestCase, FakeCompletedProcess, FakeConfigManager


def _make_config_manager() -> FakeConfigManager:
    manager = FakeConfigManager()
    temp_dir = Path(tempfile.mkdtemp(prefix="sage_head_cli_"))
    log_dir = temp_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "head.log").write_text("log\n", encoding="utf-8")

    # Update underlying config so accessor returns these paths
    manager._config["head"]["log_dir"] = str(log_dir)
    manager._config["head"]["temp_dir"] = str(temp_dir / "tmp")
    manager._config["remote"]["ray_command"] = "ray"
    manager._config["remote"]["conda_env"] = "sage"
    return manager


def _patch(target: str, **kwargs):
    return lambda: patch(target, **kwargs)


def _patch_head_dependencies() -> list:
    manager = _make_config_manager()

    return [
        _patch(
            "sage.tools.cli.commands.head.get_config_manager",
            return_value=manager,
        ),
        _patch(
            "sage.cli.commands.platform.head.get_config_manager",
            return_value=manager,
        ),
        _patch(
            "sage.cli.commands.platform.head.subprocess.run",
            return_value=FakeCompletedProcess(stdout="ok", returncode=0),
        ),
    ]


def _patch_time_sleep():
    return _patch("sage.cli.commands.platform.head.time.sleep", return_value=None)


def _start_stop_patches() -> list:
    return _patch_head_dependencies() + [_patch_time_sleep()]


def collect_cases() -> list[CLITestCase]:
    patches = _patch_head_dependencies()

    return [
        CLITestCase(
            "sage head status",
            ["head", "status"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage head version",
            ["head", "version"],
            app=sage_app,
        ),
        CLITestCase(
            "sage head start",
            ["head", "start"],
            app=sage_app,
            patch_factories=_start_stop_patches(),
        ),
        CLITestCase(
            "sage head stop",
            ["head", "stop"],
            app=sage_app,
            patch_factories=_start_stop_patches(),
        ),
        CLITestCase(
            "sage head restart",
            ["head", "restart"],
            app=sage_app,
            patch_factories=[
                _patch("sage.cli.commands.platform.head.stop_head", return_value=None),
                _patch("sage.cli.commands.platform.head.start_head", return_value=None),
                _patch_time_sleep(),
            ],
        ),
        CLITestCase(
            "sage head logs",
            ["head", "logs", "--lines", "5"],
            app=sage_app,
            patch_factories=patches,
        ),
    ]
