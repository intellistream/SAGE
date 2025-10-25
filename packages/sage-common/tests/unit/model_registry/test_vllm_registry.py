import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from sage.common.model_registry import vllm_registry


def _fake_snapshot_download(*, repo_id: str, local_dir: str, **_: Any) -> str:
    target = Path(local_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "config.json").write_text("{}", encoding="utf-8")
    return str(target)


@pytest.fixture(autouse=True)
def _force_tmp_root(tmp_path, monkeypatch):
    monkeypatch.setattr(vllm_registry, "_DEFAULT_ROOT", tmp_path)


def test_download_and_manifest_roundtrip(tmp_path):
    with patch.object(vllm_registry, "snapshot_download", side_effect=_fake_snapshot_download):
        info = vllm_registry.download_model("intellistream/test-model", revision="main")

    assert info.model_id == "intellistream/test-model"
    assert info.revision == "main"
    assert info.path.exists()

    listed = vllm_registry.list_models()
    assert len(listed) == 1
    assert listed[0].model_id == "intellistream/test-model"

    resolved = vllm_registry.get_model_path("intellistream/test-model")
    assert resolved == info.path

    vllm_registry.touch_model("intellistream/test-model")
    after_touch = vllm_registry.list_models()[0]
    assert after_touch.last_used >= info.last_used


def test_ensure_model_available_auto_download(tmp_path):
    with patch.object(vllm_registry, "snapshot_download", side_effect=_fake_snapshot_download):
        path = vllm_registry.ensure_model_available(
            "intellistream/new-model",
            auto_download=True,
        )
    assert Path(path).exists()


def test_delete_model_removes_manifest(tmp_path):
    with patch.object(vllm_registry, "snapshot_download", side_effect=_fake_snapshot_download):
        vllm_registry.download_model("intellistream/delete-me")

    assert vllm_registry.list_models()

    vllm_registry.delete_model("intellistream/delete-me")
    assert not vllm_registry.list_models()
    manifest_path = tmp_path / "metadata.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "intellistream/delete-me" not in manifest
