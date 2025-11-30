"""Basic help coverage for the public ``sage`` CLI entry point."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from sage.cli.main import app

runner = CliRunner()


def _available_groups() -> list[str]:
    groups: list[str] = []
    for info in getattr(app, "registered_groups", []):
        # ``name`` matches the CLI segment, e.g. ``cluster`` or ``llm``
        if info.name is not None:
            groups.append(info.name)
    return groups


@pytest.mark.cli
def test_root_help_displays_categories() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "SAGE" in result.stdout
    assert "Platform" in result.stdout
    assert "Apps" in result.stdout


@pytest.mark.cli
@pytest.mark.parametrize("group_name", _available_groups())
def test_group_help_commands(group_name: str) -> None:
    result = runner.invoke(app, [group_name, "--help"])
    assert result.exit_code == 0, result.stdout
    assert group_name in result.stdout
