"""Test cases for ``sage inference`` command group."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from sage.cli.main import app as sage_app

from .helpers import CLITestCase, DummyProcess

MODULE = "sage.cli.commands.apps.inference"


def _fake_process(pid: int = 4321) -> MagicMock:
    proc = MagicMock()
    proc.pid = pid
    proc.wait.return_value = 0
    proc.terminate.return_value = None
    proc.kill.return_value = None
    return proc


def _patch_temp_paths(*, write_log: bool = False):
    temp_dir = Path(tempfile.mkdtemp(prefix="sage_inference_cli_"))
    pid_file = temp_dir / "inference.pid"
    config_file = temp_dir / "inference.json"
    log_file = temp_dir / "logs" / "inference.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if write_log:
        log_file.write_text("line1\nline2\n", encoding="utf-8")

    return [
        lambda: patch(f"{MODULE}.PID_FILE", pid_file),
        lambda: patch(f"{MODULE}.CONFIG_FILE", config_file),
        lambda: patch(f"{MODULE}.LOG_FILE", log_file),
    ]


def _patch_psutil_process():
    return lambda: patch(
        f"{MODULE}.psutil.Process",
        side_effect=lambda pid: DummyProcess(pid=pid),
    )


def _patch_running_pid(pid: int | None):
    return lambda: patch(f"{MODULE}._get_running_pid", return_value=pid)


def _patch_port_in_use(result: bool):
    return lambda: patch(f"{MODULE}._is_port_in_use", return_value=result)


def _patch_popen():
    return lambda: patch(f"{MODULE}.subprocess.Popen", return_value=_fake_process())


def _patch_health_response():
    return lambda: patch(
        f"{MODULE}._test_api_health",
        return_value={
            "status": "success",
            "backends": {
                "llm": {"healthy": True},
                "embedding": {"healthy": True},
            },
        },
    )


def _patch_load_config(config: dict):
    return lambda: patch(f"{MODULE}._load_config", return_value=config)


def collect_cases() -> list[CLITestCase]:
    return [
        CLITestCase(
            "sage inference start background",
            ["inference", "start", "--background", "--port", "8100"],
            app=sage_app,
            patch_factories=_patch_temp_paths()
            + [
                _patch_running_pid(None),
                _patch_port_in_use(False),
                _patch_popen(),
                lambda: patch(f"{MODULE}._save_pid"),
                lambda: patch(f"{MODULE}._save_config"),
            ],
        ),
        CLITestCase(
            "sage inference stop force",
            ["inference", "stop", "--force"],
            app=sage_app,
            patch_factories=_patch_temp_paths()
            + [
                _patch_running_pid(9001),
                _patch_psutil_process(),
            ],
        ),
        CLITestCase(
            "sage inference status json",
            ["inference", "status", "--json"],
            app=sage_app,
            patch_factories=_patch_temp_paths()
            + [
                _patch_running_pid(1234),
                _patch_psutil_process(),
                _patch_port_in_use(True),
                _patch_health_response(),
                _patch_load_config({"port": 8000, "llm_model": "demo"}),
            ],
        ),
        CLITestCase(
            "sage inference config json",
            ["inference", "config", "--output", "json"],
            app=sage_app,
            patch_factories=[
                _patch_load_config(
                    {
                        "host": "0.0.0.0",
                        "port": 8000,
                        "llm_model": "demo-llm",
                        "embedding_model": "demo-embed",
                        "scheduling_policy": "adaptive",
                    }
                )
            ],
        ),
        CLITestCase(
            "sage inference logs tail",
            ["inference", "logs", "-n", "1"],
            app=sage_app,
            patch_factories=_patch_temp_paths(write_log=True),
        ),
    ]
