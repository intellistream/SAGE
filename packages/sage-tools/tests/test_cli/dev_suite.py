"""Test cases for ``sage dev`` command group."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from sage.tools.cli.main import app as sage_app

from .helpers import CLITestCase

_TEMP_DIRS: list[Path] = []


def _create_sample_project() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="sage_cli_dev_"))
    _TEMP_DIRS.append(temp_dir)

    pkg_src = temp_dir / "packages" / "demo" / "src" / "sage" / "demo"
    pkg_src.mkdir(parents=True, exist_ok=True)
    (pkg_src / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")
    version_file = pkg_src.parent / "_version.py"
    version_file.write_text(
        "__version__ = '0.1.0'\n__author__ = 'Test'\n__email__ = 'test@example.com'\n",
        encoding="utf-8",
    )

    return temp_dir


def cleanup():
    for path in _TEMP_DIRS:
        shutil.rmtree(path, ignore_errors=True)
    _TEMP_DIRS.clear()


def collect_cases() -> list[CLITestCase]:
    project_root = _create_sample_project()

    return [
        CLITestCase(
            "sage dev version list",
            ["dev", "version", "list", "--root", str(project_root)],
            app=sage_app,
        ),
    ]
