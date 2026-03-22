from __future__ import annotations

import argparse
import importlib
import sys
import types

import pytest


@pytest.fixture(autouse=True)
def clear_edge_server_module() -> None:
    sys.modules.pop("sage.edge.server", None)
    yield
    sys.modules.pop("sage.edge.server", None)


def _import_server_module():
    return importlib.import_module("sage.edge.server")


def test_server_main_invokes_uvicorn_with_parsed_args(monkeypatch: pytest.MonkeyPatch) -> None:
    server = _import_server_module()
    parsed = argparse.Namespace(
        host="127.0.0.1",
        port=9988,
        llm_prefix="/edge",
        no_llm=False,
        log_level="debug",
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(server, "_parse_args", lambda: parsed)
    monkeypatch.setattr(server, "_load_llm_gateway_app", lambda: object())
    monkeypatch.setattr(
        server,
        "create_app",
        lambda *, mount_llm, llm_prefix, llm_app: (
            captured.update({"mount_llm": mount_llm, "llm_prefix": llm_prefix, "llm_app": llm_app})
            or object()
        ),
    )

    fake_uvicorn = types.SimpleNamespace(
        run=lambda app, *, host, port, log_level: captured.update(
            {"app": app, "host": host, "port": port, "log_level": log_level}
        )
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    server.main()

    assert captured["mount_llm"] is True
    assert captured["llm_prefix"] == "/edge"
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 9988
    assert captured["log_level"] == "debug"


def test_server_main_no_llm_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    server = _import_server_module()
    parsed = argparse.Namespace(
        host="0.0.0.0",
        port=8899,
        llm_prefix=None,
        no_llm=True,
        log_level="info",
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(server, "_parse_args", lambda: parsed)
    monkeypatch.setattr(
        server,
        "create_app",
        lambda *, mount_llm, llm_prefix, llm_app: (
            captured.update({"mount_llm": mount_llm, "llm_prefix": llm_prefix, "llm_app": llm_app})
            or object()
        ),
    )
    monkeypatch.setitem(
        sys.modules, "uvicorn", types.SimpleNamespace(run=lambda *args, **kwargs: None)
    )

    server.main()

    assert captured == {"mount_llm": False, "llm_prefix": None, "llm_app": None}


def test_load_llm_gateway_app_tries_known_specs(monkeypatch: pytest.MonkeyPatch) -> None:
    server = _import_server_module()
    gateway_module = types.ModuleType("sagellm_gateway.server")
    gateway_module.app = object()
    monkeypatch.setitem(sys.modules, "sagellm_gateway.server", gateway_module)

    loaded = server._load_llm_gateway_app()
    assert loaded is gateway_module.app


def test_load_llm_gateway_app_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    server = _import_server_module()

    def fail_import(name: str):
        raise ImportError(f"missing {name}")

    monkeypatch.setattr(server.importlib, "import_module", fail_import)

    with pytest.raises(ImportError, match="Unable to load a gateway ASGI app"):
        server._load_llm_gateway_app()
