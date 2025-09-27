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


def _patch_manager() -> Callable[[], object]:
    fake_manager = FakeStudioManager()
    return lambda: patch(
        "sage.tools.cli.commands.studio.studio_manager",
        fake_manager,
    )


def collect_cases() -> list[CLITestCase]:
    patch_factory = _patch_manager()

    return [
        CLITestCase(
            "sage studio start",
            ["studio", "start", "--host", "127.0.0.1", "--port", "9001"],
            app=sage_app,
            patch_factories=[patch_factory],
        ),
        CLITestCase(
            "sage studio status",
            ["studio", "status"],
            app=sage_app,
            patch_factories=[patch_factory],
        ),
    ]
