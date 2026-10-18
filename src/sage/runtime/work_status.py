"""Content-free observations of the existing durable work engine.

Snapshots neither claim work nor renew leases. They are not an authorization
grant, a storage probe, a handler-progress heartbeat or external-delivery proof.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True)
class WorkServiceStatus:
    namespace: str
    phase: Literal["created", "running", "draining", "stopped", "closed", "failed"]
    supervisor_alive: bool
    accepting: bool
    ready: bool
    error_type: str | None = None
    execution_context_running: bool | None = None
    drained: bool = False
    version: int = 1

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class WorkTaskStatus:
    task_id: str
    status: Literal["pending", "running", "done", "failed", "blocked"]
    attempt: int
    available_at: float
    lease_until: float
    lease_expired: bool
    claimable: bool
    dependency_task_ids: tuple[str, ...]
    dependency_mode: Literal["success", "settled"]
    dependencies_ready: bool
    last_failure_code: str | None


@dataclass(frozen=True)
class WorkRequestStatus:
    namespace: str
    request_id: str
    observed_at: float
    journal_version: int
    tasks: tuple[WorkTaskStatus, ...]
    version: int = 1

    def to_dict(self):
        return asdict(self)
