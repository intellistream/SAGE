"""Test cases for ``sage docs`` command group."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from .helpers import CLITestCase

DOCS_MODULE = "sage.cli.commands.platform.docs"

_DOCS_DIR = Path("/tmp/docs-public")


def _patch_common(success: bool = True):
    patches = [
        patch(f"{DOCS_MODULE}.find_docs_dir", return_value=_DOCS_DIR),
        patch(f"{DOCS_MODULE}.check_mkdocs_installed", return_value=success),
    ]
    return patches


def _patch_subprocess(success: bool = True):
    def runner(*args, **kwargs):  # pragma: no cover - simple stub
        if not success:
            raise RuntimeError("subprocess error")
        return None

    return patch(f"{DOCS_MODULE}.subprocess.run", side_effect=runner)


def collect_cases() -> list[CLITestCase]:
    return [
        CLITestCase("sage docs --help", ["docs", "--help"]),
        CLITestCase(
            "sage docs serve",
            ["docs", "serve", "--port", "9000", "--no-open"],
            patch_factories=[
                *_patch_common(),
                _patch_subprocess(),
            ],
        ),
        CLITestCase(
            "sage docs serve missing mkdocs",
            ["docs", "serve"],
            patch_factories=[*_patch_common(success=False)],
            expected_exit_code=1,
        ),
        CLITestCase(
            "sage docs build",
            ["docs", "build", "--strict", "--output", "site"],
            patch_factories=[
                *_patch_common(),
                _patch_subprocess(),
            ],
        ),
        CLITestCase(
            "sage docs install-deps",
            ["docs", "install-deps"],
            patch_factories=[_patch_subprocess()],
        ),
        CLITestCase(
            "sage docs info",
            ["docs", "info"],
            patch_factories=[*_patch_common()],
        ),
    ]
