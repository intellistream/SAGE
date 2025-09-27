#!/usr/bin/env python3
"""Tests for the `sage config llm auto` command."""

from pathlib import Path

import yaml
from sage.tools.cli.commands.config import app as config_app
from sage.tools.cli.utils.llm_detection import LLMServiceInfo
from typer.testing import CliRunner

runner = CliRunner()


def _write_config(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_auto_updates_generator_remote(monkeypatch, tmp_path):
    """Ensure the command updates generator.remote with detected service info."""

    config_path = tmp_path / "config.yaml"
    _write_config(
        config_path,
        """
        generator:
          remote:
            method: "openai"
            api_key: ""
        """,
    )

    detection = LLMServiceInfo(
        name="ollama",
        base_url="http://127.0.0.1:11434/v1",
        models=["llama3", "llama2"],
        default_model="llama3",
        generator_section="remote",
        description="Ollama test instance",
    )

    monkeypatch.setattr(
        "sage.tools.cli.commands.config.detect_all_services",
        lambda prefer=None: [detection],
    )

    result = runner.invoke(
        config_app,
        [
            "llm",
            "auto",
            "--config-path",
            str(config_path),
            "--yes",
        ],
    )

    assert result.exit_code == 0, result.stdout

    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    generator = updated["generator"]["remote"]
    assert generator["base_url"] == detection.base_url
    assert generator["model_name"] == detection.default_model
    assert generator["method"] == "openai"

    backup_path = config_path.with_suffix(".yaml.bak")
    assert backup_path.exists()


def test_auto_updates_specific_section(monkeypatch, tmp_path):
    """The user can override the generator section and model name."""

    config_path = tmp_path / "pipeline.yaml"
    _write_config(config_path, "generator: {}\n")

    detection = LLMServiceInfo(
        name="ollama",
        base_url="http://127.0.0.1:11434/v1",
        models=["llama3"],
        default_model="llama3",
        generator_section="remote",
        description="Ollama test instance",
    )

    monkeypatch.setattr(
        "sage.tools.cli.commands.config.detect_all_services",
        lambda prefer=None: [detection],
    )

    result = runner.invoke(
        config_app,
        [
            "llm",
            "auto",
            "--config-path",
            str(config_path),
            "--section",
            "vllm",
            "--model-name",
            "custom-model",
            "--yes",
        ],
    )

    assert result.exit_code == 0, result.stdout

    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    generator = updated["generator"]["vllm"]
    assert generator["base_url"] == detection.base_url
    assert generator["model_name"] == "custom-model"


def test_auto_handles_missing_services(monkeypatch, tmp_path):
    """When no services are detected the command exits with error."""

    config_path = tmp_path / "config.yaml"
    _write_config(config_path, "generator: {}\n")

    monkeypatch.setattr(
        "sage.tools.cli.commands.config.detect_all_services",
        lambda prefer=None: [],
    )

    result = runner.invoke(
        config_app,
        [
            "llm",
            "auto",
            "--config-path",
            str(config_path),
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "未检测到支持的本地 LLM 服务" in result.stdout
