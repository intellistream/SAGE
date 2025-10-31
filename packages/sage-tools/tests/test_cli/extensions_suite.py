"""Test cases for ``sage extensions`` commands."""

from __future__ import annotations

import builtins
from types import SimpleNamespace
from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase


def _patch_extensions_import():
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        extensions = {
            "sage.middleware.components.sage_db.python._sage_db",
            "sage.middleware.components.sage_flow.python._sage_flow",
        }
        if name in extensions:
            return SimpleNamespace()
        return real_import(name, *args, **kwargs)

    return patch("builtins.__import__", side_effect=fake_import)


def collect_cases() -> list[CLITestCase]:
    return [
        CLITestCase(
            "sage extensions status",
            ["extensions", "status"],
            app=sage_app,
            patch_factories=[_patch_extensions_import],
        ),
        CLITestCase(
            "sage test cpp-extensions",
            ["test", "cpp-extensions"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.tools.cli.commands.extensions.check_extension_import",
                    return_value=True,
                )
            ],
        ),
    ]
