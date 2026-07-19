from __future__ import annotations

import json
import tarfile
from pathlib import Path

from tools.benchmark_carrier.package_semantic_merge_artifact import (
    ENDPOINT_ALLOWLIST,
    PUBLICATION_ARCHIVE_ROOT,
    _audit,
    package,
)


def test_package_sanitizes_identity_and_excludes_endpoint_logs(
    tmp_path: Path, monkeypatch
) -> None:
    comparison = tmp_path / "comparison-source"
    endpoint = tmp_path / "endpoint-source"
    comparison.mkdir()
    endpoint.mkdir()
    (comparison / "run_metadata.json").write_text(
        '{"path":"/home/reviewer/SAGE","host":"host-192-168-1-9",'
        '"commit":"0123456789abcdef0123456789abcdef01234567",'
        '"branch":"feature/semantic-mapreduce-paper",'
        '"conda_env":"esage-vllm-hust-dev",'
        '"api_key_env":"VLLM_HUST_API_KEY",'
        '"runtime":"external/vllm-hust","system":"Semantic MapReduce"}\n',
        encoding="utf-8",
    )
    for name in ENDPOINT_ALLOWLIST:
        (endpoint / name).write_text(
            "user=reviewer path=/home/reviewer/SAGE ip=192.168.1.9\n",
            encoding="utf-8",
        )
    (endpoint / "systemd-journal-tail.txt").write_text(
        "private historical log\n", encoding="utf-8"
    )

    monkeypatch.setattr(
        "tools.benchmark_carrier.package_semantic_merge_artifact._replacements",
        lambda: [
            ("/home/reviewer", "<USER_HOME>"),
            ("host-192-168-1-9", "<HOSTNAME>"),
            ("reviewer", "<USER>"),
        ],
    )
    output = tmp_path / "anonymous-package-a48f1e6"
    archive = tmp_path / "anonymous-package.tar.gz"
    curve = tmp_path / "quality_latency_token_curve.json"
    curve.write_text('{"path":"/home/reviewer/SAGE"}\n', encoding="utf-8")
    second_model = tmp_path / "second-model-source"
    (second_model / "matrix").mkdir(parents=True)
    (second_model / "matrix" / "raw.json").write_text(
        '{"model":"qwen25-14b-sage-eurosys27",'
        '"path":"/data/shared_models/Qwen--Qwen2.5-14B-Instruct"}\n',
        encoding="utf-8",
    )
    result = package(
        comparison,
        endpoint,
        output,
        archive,
        (curve,),
        (("second-model", second_model),),
    )

    assert result["status"] == "PASS"
    assert archive.is_file()
    with tarfile.open(archive, "r:gz") as stream:
        roots = {item.name.split("/", 1)[0] for item in stream.getmembers()}
    assert roots == {PUBLICATION_ARCHIVE_ROOT}
    assert not (output / "endpoint" / "systemd-journal-tail.txt").exists()
    packaged_text = (output / "comparison" / "run_metadata.json").read_text()
    assert "reviewer" not in packaged_text
    assert "192.168.1.9" not in packaged_text
    assert "0123456789abcdef0123456789abcdef01234567" not in packaged_text
    assert "feature/semantic-mapreduce-paper" not in packaged_text
    assert "vllm-hust" not in packaged_text
    assert "Semantic MapReduce" not in packaged_text
    assert "REVISION_" in packaged_text
    assert "ANONYMOUS_BRANCH" in packaged_text
    assert "project-specific-env" in packaged_text
    assert "MODEL_API_KEY" in packaged_text
    assert json.loads(packaged_text)["publication_anonymized"] is True
    assert (output / "supplementary" / curve.name).is_file()
    assert (output / "verify.py").is_file()
    environment = json.loads((output / "environment.json").read_text())
    assert environment["dependencies"] == "Python standard library only"
    assert "python verify.py comparison" in (output / "README.md").read_text()
    second_text = (
        output / "supplementary" / "second-model" / "matrix" / "raw.json"
    ).read_text()
    assert "qwen25-14b-sage-eurosys27" not in second_text
    assert "/data/shared_models" not in second_text
    manifest = json.loads((output / "ANONYMIZATION_MANIFEST.json").read_text())
    assert manifest["status"] == "PASS"
    assert manifest["git_provenance_redacted"] is True
    assert manifest["supplementary_files"] == [curve.name]
    assert manifest["supplementary_dirs"] == ["second-model"]
    assert {"verify.py", "environment.json"} <= set(manifest["files"])


def test_anonymity_audit_rejects_reverse_identity_markers(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "leak.txt").write_text(
        "commit=0123456789abcdef0123456789abcdef01234567 "
        "branch=feature/private-paper remote=https://github.com/intellistream/SAGE "
        "system=Semantic MapReduce\n",
        encoding="utf-8",
    )
    (package_dir / "SAGE-result.txt").write_text("otherwise clean\n", encoding="utf-8")

    full_revision = "0123456789abcdef0123456789abcdef01234567"
    failures = _audit(package_dir, [], [(full_revision, "REVISION_001")])

    assert any("Git revision remains" in failure for failure in failures)
    assert any("Git branch remains" in failure for failure in failures)
    assert any("public Git remote remains" in failure for failure in failures)
    assert any("repository name remains" in failure for failure in failures)
    assert any("public system name remains" in failure for failure in failures)
    assert any("packaged path" in failure for failure in failures)


def test_anonymity_audit_rejects_short_git_revision_in_path_and_content(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "run-a48f1e6.json").write_text(
        '{"revision":"a48f1e6"}\n', encoding="utf-8"
    )

    short_revision = "a48f1e6"
    failures = _audit(package_dir, [], [(short_revision, "REVISION_001")])

    assert any("Git provenance remains in packaged path" in item for item in failures)
    assert any("Git revision remains" in item for item in failures)
