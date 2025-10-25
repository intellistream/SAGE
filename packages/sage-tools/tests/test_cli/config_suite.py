"""Test cases for ``sage config`` command group."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase, FakeConfigManager


def _patch_config_manager(factory: Callable[[], FakeConfigManager]):
    def _factory():
        manager = factory()
        return patch(
            "sage.tools.cli.config_manager.get_config_manager", return_value=manager
        )

    return _factory


def collect_cases() -> list[CLITestCase]:
    def make_show_manager() -> FakeConfigManager:
        manager = FakeConfigManager()
        manager.save_config(manager.load_config())
        return manager

    init_manager = FakeConfigManager()
    init_called = {"value": False}

    def custom_init():
        init_called["value"] = True
        init_manager.save_config(init_manager.load_config())

    init_manager.init_config = custom_init  # type: ignore[assignment]

    def check_init(result):
        assert init_called["value"], "Config init should have been invoked"

    return [
        CLITestCase(
            "sage config show",
            ["config", "show"],
            app=sage_app,
            patch_factories=[_patch_config_manager(make_show_manager)],
        ),
        CLITestCase(
            "sage config init --force",
            ["config", "init", "--force"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.config_manager.get_config_manager",
                    return_value=init_manager,
                )
            ],
            check=check_init,
        ),
    ]
