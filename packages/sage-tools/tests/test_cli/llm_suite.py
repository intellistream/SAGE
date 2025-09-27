"""Test cases for the ``sage llm`` command group."""

from __future__ import annotations

from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase, DummyProcess


def _patch_llm_helpers() -> list:
    fake_processes = [DummyProcess(pid=4321, cmd=["vllm", "serve", "model"])]

    return [
        lambda: patch(
            "sage.tools.cli.commands.llm._is_service_running",
            return_value=True,
        ),
        lambda: patch(
            "sage.tools.cli.commands.llm._find_llm_processes",
            return_value=fake_processes,
        ),
        lambda: patch(
            "sage.tools.cli.commands.llm._test_api_endpoint",
            return_value=None,
        ),
    ]


def collect_cases() -> list[CLITestCase]:
    status_patches = _patch_llm_helpers()

    return [
        CLITestCase(
            "sage llm status",
            ["llm", "status"],
            app=sage_app,
            patch_factories=status_patches,
        ),
    ]
