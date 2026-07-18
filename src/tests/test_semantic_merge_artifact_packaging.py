from __future__ import annotations

import json
from pathlib import Path

from tools.benchmark_carrier.package_semantic_merge_artifact import (
    ENDPOINT_ALLOWLIST,
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
        '{"path":"/home/reviewer/SAGE","host":"host-192-168-1-9"}\n',
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
    output = tmp_path / "anonymous-package"
    archive = tmp_path / "anonymous-package.tar.gz"
    curve = tmp_path / "quality_latency_token_curve.json"
    curve.write_text('{"path":"/home/reviewer/SAGE"}\n', encoding="utf-8")
    result = package(comparison, endpoint, output, archive, (curve,))

    assert result["status"] == "PASS"
    assert archive.is_file()
    assert not (output / "endpoint" / "systemd-journal-tail.txt").exists()
    packaged_text = (output / "comparison" / "run_metadata.json").read_text()
    assert "reviewer" not in packaged_text
    assert "192.168.1.9" not in packaged_text
    assert (output / "supplementary" / curve.name).is_file()
    manifest = json.loads((output / "ANONYMIZATION_MANIFEST.json").read_text())
    assert manifest["status"] == "PASS"
    assert manifest["supplementary_files"] == [curve.name]
