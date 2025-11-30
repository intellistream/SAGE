"""Test cases for ``sage worker`` command group."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from sage.cli.main import app as sage_app

from .helpers import CLITestCase, FakeConfigManager


def _setup_manager() -> FakeConfigManager:
    manager = FakeConfigManager()
    temp_dir = Path(tempfile.mkdtemp(prefix="sage_worker_cli_"))
    log_dir = temp_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    manager._config["worker"]["log_dir"] = str(log_dir)
    manager._config["worker"]["temp_dir"] = str(temp_dir / "tmp")
    manager._config["remote"]["ray_command"] = "ray"
    manager._config["remote"]["conda_env"] = "sage"
    manager._config.setdefault("ssh", {})["user"] = "sage"
    manager._config["ssh"]["key_path"] = str(temp_dir / "id_rsa")
    manager._config["ssh"]["connect_timeout"] = 5
    manager._config["workers_ssh_hosts"] = [("host1", 22)]
    return manager


def _patch(target: str, **kwargs):
    return lambda: patch(target, **kwargs)


def _patch_config_manager() -> list:
    manager = _setup_manager()
    return [
        _patch(
            "sage.tools.cli.commands.worker.get_config_manager",
            return_value=manager,
        ),
        _patch(
            "sage.cli.commands.platform.worker.get_config_manager",
            return_value=manager,
        ),
    ]


def _patch_subprocess():
    return _patch("sage.cli.commands.platform.worker.subprocess.run")


def _patch_execute_remote(success: bool = True):
    return _patch(
        "sage.cli.commands.platform.worker.execute_remote_command",
        return_value=success,
    )


def _patch_time_sleep():
    return _patch("sage.cli.commands.platform.worker.time.sleep", return_value=None)


def collect_cases() -> list[CLITestCase]:
    patches = _patch_config_manager()

    return [
        CLITestCase(
            "sage worker list",
            ["worker", "list"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage worker version",
            ["worker", "version"],
            app=sage_app,
        ),
        CLITestCase(
            "sage worker start",
            ["worker", "start"],
            app=sage_app,
            patch_factories=patches
            + [
                _patch_execute_remote(),
                _patch_time_sleep(),
            ],
        ),
        CLITestCase(
            "sage worker stop",
            ["worker", "stop"],
            app=sage_app,
            patch_factories=patches + [_patch_execute_remote()],
        ),
        CLITestCase(
            "sage worker stop force",
            ["worker", "stop", "--force"],
            app=sage_app,
            patch_factories=patches + [_patch_execute_remote()],
        ),
        CLITestCase(
            "sage worker status",
            ["worker", "status"],
            app=sage_app,
            patch_factories=patches + [_patch_subprocess()],
        ),
        CLITestCase(
            "sage worker add",
            ["worker", "add", "host1:22"],
            app=sage_app,
            patch_factories=patches
            + [
                _patch(
                    "sage.cli.commands.platform.worker.add_worker",
                    return_value=None,
                )
            ],
        ),
        CLITestCase(
            "sage worker remove",
            ["worker", "remove", "host1:22"],
            app=sage_app,
            patch_factories=patches
            + [
                _patch(
                    "sage.cli.commands.platform.worker.remove_worker",
                    return_value=None,
                )
            ],
        ),
        CLITestCase(
            "sage worker config",
            ["worker", "config"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage worker deploy",
            ["worker", "deploy"],
            app=sage_app,
            patch_factories=[
                _patch(
                    "sage.cli.commands.platform.worker.DeploymentManager",
                    return_value=type(
                        "DM",
                        (),
                        {"deploy_to_all_workers": lambda self: (1, 1)},
                    )(),
                )
            ],
        ),
    ]
