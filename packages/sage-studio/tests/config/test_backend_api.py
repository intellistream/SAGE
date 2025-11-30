"""Tests for selected helpers inside `sage.studio.config.backend.api`."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from sage.studio.config.backend import api

client = TestClient(api.app)


def test_convert_pipeline_to_job_infers_metadata(tmp_path: Path):
    pipeline = {
        "name": "Test Pipeline",
        "description": "demo",
        "nodes": [
            {"id": "source", "name": "Source"},
            {"id": "sink", "name": "Sink"},
        ],
        "edges": [
            {"source": "source", "target": "sink"},
        ],
    }

    file_path = tmp_path / "pipeline_1000.json"
    file_path.write_text(json.dumps(pipeline))

    job = api._convert_pipeline_to_job(pipeline, "pipeline_1000", file_path)

    assert job["jobId"] == "pipeline_1000"
    assert job["description"] == "demo"
    assert job["operators"][0]["downstream"] == [1]
    assert job["config"]["nodes"] == pipeline["nodes"]


def test_read_sage_data_from_files_handles_missing(tmp_path: Path, monkeypatch):
    def fake_get_sage_dir() -> Path:
        return tmp_path

    monkeypatch.setattr(api, "_get_sage_dir", fake_get_sage_dir)

    data = api._read_sage_data_from_files()

    # When there are no files, we still return the default structure
    assert data == {"jobs": [], "operators": [], "pipelines": []}


def test_submit_pipeline_persists_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(api, "_get_sage_dir", lambda: tmp_path)

    payload = {"name": "Flow", "nodes": [], "edges": []}

    response = client.post("/api/pipeline/submit", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"

    pipelines_dir = tmp_path / "pipelines"
    saved_files = list(pipelines_dir.glob("pipeline_*.json"))
    assert saved_files, "Pipeline file should be saved"
