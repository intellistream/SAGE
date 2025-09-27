"""Test cases for ``sage extensions`` commands."""

from __future__ import annotations

from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase


def collect_cases() -> list[CLITestCase]:
    return [
        CLITestCase(
            "sage extensions status",
            ["extensions", "status"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.commands.extensions.__import__",
                    side_effect=lambda name, *args, **kwargs: None,
                )
            ],
        ),
        CLITestCase(
            "sage test cpp-extensions",
            ["test", "cpp-extensions"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.commands.test_extensions.test_import",
                    return_value=True,
                )
            ],
        ),
    ]
