from __future__ import annotations

import json
import zipfile
from pathlib import Path

from tools.benchmark_carrier.run_aiopsarena_reducer_grouping_replay import run


def _fixture_archive(path: Path) -> None:
    payload = {
        "timestamp": [600, 600, 1200],
        "service": ["frontend", "frontend", "cartservice"],
        "cmdb_id": ["frontend-0", "frontend-1", "cartservice-0"],
        "failure_type": ["cpu", "cpu", "loss"],
        "duration": [600, 600, 300],
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Case/groundtruth/groundtruth.json", json.dumps(payload))


def test_public_groundtruth_defines_reducer_episode_units(tmp_path: Path) -> None:
    archive = tmp_path / "case.zip"
    _fixture_archive(archive)

    result = run(archive, ["map-only", "service-local", "hybrid-hint"])

    assert result["evidence_label"] == "replay"
    assert result["validation_scope"] == "reducer-only-label-conditioned"
    assert result["end_to_end_detection_claim"] is False
    assert result["source"]["groundtruth_rows"] == 3
    assert result["source"]["incident_episode_count"] == 2
    assert all(item["source_incident_id"] is None for item in result["evidence"])
    by_reducer = {item["reducer"]: item for item in result["results"]}
    assert by_reducer["map-only"]["hypothesis_count"] == 3
    assert by_reducer["map-only"]["f1"] == 0.8
    assert by_reducer["service-local"]["hypothesis_count"] == 2
    assert by_reducer["service-local"]["f1"] == 1.0
    assert by_reducer["hybrid-hint"]["f1"] == 1.0
    assert len(result["replay"]["result_digest"]) == 64
