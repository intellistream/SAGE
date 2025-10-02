import json

import pytest
from sage.tools.cli.main import app
from typer.testing import CliRunner


def _has_sage_db() -> bool:
    try:
        from sage.middleware.components.sage_db.python import sage_db  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.cli
def test_chat_help():
    runner = CliRunner()
    result = runner.invoke(app, ["chat", "--help"])
    assert result.exit_code == 0
    assert "编程助手" in result.stdout


@pytest.mark.cli
@pytest.mark.skipif(not _has_sage_db(), reason="SageDB extension not available")
def test_chat_ingest_and_query(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "intro.md").write_text(
        """# 快速开始

SAGE CLI 用于管理 Streaming-Augmented Generative Execution。

## 安装

运行 `./quickstart.sh` 即可完成依赖安装。
""",
        encoding="utf-8",
    )

    index_root = tmp_path / "index"
    runner = CliRunner()

    ingest_result = runner.invoke(
        app,
        [
            "chat",
            "ingest",
            "--source",
            str(docs_dir),
            "--index-root",
            str(index_root),
            "--index",
            "test-index",
            "--chunk-size",
            "200",
            "--chunk-overlap",
            "40",
            "--embedding-method",
            "hash",
            "--fixed-dim",
            "256",
        ],
    )
    assert (
        ingest_result.exit_code == 0
    ), f"Ingest failed: {ingest_result.stdout}\n{ingest_result.stderr}"

    manifest_path = index_root / "test-index.manifest.json"
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["num_documents"] == 1
    assert payload["num_chunks"] >= 1

    chat_result = runner.invoke(
        app,
        [
            "chat",
            "--index",
            "test-index",
            "--index-root",
            str(index_root),
            "--ask",
            "如何安装 SAGE?",
            "--backend",
            "mock",
        ],
    )
    assert (
        chat_result.exit_code == 0
    ), f"Chat failed: {chat_result.stdout}\n{chat_result.stderr}"
    assert "回答" in chat_result.stdout or "索引" in chat_result.stdout
