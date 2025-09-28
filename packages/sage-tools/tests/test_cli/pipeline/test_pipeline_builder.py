"""Tests for the SAGE pipeline builder CLI command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sage.tools.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture()
def temp_output(tmp_path: Path) -> Path:
    return tmp_path


def test_list_templates_shows_builtin_templates():
    result = runner.invoke(app, ["pipeline", "list-templates"])
    assert result.exit_code == 0
    assert "内置模板列表" in result.stdout
    assert "rag-qa" in result.stdout


def test_show_template_returns_json():
    result = runner.invoke(app, ["pipeline", "show-template", "rag-qa"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["key"] == "rag-qa"
    assert "config" in data


def test_non_interactive_build_generates_files(temp_output: Path):
    result = runner.invoke(
        app,
        [
            "pipeline",
            "build",
            "--template",
            "rag-qa",
            "--non-interactive",
            "--output-dir",
            str(temp_output),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "Pipeline 构建完成" in result.stdout

    generated_dirs = list(temp_output.iterdir())
    assert generated_dirs, "Expected generated pipeline directory"

    generated_dir = generated_dirs[0]
    assert (generated_dir / "pipeline_config.yaml").exists()
    assert (generated_dir / "pipeline_runner.py").exists()
    assert (generated_dir / "README.md").exists()


def test_dump_only_returns_json():
    result = runner.invoke(
        app,
        [
            "pipeline",
            "build",
            "--template",
            "rag-qa",
            "--non-interactive",
            "--dump",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "config" in data
    assert "code" in data
