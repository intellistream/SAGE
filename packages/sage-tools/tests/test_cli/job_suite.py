"""Test cases for the ``sage job`` command group."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Callable, Dict, List
from unittest.mock import patch

from sage.tools.cli.main import app as sage_app

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

    def list_jobs() -> Dict[str, object]:
        return {"status": "success", "jobs": jobs}

    def get_job_status(uuid: str) -> Dict[str, object]:
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

    def health_check() -> Dict[str, object]:
        return {
            "status": "success",
            "daemon_status": {
                "socket_service": "running",
                "actor_name": "demo",
                "namespace": "default",
            },
        }

    def get_server_info() -> Dict[str, object]:
        return {
            "status": "success",
            "server_info": {
                "session_id": "session-1",
                "log_base_dir": "/tmp/sage",
                "environments_count": 1,
                "jobs": jobs,
            },
        }

    def pause_job(uuid: str) -> Dict[str, object]:
        return {"status": "stopped", "message": f"{uuid} stopped"}

    def continue_job(uuid: str) -> Dict[str, object]:
        return {"status": "running", "message": f"{uuid} continued"}

    def delete_job(uuid: str, force: bool = False) -> Dict[str, object]:
        return {"status": "success", "message": "deleted"}

    def cleanup_all_jobs() -> Dict[str, object]:
        return {"status": "success", "message": "all cleaned"}

    return SimpleNamespace(
        list_jobs=list_jobs,
        get_job_status=get_job_status,
        health_check=health_check,
        get_server_info=get_server_info,
        pause_job=pause_job,
        continue_job=continue_job,
        delete_job=delete_job,
        cleanup_all_jobs=cleanup_all_jobs,
    )


def _patch_cli_client() -> List[Callable[[], object]]:
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
            "sage job show",
            ["job", "show", "1"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job stop force",
            ["job", "stop", "job-demo-uuid", "--force"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job continue force",
            ["job", "continue", "job-demo-uuid", "--force"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job delete force",
            ["job", "delete", "job-demo-uuid", "--force"],
            app=sage_app,
            patch_factories=patches,
        ),
        CLITestCase(
            "sage job cleanup force",
            ["job", "cleanup", "--force"],
            app=sage_app,
            patch_factories=patches,
        ),
    ]
