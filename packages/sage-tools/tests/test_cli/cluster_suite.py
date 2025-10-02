"""Test cases for ``sage cluster`` command group."""

from __future__ import annotations

from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase, FakeConfigManager


def _patch_cluster_config() -> list:
    manager = FakeConfigManager()
    return [
        lambda: patch(
            "sage.tools.cli.commands.cluster.get_config_manager",
            return_value=manager,
        )
    ]


def collect_cases() -> list[CLITestCase]:
    patches = _patch_cluster_config()

    return [
        CLITestCase(
            "sage cluster info",
            ["cluster", "info"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage cluster version",
            ["cluster", "version"],
            app=sage_app,
        ),
    ]
