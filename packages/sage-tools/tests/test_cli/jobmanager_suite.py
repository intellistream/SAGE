"""Test cases for ``sage jobmanager`` command group."""

from __future__ import annotations

from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase


def collect_cases() -> list[CLITestCase]:
    status_patch = lambda: patch(
        "sage.tools.cli.commands.jobmanager.JobManagerController.status",
        return_value={
            "health": {"status": "success"},
            "processes": [],
            "port_occupied": False,
        },
    )

    return [
        CLITestCase(
            "sage jobmanager status",
            ["jobmanager", "status"],
            app=sage_app,
            patch_factories=[status_patch],
        ),
        CLITestCase(
            "sage jobmanager version",
            ["jobmanager", "version"],
            app=sage_app,
        ),
    ]
