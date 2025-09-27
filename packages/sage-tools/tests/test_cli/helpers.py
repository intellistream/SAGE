"""Utility helpers for SAGE CLI integration tests.

This module provides a small framework around :class:`typer.testing.CliRunner`
so individual CLI test scripts can focus on describing the commands they want to
validate instead of wiring mocks and assertion plumbing repeatedly.
"""

from __future__ import annotations

import copy
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

from typer.testing import CliRunner

from sage.tools.cli.main import app as sage_app

# Type alias for factory functions that return context managers (e.g. mocks).
PatchFactory = Callable[[], object]
CheckCallable = Callable[["CLITestResult"], None]


@dataclass
class CLITestCase:
    """Represents a single CLI invocation that should succeed."""

    name: str
    args: Sequence[str]
    app: object = sage_app
    patch_factories: Sequence[PatchFactory] = field(default_factory=tuple)
    env: Optional[dict[str, str]] = None
    expected_exit_code: int = 0
    check: Optional[CheckCallable] = None


@dataclass
class CLITestResult:
    """Outcome of executing a :class:`CLITestCase`."""

    case: CLITestCase
    exit_code: int
    stdout: str
    stderr: str
    exception: BaseException | None

    @property
    def ok(self) -> bool:
        return self.exit_code == self.case.expected_exit_code and self.exception is None


@dataclass
class CLIRunSummary:
    """Summary returned by :func:`run_cases` or the CLI test runner."""

    results: List[CLITestResult]

    @property
    def success(self) -> bool:
        return all(result.ok for result in self.results)

    @property
    def failures(self) -> List[CLITestResult]:
        return [result for result in self.results if not result.ok]


class FakeConfigManager:
    """In-memory drop-in replacement for :class:`ConfigManager`."""

    def __init__(self, config: Optional[dict] = None):
        self._temp_dir = Path(tempfile.mkdtemp(prefix="sage_cli_config_"))
        self.config_path = self._temp_dir / "config.yaml"
        self._config = copy.deepcopy(config or default_config())
        self._config.setdefault("workers_ssh_hosts", [])

    def load_config(self) -> dict:
        return copy.deepcopy(self._config)

    def save_config(self, config: dict):
        self._config = copy.deepcopy(config)

    def init_config(self):
        self.save_config(default_config())

    @property
    def config(self) -> dict:
        return copy.deepcopy(self._config)

    def get_head_config(self) -> dict:
        return copy.deepcopy(self._config.get("head", {}))

    def get_worker_config(self) -> dict:
        return copy.deepcopy(self._config.get("worker", {}))

    def get_ssh_config(self) -> dict:
        return copy.deepcopy(self._config.get("ssh", {}))

    def get_remote_config(self) -> dict:
        return copy.deepcopy(self._config.get("remote", {}))

    def get_workers_ssh_hosts(self) -> List[tuple[str, int]]:
        hosts = self._config.get("workers_ssh_hosts", [])
        if isinstance(hosts, list):
            return [(item["host"], item.get("port", 22)) for item in hosts]
        return []

    def add_worker_ssh_host(self, host: str, port: int = 22) -> bool:
        hosts = self._config.setdefault("workers_ssh_hosts", [])
        for item in hosts:
            if item["host"] == host and item.get("port", 22) == port:
                return False
        hosts.append({"host": host, "port": port})
        return True

    def remove_worker_ssh_host(self, host: str, port: int = 22) -> bool:
        hosts = self._config.setdefault("workers_ssh_hosts", [])
        original_len = len(hosts)
        hosts[:] = [item for item in hosts if not (item["host"] == host and item.get("port", 22) == port)]
        return len(hosts) < original_len

    def get_worker_config_path(self) -> Path:
        return self._temp_dir


def default_config() -> dict:
    """Return a representative configuration dictionary for tests."""

    return {
        "head": {
            "host": "127.0.0.1",
            "head_port": 6379,
            "dashboard_port": 8265,
            "dashboard_host": "127.0.0.1",
            "temp_dir": "/tmp/ray_head",
            "log_dir": "/tmp/sage_head_logs",
            "ray_command": "ray",
            "conda_env": "sage",
        },
        "worker": {
            "bind_host": "127.0.0.1",
            "temp_dir": "/tmp/ray_worker",
            "log_dir": "/tmp/sage_worker_logs",
        },
        "ssh": {
            "user": "sage",
            "key_path": "~/.ssh/id_rsa",
            "connect_timeout": 5,
            "workers": [
                {"host": "worker-node-1", "port": 22},
                {"host": "worker-node-2", "port": 2200},
            ],
        },
        "remote": {
            "sage_home": "/opt/sage",
            "python_path": "/opt/conda/bin/python",
            "ray_command": "ray",
            "conda_env": "sage",
        },
        "monitor": {"refresh_interval": 5},
        "jobmanager": {"timeout": 10, "retry_attempts": 2},
    }


def run_case(case: CLITestCase) -> CLITestResult:
    """Execute a single CLI test case."""

    runner = CliRunner()
    with ExitStack() as stack:
        for factory in case.patch_factories:
            stack.enter_context(factory())
        result = runner.invoke(case.app, list(case.args), env=case.env)

    cli_result = CLITestResult(
        case=case,
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr or "",
        exception=result.exception,
    )

    if case.check is not None:
        case.check(cli_result)

    return cli_result


def run_cases(cases: Iterable[CLITestCase]) -> CLIRunSummary:
    results = [run_case(case) for case in cases]
    return CLIRunSummary(results=results)


class FakeCompletedProcess:
    """Simple stand-in for :class:`subprocess.CompletedProcess`."""

    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class DummyProcess:
    """A lightweight object emulating a running process for CLI tests."""

    def __init__(self, pid: int = 1234, cmd: Optional[List[str]] = None):
        self.pid = pid
        self._cmd = cmd or ["python", "-m", "sage"]

    # Methods used by psutil during CLI commands
    def terminate(self):
        return None

    def kill(self):
        return None

    def wait(self, timeout: Optional[int] = None):
        return 0

    def cpu_percent(self):
        return 0.5

    def memory_info(self):
        return type("Mem", (), {"rss": 10 * 1024 * 1024})()

    def create_time(self):
        import time

        return time.time() - 30

    def cmdline(self):
        return list(self._cmd)

    def oneshot(self):
        class _Oneshot:
            def __enter__(self_inner):
                return self

            def __exit__(self_inner, exc_type, exc, tb):
                return False

        return _Oneshot()


__all__ = [
    "CLITestCase",
    "CLITestResult",
    "CLIRunSummary",
    "FakeCompletedProcess",
    "FakeConfigManager",
    "DummyProcess",
    "default_config",
    "run_case",
    "run_cases",
]
