"""Helpers for process PID state files used by CLI runtime commands."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import psutil


def read_running_pid(
    pid_file: Path,
    *,
    matcher: Callable[[psutil.Process], bool] | None = None,
) -> int | None:
    """Read PID from file and return it only if process is still valid.

    The PID file is removed automatically when the PID is invalid/stale.
    """
    if not pid_file.exists():
        return None

    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, OSError):
        pid_file.unlink(missing_ok=True)
        return None

    if not psutil.pid_exists(pid):
        pid_file.unlink(missing_ok=True)
        return None

    if matcher is None:
        return pid

    try:
        proc = psutil.Process(pid)
        if matcher(proc):
            return pid
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    pid_file.unlink(missing_ok=True)
    return None


def write_pid(pid_file: Path, pid: int) -> None:
    """Persist PID to file, ensuring parent directory exists."""
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid))
