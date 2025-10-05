from pathlib import Path
import sys
import zipfile

import yaml
from typer.testing import CliRunner

from sage.tools.cli.commands.pipeline_knowledge import (
    PipelineKnowledgeBase,
    build_query_payload,
)
from sage.tools.cli.commands.pipeline_domain import load_domain_contexts
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
            "--no-knowledge",
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
            "--no-knowledge",
            "--non-interactive",
            "--output",
            str(tmp_path / "config.yaml"),
        ],
    )

    assert result.exit_code != 0
    assert result.exception is not None
    assert "必须提供" in str(result.exception)


def test_load_domain_contexts_provides_examples():
    contexts = load_domain_contexts(limit=2)
    assert contexts, "context loader should yield at least one snippet"
    joined = "\n".join(contexts)
    assert "Pipeline" in joined or "SAGE" in joined


def test_pipeline_knowledge_base_retrieval(tmp_path):
    docs_dir = tmp_path / "docs-public" / "docs_src"
    docs_dir.mkdir(parents=True)
    (docs_dir / "builder.md").write_text(
        "SAGE Pipeline Builder 支持多阶段配置",
        encoding="utf-8",
    )

    examples_dir = tmp_path / "examples" / "config"
    examples_dir.mkdir(parents=True)
    (examples_dir / "demo.yaml").write_text(
        """
pipeline:
  name: demo
  description: test
stages:
  - id: retriever
    class: sage.libs.rag.retriever.SimpleRetriever
    summary: demo retriever
sink:
  class: sage.libs.io.TerminalSink
""".strip(),
        encoding="utf-8",
    )

    libs_dir = tmp_path / "packages" / "sage-libs" / "src" / "sage" / "libs"
    libs_dir.mkdir(parents=True, exist_ok=True)
    (libs_dir / "demo.py").write_text(
        '"""Simple pipeline components."""\nclass DemoStage:\n    """Demo stage for tests."""',
        encoding="utf-8",
    )

    kb = PipelineKnowledgeBase(project_root=tmp_path, max_chunks=200)
    results = kb.search("retriever component", top_k=3)
    assert results, "knowledge base should return results"
    assert any("retriever" in item.text for item in results)


def test_pipeline_knowledge_base_remote_download(tmp_path, monkeypatch):
    # Produce a fake remote docs archive
    docs_src = tmp_path / "remote" / "docs_src"
    docs_src.mkdir(parents=True)
    (docs_src / "guide.md").write_text("# 指南\nPipeline Builder 远程文档", encoding="utf-8")

    zip_path = tmp_path / "docs.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for file_path in docs_src.rglob("*"):
            arcname = file_path.relative_to(tmp_path / "remote")
            zf.write(file_path, arcname=str(arcname))

    monkeypatch.setenv("SAGE_PIPELINE_DOCS_URL", zip_path.as_uri())
    monkeypatch.setenv("SAGE_PIPELINE_DOWNLOAD_DOCS", "1")
    monkeypatch.setenv("SAGE_OUTPUT_DIR", str(tmp_path / ".sage"))

    from sage.common.config.output_paths import get_sage_paths

    get_sage_paths.cache_clear()

    kb = PipelineKnowledgeBase(project_root=Path("/nonexistent"), allow_download=True)
    results = kb.search("远程文档", top_k=2)
    assert any("远程文档" in item.text for item in results)


def test_build_query_payload_includes_feedback():
    payload = build_query_payload(
        {"goal": "test", "name": "demo"},
        previous_plan={"stages": [{"id": "retriever", "class": "Demo"}]},
        feedback="需要加速",
    )
    assert "retriever" in payload
    assert "需要加速" in payload


def test_pipeline_run_success(tmp_path, monkeypatch):
    module_dir = tmp_path / "demo_components"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("", encoding="utf-8")
    component_file = module_dir / "ops.py"
    component_file.write_text(
        """
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.sink_function import SinkFunction


class DemoBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._emitted = False

    def execute(self):
        if self._emitted:
            return None
        self._emitted = True
        return "hello"


class UpperCase(MapFunction):
    def execute(self, value):
        return str(value).upper()


class CollectSink(SinkFunction):
    collected = []

    def execute(self, value):
        self.collected.append(value)
        return value
        """,
        encoding="utf-8",
    )

    sys.path.insert(0, str(tmp_path))

    config_path = tmp_path / "pipeline.yaml"
    config_path.write_text(
        """
pipeline:
  name: demo-pipeline
  type: local
source:
  id: demo-source
  kind: batch
  class: demo_components.ops.DemoBatch
  params: {}
stages:
  - id: uppercase
    kind: map
    class: demo_components.ops.UpperCase
    params: {}
sink:
  id: collector
  kind: sink
  class: demo_components.ops.CollectSink
  params: {}
services: []
""",
        encoding="utf-8",
    )

    submitted: dict[str, object] = {}

    def fake_submit(self, autostop: bool = False):
        submitted["autostop"] = autostop
        submitted["functions"] = [
            getattr(transformation, "function_class", None)
            for transformation in self.pipeline
        ]
        return "uuid-demo"

    monkeypatch.setattr(
        "sage.core.api.local_environment.LocalEnvironment.submit",
        fake_submit,
    )
    monkeypatch.setattr(
        "sage.core.api.local_environment.LocalEnvironment._wait_for_completion",
        lambda self: None,
    )

    try:
        result = runner.invoke(
            app,
            ["pipeline", "run", str(config_path)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.stdout
        assert submitted["autostop"] is True
        function_names = [fn.__name__ for fn in submitted["functions"] if fn]
        assert "DemoBatch" in function_names
        assert "UpperCase" in function_names
        assert "CollectSink" in function_names
    finally:
        sys.path.remove(str(tmp_path))


def test_pipeline_run_missing_file():
    result = runner.invoke(
        app,
        ["pipeline", "run", "/nonexistent/pipeline.yaml"],
        catch_exceptions=False,
    )

    assert result.exit_code != 0
    assert "❌" in result.stdout
