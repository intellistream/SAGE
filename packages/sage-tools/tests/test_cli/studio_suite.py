"""Test cases for ``sage studio`` command group."""

from __future__ import annotations

from types import MethodType
from unittest.mock import patch

from .helpers import CLITestCase

STUDIO_MODULE = "sage.cli.commands.apps.studio"


def _make_manager(**overrides):
    class FakeManager:
        def __init__(self):
            self.config = {"host": "127.0.0.1", "port": 5173}

        def list_finetuned_models(self):
            return []

        def is_running(self):
            return False

        def load_config(self):
            return self.config

        def start(self, **kwargs):
            return True

        def stop(self):
            return True

        def status(self):
            return None

        def logs(self, **kwargs):
            return None

        def install(self):
            return True

        def build(self):
            return True

        def clean(self):  # type: ignore[override]
            return True

        def clean_frontend_cache(self):
            return True

        def run_npm_command(self, args):
            return True

    manager = FakeManager()
    for name, value in overrides.items():
        if callable(value):
            setattr(manager, name, MethodType(value, manager))
        else:
            setattr(manager, name, value)
    return manager


def _patch_manager(**overrides):
    return patch(f"{STUDIO_MODULE}.studio_manager", _make_manager(**overrides))


def _patch_webbrowser_open():
    return patch("webbrowser.open", return_value=True)


def collect_cases() -> list[CLITestCase]:
    return [
        CLITestCase("sage studio --help", ["studio", "--help"]),
        CLITestCase(
            "sage studio start",
            ["studio", "start", "--host", "0.0.0.0", "--port", "9000", "--no-llm"],
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio start list finetuned",
            ["studio", "start", "--list-finetuned"],
            patch_factories=[
                _patch_manager(
                    list_finetuned_models=lambda self: [
                        {
                            "name": "demo",
                            "type": "llm",
                            "base_model": "qwen",
                            "path": "/tmp/model",
                            "completed_at": "2025-01-01",
                        }
                    ]
                )
            ],
        ),
        CLITestCase(
            "sage studio stop",
            ["studio", "stop"],
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio restart",
            ["studio", "restart", "--no-clean", "--no-llm"],
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio status",
            ["studio", "status"],
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio logs",
            ["studio", "logs", "--backend", "--gateway"],
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio install",
            ["studio", "install"],
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio build",
            ["studio", "build"],
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio open",
            ["studio", "open"],
            patch_factories=[
                _patch_manager(is_running=lambda self: True),
                _patch_webbrowser_open(),
            ],
        ),
        CLITestCase(
            "sage studio clean",
            ["studio", "clean"],
            patch_factories=[_patch_manager()],
        ),
        CLITestCase(
            "sage studio npm",
            ["studio", "npm", "run", "build"],
            patch_factories=[_patch_manager()],
        ),
    ]
