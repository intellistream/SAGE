"""Test cases for the ``sage job`` command group."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import patch

from sage.cli.main import app as sage_app

from .helpers import CLITestCase


def _build_fake_client() -> SimpleNamespace:
    jobs = [
        {
            "uuid": "job-demo-uuid",
            "name": "demo-job",
            "status": "running",
            "start_time": "2025-01-01 00:00:00",
            "runtime": "00:05:00",
        }
    ]

    def list_jobs() -> dict[str, object]:
        return {"status": "success", "jobs": jobs}

    def get_job_status(uuid: str) -> dict[str, object]:
        return {
            "status": "success",
            "job_status": {
                "uuid": uuid,
                "name": "demo-job",
                "status": "running",
                "start_time": "2025-01-01 00:00:00",
                "runtime": "00:05:00",
            },
        }

    def health_check() -> dict[str, object]:
        return {
            "status": "success",
            "daemon_status": {
                "socket_service": "running",
                "actor_name": "demo",
                "namespace": "default",
            },
        }

    def get_server_info() -> dict[str, object]:
        return {
            "status": "success",
            "server_info": {
                "session_id": "session-1",
                "log_base_dir": "/tmp/sage",
                "environments_count": 1,
                "jobs": jobs,
            },
        }

    return SimpleNamespace(
        list_jobs=list_jobs,
        get_job_status=get_job_status,
        health_check=health_check,
        get_server_info=get_server_info,
        pause_job=lambda uuid: {"status": "stopped", "message": "stopped"},
        continue_job=lambda uuid: {"status": "running", "message": "resumed"},
        delete_job=lambda uuid, force=False: {"status": "success", "message": "deleted"},
        cleanup_all_jobs=lambda: {"status": "success", "message": "all cleaned"},
    )


def _patch_cli_client() -> list[Callable[[], object]]:
    fake_client = _build_fake_client()

    def fake_connect(self):  # type: ignore[override]
        self.client = fake_client
        self.connected = True
        return True

    def fake_ensure_connected(self):  # type: ignore[override]
        if not getattr(self, "connected", False):
            fake_connect(self)
        return True

    return [
        lambda: patch(
            "sage.tools.cli.commands.job.JobManagerCLI.connect",
            fake_connect,
        ),
        lambda: patch(
            "sage.tools.cli.commands.job.JobManagerCLI.ensure_connected",
            fake_ensure_connected,
        ),
        lambda: patch(
            "sage.tools.cli.commands.job.typer.confirm",
            return_value=True,
        ),
        lambda: patch(
            "sage.tools.cli.commands.job.cli._resolve_job_identifier",
            return_value="job-demo-uuid",
        ),
    ]


def collect_cases() -> list[CLITestCase]:
    patches = _patch_cli_client()

    return [
        CLITestCase(
            "sage job list",
            ["job", "list"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job status",
            ["job", "status", "job-demo-uuid"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job health",
            ["job", "health"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job info",
            ["job", "info"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job stop",
            ["job", "stop", "job-demo-uuid", "--force"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job continue",
            ["job", "continue", "job-demo-uuid", "--force"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job delete",
            ["job", "delete", "job-demo-uuid", "--force"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job cleanup",
            ["job", "cleanup", "--force"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job show",
            ["job", "show", "job-demo-uuid"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job pause alias",
            ["job", "pause", "job-demo-uuid", "--force"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job resume alias",
            ["job", "resume", "job-demo-uuid", "--force"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job monitor",
            ["job", "monitor", "--refresh", "0"],
            app=sage_app,
            patch_factories=patches
            + [
                lambda: patch(
                    "sage.tools.cli.commands.job.time.sleep",
                    side_effect=KeyboardInterrupt,
                ),
                lambda: patch(
                    "sage.tools.cli.commands.job.os.system",
                    return_value=0,
                ),
            ],
        ),
        CLITestCase(
            "sage job watch",
            ["job", "watch", "job-demo-uuid", "--refresh", "0"],
            app=sage_app,
            patch_factories=patches
            + [
                lambda: patch(
                    "sage.tools.cli.commands.job.time.sleep",
                    side_effect=KeyboardInterrupt,
                ),
                lambda: patch(
                    "sage.tools.cli.commands.job.os.system",
                    return_value=0,
                ),
            ],
        ),
    ]
