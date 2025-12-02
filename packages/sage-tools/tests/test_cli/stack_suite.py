"""Test cases for ``sage stack`` command group."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from .helpers import CLITestCase

STACK_MODULE = "sage.cli.commands.apps.stack"

PID_DIR = Path("/tmp/sage-stack-test")


def _patch_dirs():
    return patch(f"{STACK_MODULE}.SAGE_DIR", PID_DIR)


def _patch_helpers():
    patches = [
        patch(f"{STACK_MODULE}._ensure_dirs"),
        patch(f"{STACK_MODULE}._is_port_in_use", return_value=False),
        patch(f"{STACK_MODULE}._wait_for_port", return_value=True),
        patch(f"{STACK_MODULE}._save_pid"),
        patch(f"{STACK_MODULE}.subprocess.Popen"),
        patch(f"{STACK_MODULE}.console.print"),
    ]
    return patches


def _patch_stop_service(stopped: bool = True):
    return patch(f"{STACK_MODULE}._stop_service", return_value=stopped)


def _patch_pid_checks():
    return [
        patch(f"{STACK_MODULE}._get_pid_from_file", return_value=None),
        patch(f"{STACK_MODULE}.psutil.process_iter", return_value=[]),
    ]


def collect_cases() -> list[CLITestCase]:
    start_patches = [_patch_dirs(), *_patch_helpers()]

    return [
        CLITestCase("sage stack --help", ["stack", "--help"]),
        CLITestCase(
            "sage stack start",
            ["stack", "start", "--skip-llm", "--skip-embedding"],
            patch_factories=[lambda p=p: p for p in start_patches],
        ),
        CLITestCase(
            "sage stack stop",
            ["stack", "stop"],
            patch_factories=[_patch_stop_service()],
        ),
        CLITestCase(
            "sage stack stop force",
            ["stack", "stop", "--force"],
            patch_factories=[_patch_stop_service(False), *_patch_pid_checks()],
        ),
        CLITestCase(
            "sage stack status",
            ["stack", "status"],
            patch_factories=[
                patch(f"{STACK_MODULE}.Table"),
                patch(f"{STACK_MODULE}.console.print"),
                patch(f"{STACK_MODULE}._get_pid_from_file", side_effect=[1234, None]),
                patch(f"{STACK_MODULE}.psutil.Process"),
                patch(f"{STACK_MODULE}.psutil.pid_exists", return_value=True),
            ],
        ),
        CLITestCase(
            "sage stack logs",
            ["stack", "logs"],
            patch_factories=[patch(f"{STACK_MODULE}.console.print")],
        ),
    ]
