"""Test cases for ``sage studio`` command group."""

from __future__ import annotations

from typing import Callable
from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase


class FakeStudioManager:
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


def _patch_manager(*, running: bool = False) -> Callable[[], object]:
    def _factory():
        fake_manager = FakeStudioManager()
        fake_manager._running = running
        return patch(
            "sage.tools.cli.commands.studio.studio_manager",
            fake_manager,
        )

    return _factory


def collect_cases() -> list[CLITestCase]:
    return [
        CLITestCase(
            "sage studio start",
            ["studio", "start", "--host", "127.0.0.1", "--port", "9001"],
            app=sage_app,
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio status",
            ["studio", "status"],
            app=sage_app,
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio stop",
            ["studio", "stop"],
            app=sage_app,
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio restart",
            ["studio", "restart"],
            app=sage_app,
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio logs",
            ["studio", "logs", "--follow"],
            app=sage_app,
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio install",
            ["studio", "install"],
            app=sage_app,
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio build",
            ["studio", "build"],
            app=sage_app,
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio open",
            ["studio", "open"],
            app=sage_app,
            patch_factories=[
                _patch_manager(running=True),
                lambda: patch(
                    "sage.tools.cli.commands.studio.webbrowser.open", return_value=True
                ),
            ],
        ),
        CLITestCase(
            "sage studio clean",
            ["studio", "clean"],
            app=sage_app,
            patch_factories=[_patch_manager()],
        ),
    ]
