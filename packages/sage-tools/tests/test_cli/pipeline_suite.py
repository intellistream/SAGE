"""Test cases for ``sage pipeline`` command group."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from .helpers import CLITestCase

PIPELINE_MODULE = "sage.cli.commands.apps.pipeline"


def _patch_builder_dependencies():
    patches = [
        patch(f"{PIPELINE_MODULE}.load_domain_contexts", return_value=[]),
        patch(f"{PIPELINE_MODULE}.load_custom_contexts", return_value=[]),
        patch(f"{PIPELINE_MODULE}.get_default_knowledge_base", return_value=None),
    ]
    return patches


def _patch_plan_generation():
    mock_generator = MagicMock()
    mock_plan = {
        "pipeline": {"name": "demo", "type": "local"},
        "stages": [{"class": "A"}],
        "sink": {"class": "B"},
    }
    mock_generator.generate.side_effect = [mock_plan]
    patches = [
        patch(f"{PIPELINE_MODULE}.PipelinePlanGenerator", return_value=mock_generator),
        patch(f"{PIPELINE_MODULE}._render_plan"),
        patch(f"{PIPELINE_MODULE}._plan_to_yaml", return_value="pipeline: demo"),
        patch(f"{PIPELINE_MODULE}._preview_yaml"),
        patch(f"{PIPELINE_MODULE}._save_plan", return_value=Path("/tmp/demo.yaml")),
    ]
    return patches


def _patch_execute_plan():
    return patch(f"{PIPELINE_MODULE}.execute_pipeline_plan", return_value=None)


def _patch_pipeline_file(plan: dict | None = None):
    target = plan or {
        "pipeline": {"name": "ci", "type": "local"},
        "stages": [{"class": "X"}],
        "sink": {"class": "Y"},
    }
    return patch(f"{PIPELINE_MODULE}._load_pipeline_file", return_value=target)


def _patch_kb_search():
    fake_chunk = MagicMock()
    fake_chunk.text = "Sample chunk"
    fake_chunk.kind = "doc"
    fake_chunk.score = 0.9
    fake_chunk.vector = [0.1] * 5

    fake_kb = MagicMock()
    fake_kb.search.return_value = [fake_chunk]

    return patch(f"{PIPELINE_MODULE}.PipelineKnowledgeBase", return_value=fake_kb)


def collect_cases() -> list[CLITestCase]:
    build_patches = _patch_builder_dependencies() + _patch_plan_generation()

    return [
        CLITestCase("sage pipeline --help", ["pipeline", "--help"]),
        CLITestCase(
            "sage pipeline build non-interactive",
            [
                "pipeline",
                "build",
                "--name",
                "demo",
                "--goal",
                "demo goal",
                "--backend",
                "mock",
                "--non-interactive",
                "--no-knowledge",
            ],
            patch_factories=[lambda p=p: p for p in build_patches],
        ),
        CLITestCase(
            "sage pipeline run",
            ["pipeline", "run", "demo.yaml"],
            patch_factories=[_patch_pipeline_file(), _patch_execute_plan()],
        ),
        CLITestCase(
            "sage pipeline analyze-embedding",
            ["pipeline", "analyze-embedding", "question"],
            patch_factories=[_patch_kb_search()],
        ),
        CLITestCase(
            "sage pipeline create-embedding",
            ["pipeline", "create-embedding", "--template", "rag"],
            patch_factories=[
                patch(f"{PIPELINE_MODULE}.generate_embedding_pipeline", return_value={})
            ],
        ),
    ]
