from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sage.cli.commands.apps import chat as chat_module
from sage.cli.main import main
from sage.foundation.config import user_paths as user_paths_module
from sage.serving.gateway import GatewayProbeResult


def test_chat_direct_requires_sagellm_binary(capsys: pytest.CaptureFixture[str]) -> None:
    status = main(["chat", "--backend", "direct", "--ask", "你好", "--stream"])
    captured = capsys.readouterr()

    assert status == 2
    assert "未找到 `sagellm` 可执行文件" in captured.err


def test_chat_direct_uses_sagellm_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(chat_module, "_sagellm_executable", lambda: "/tmp/fake-sagellm")

    recorded: dict[str, object] = {}

    def fake_run(command: list[str], check: bool = False):
        recorded["command"] = command
        recorded["check"] = check
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(chat_module.subprocess, "run", fake_run)

    status = main(
        [
            "chat",
            "--backend",
            "direct",
            "--ask",
            "你好",
            "--stream",
            "--model",
            "Qwen/Test",
            "--direct-backend",
            "cpu",
            "--max-tokens",
            "64",
        ]
    )

    assert status == 0
    assert recorded["command"] == [
        "/tmp/fake-sagellm",
        "run",
        "-p",
        "你好",
        "--stream",
        "-m",
        "Qwen/Test",
        "--backend",
        "cpu",
        "--max-tokens",
        "64",
    ]


def test_chat_auto_falls_back_to_direct_when_gateway_missing(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        chat_module,
        "probe_gateway",
        lambda cfg: GatewayProbeResult(ok=False, url=cfg.health_url, error="down"),
    )
    monkeypatch.setattr(chat_module, "_sagellm_executable", lambda: "/tmp/fake-sagellm")
    monkeypatch.setattr(chat_module, "_run_direct_sagellm", lambda prompt, args: 0)

    status = main(["chat", "--ask", "你好"])
    captured = capsys.readouterr()

    assert status == 0
    assert captured.err == ""


def test_chat_auto_requires_real_backend(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SAGE_CHAT_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SAGE_CHAT_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("SAGELLM_BASE_URL", raising=False)
    monkeypatch.setattr(chat_module, "_sagellm_executable", lambda: None)
    monkeypatch.setattr(
        chat_module,
        "probe_gateway",
        lambda cfg: GatewayProbeResult(ok=False, url=cfg.health_url, error="down"),
    )

    status = main(["chat", "--ask", "你好"])
    captured = capsys.readouterr()

    assert status == 2
    assert "本机也不存在 `sagellm` 命令" in captured.err


def test_chat_auto_uses_openai_env_when_configured(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setattr(chat_module, "_sagellm_executable", lambda: None)
    monkeypatch.setattr(
        chat_module,
        "probe_gateway",
        lambda cfg: GatewayProbeResult(ok=False, url=cfg.health_url, error="down"),
    )

    def fake_request(prompt: str, args: object) -> int:
        print(f"real-backend:{prompt}:{chat_module._chat_base_url(args)}")
        return 0

    monkeypatch.setattr(chat_module, "_request_openai_chat", fake_request)

    status = main(["chat", "--ask", "你好"])
    captured = capsys.readouterr()

    assert status == 0
    assert "real-backend:你好:https://example.invalid/v1" in captured.out


def test_verify_core_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = main(["verify"])
    captured = capsys.readouterr()

    assert status == 0
    assert "core    : ok" in captured.out


def test_index_ingest_writes_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    user_paths_module.get_user_data_dir.cache_clear()
    user_paths_module.get_user_config_dir.cache_clear()
    user_paths_module.get_user_state_dir.cache_clear()
    user_paths_module.get_user_cache_dir.cache_clear()
    user_paths_module._user_paths = None

    status = main(
        [
            "index",
            "ingest",
            "--quiet",
            "--index",
            "unit-test-index",
            "--source",
            "./docs",
        ]
    )

    metadata_path = chat_module.resolve_index_root("unit-test-index") / "metadata.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert status == 0
    assert payload["index"] == "unit-test-index"
    assert payload["mode"] == "core-placeholder"
