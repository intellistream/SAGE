"""Test cases for ``sage worker`` command group."""

from __future__ import annotations

from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase, FakeConfigManager


def _patch_config_manager() -> list:
    manager = FakeConfigManager()
    return [
        lambda: patch(
            "sage.tools.cli.commands.worker.get_config_manager",
            return_value=manager,
        )
    ]


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
    ]
