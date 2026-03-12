from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sage.edge.app import create_app


@pytest.fixture
def mock_gateway_app() -> FastAPI:
    app = FastAPI(title="Mock Gateway")

    @app.get("/v1/models")
    async def list_models() -> dict[str, list[str]]:
        return {"data": ["mock-model"]}

    return app


def test_create_app_no_llm_health_and_ready() -> None:
    app = create_app(mount_llm=False)
    client = TestClient(app)

    assert client.get("/healthz").json() == {
        "status": "ok",
        "service": "SAGE Edge",
        "llm_mounted": False,
        "llm_prefix": "/",
    }
    assert client.get("/readyz").json()["status"] == "ready"


def test_create_app_mount_llm_at_root(mock_gateway_app: FastAPI) -> None:
    app = create_app(mount_llm=True, llm_app=mock_gateway_app)
    client = TestClient(app)

    assert client.get("/v1/models").json() == {"data": ["mock-model"]}
    assert client.get("/healthz").json()["llm_mounted"] is True


def test_create_app_mount_llm_at_custom_prefix(mock_gateway_app: FastAPI) -> None:
    app = create_app(mount_llm=True, llm_prefix="/llm", llm_app=mock_gateway_app)
    client = TestClient(app)

    assert client.get("/llm/v1/models").json() == {"data": ["mock-model"]}
    assert client.get("/healthz").json()["llm_prefix"] == "/llm"


def test_create_app_invalid_prefix_raises() -> None:
    with pytest.raises(ValueError, match="llm_prefix must start with '/'"):
        create_app(mount_llm=True, llm_prefix="llm", llm_app=FastAPI())


def test_create_app_missing_llm_app_raises() -> None:
    with pytest.raises(RuntimeError, match="requires explicit llm_app injection"):
        create_app(mount_llm=True)
