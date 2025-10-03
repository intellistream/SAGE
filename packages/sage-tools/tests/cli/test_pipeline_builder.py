from pathlib import Path

import yaml
from typer.testing import CliRunner

from sage.tools.cli.main import app


runner = CliRunner()


def test_pipeline_builder_mock_non_interactive(tmp_path):
    output_path = tmp_path / "demo.yaml"

    result = runner.invoke(
        app,
        [
            "pipeline",
            "build",
            "--backend",
            "mock",
            "--name",
            "QA Helper",
            "--goal",
            "构建一个问答流程",
            "--non-interactive",
            "--output",
            str(output_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert output_path.exists()

    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert data["pipeline"]["name"] == "qa-helper"
    assert data["stages"], "stages should not be empty"
    assert any(
        stage["class"].endswith("SimplePromptor") for stage in data["stages"]
    )


def test_pipeline_builder_missing_fields_non_interactive(tmp_path):
    result = runner.invoke(
        app,
        [
            "pipeline",
            "build",
            "--backend",
            "mock",
            "--non-interactive",
            "--output",
            str(tmp_path / "config.yaml"),
        ],
    )

    assert result.exit_code != 0
    assert result.exception is not None
    assert "必须提供" in str(result.exception)
