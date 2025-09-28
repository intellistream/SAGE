"""Test cases for ``sage doctor`` command."""

from __future__ import annotations

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase


def collect_cases() -> list[CLITestCase]:
    return [
        CLITestCase("sage doctor", ["doctor"], app=sage_app),
    ]
