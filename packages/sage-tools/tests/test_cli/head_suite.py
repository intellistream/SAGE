"""Test cases for ``sage head`` command group."""

from __future__ import annotations

from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase, FakeCompletedProcess, FakeConfigManager


def _patch_head_dependencies() -> list:
    manager = FakeConfigManager()

    return [
        lambda: patch(
            "sage.tools.cli.commands.head.get_config_manager",
            return_value=manager,
        ),
        lambda: patch(
            "sage.tools.cli.commands.head.subprocess.run",
            return_value=FakeCompletedProcess(stdout="ok", returncode=0),
        ),
    ]


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
    ]
