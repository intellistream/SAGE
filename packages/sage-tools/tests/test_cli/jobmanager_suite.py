"""Test cases for ``sage jobmanager`` command group."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from sage.cli.main import app as sage_app

from .helpers import CLITestCase


def _fake_sudo_manager() -> SimpleNamespace:
    return SimpleNamespace(
        ensure_sudo_access=lambda: True,
        has_sudo_access=lambda: True,
        get_cached_password=lambda: "secret",
    )


def _patch_sudo_manager():
    return lambda: patch(
        "sage.cli.commands.platform.jobmanager.create_sudo_manager",
        return_value=_fake_sudo_manager(),
    )


def _patch_controller(method: str, *, return_value=True):
    return lambda: patch(
        f"sage.cli.commands.platform.jobmanager.JobManagerController.{method}",
        return_value=return_value,
    )


def _status_patch():
    return lambda: patch(
        "sage.cli.commands.platform.jobmanager.JobManagerController.status",
        return_value={
            "health": {"status": "success"},
            "processes": [],
            "port_occupied": False,
        },
    )


def collect_cases() -> list[CLITestCase]:
    base_patches = [_patch_sudo_manager()]

    return [
        CLITestCase(
            "sage jobmanager status",
            ["jobmanager", "status"],
            app=sage_app,
            patch_factories=base_patches + [_status_patch()],
        ),
        CLITestCase(
            "sage jobmanager version",
            ["jobmanager", "version"],
            app=sage_app,
        ),
        CLITestCase(
            "sage jobmanager start",
            ["jobmanager", "start"],
            app=sage_app,
            patch_factories=base_patches + [_patch_controller("start")],
        ),
        CLITestCase(
            "sage jobmanager start foreground force",
            [
                "jobmanager",
                "start",
                "--foreground",
                "--force",
                "--no-wait",
                "--host",
                "0.0.0.0",
                "--port",
                "19005",
            ],
            app=sage_app,
            patch_factories=base_patches + [_patch_controller("start")],
        ),
        CLITestCase(
            "sage jobmanager stop",
            ["jobmanager", "stop"],
            app=sage_app,
            patch_factories=base_patches + [_patch_controller("stop_gracefully")],
        ),
        CLITestCase(
            "sage jobmanager stop force",
            ["jobmanager", "stop", "--force"],
            app=sage_app,
            patch_factories=base_patches + [_patch_controller("force_kill")],
        ),
        CLITestCase(
            "sage jobmanager restart",
            ["jobmanager", "restart"],
            app=sage_app,
            patch_factories=base_patches + [_patch_controller("restart")],
        ),
        CLITestCase(
            "sage jobmanager restart force",
            ["jobmanager", "restart", "--force", "--no-wait"],
            app=sage_app,
            patch_factories=base_patches + [_patch_controller("restart")],
        ),
        CLITestCase(
            "sage jobmanager kill",
            ["jobmanager", "kill"],
            app=sage_app,
            patch_factories=base_patches + [_patch_controller("force_kill")],
        ),
    ]
