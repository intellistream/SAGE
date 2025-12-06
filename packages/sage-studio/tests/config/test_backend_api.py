"""Tests for selected helpers inside `sage.studio.config.backend.api`."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from sage.studio.config.backend import api
from sage.studio.services.auth_service import User
from datetime import datetime

client = TestClient(api.app)

def mock_get_current_user():
    return User(id=1, username="testuser", created_at=datetime.now())


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
    # Mock auth
    api.app.dependency_overrides[api.get_current_user] = mock_get_current_user

    # Mock user dir
    def fake_get_user_pipelines_dir(user_id: str) -> Path:
        d = tmp_path / "users" / user_id / "pipelines"
        d.mkdir(parents=True, exist_ok=True)
        return d

    monkeypatch.setattr(api, "get_user_pipelines_dir", fake_get_user_pipelines_dir)

    payload = {"name": "Flow", "nodes": [], "edges": []}

    response = client.post("/api/pipeline/submit", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    
    # Clean up override
    api.app.dependency_overrides = {}

    pipelines_dir = tmp_path / "users" / "1" / "pipelines"
    saved_files = list(pipelines_dir.glob("pipeline_*.json"))
    assert saved_files, "Pipeline file should be saved"
