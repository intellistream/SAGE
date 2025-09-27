"""Validation cases for ``sage version`` commands."""

from __future__ import annotations

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase


def collect_cases() -> list[CLITestCase]:
    return [
        CLITestCase("sage --version callback", ["--version"], app=sage_app),
        CLITestCase("sage version show", ["version", "show"], app=sage_app),
    ]
