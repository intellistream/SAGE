"""Test cases for the ``sage llm`` command group."""

from __future__ import annotations

from types import SimpleNamespace
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


def _raise_not_implemented(*_args, **_kwargs):
    raise NotImplementedError("placeholder")


def collect_cases() -> list[CLITestCase]:
    status_patches = _patch_llm_helpers()
    fake_info = SimpleNamespace(
        model_id="demo/model",
        revision="main",
        path="/tmp/demo",
        size_bytes=1024,
        size_mb=1.0,
        last_used_iso="2024-01-01T00:00:00",
        tags=["text"],
    )

    return [
        CLITestCase(
            "sage llm status",
            ["llm", "status"],
            app=sage_app,
            patch_factories=status_patches,
        ),
        CLITestCase(
            "sage llm model show --json",
            ["llm", "model", "show", "--json"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.commands.llm.vllm_registry.list_models",
                    return_value=[fake_info],
                )
            ],
        ),
        CLITestCase(
            "sage llm model download",
            ["llm", "model", "download", "--model", "demo/model"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.commands.llm.vllm_registry.download_model",
                    return_value=fake_info,
                )
            ],
        ),
        CLITestCase(
            "sage llm model delete",
            ["llm", "model", "delete", "--model", "demo/model", "--yes"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.commands.llm.vllm_registry.delete_model",
                    return_value=None,
                )
            ],
        ),
        CLITestCase(
            "sage llm fine-tune (stub)",
            [
                "llm",
                "fine-tune",
                "--base-model",
                "demo/model",
                "--dataset",
                "data.json",
                "--output",
                "out",
            ],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.commands.llm.VLLMService",
                    return_value=SimpleNamespace(
                        fine_tune=_raise_not_implemented,
                        cleanup=lambda: None,
                    ),
                )
            ],
        ),
    ]
