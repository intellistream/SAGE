from __future__ import annotations

import contextvars
from concurrent.futures import Executor, ThreadPoolExecutor
from functools import partial
from threading import Lock
from typing import Any

DEFAULT_SYNC_LANE = "default_cpu"
TORCH_DEDICATED_SYNC_LANE = "torch_dedicated"
SUPPORTED_SYNC_LANES = frozenset({DEFAULT_SYNC_LANE, TORCH_DEDICATED_SYNC_LANE})


def resolve_sync_lane(actor_config: Any | None) -> str:
    lane = None
    execution = _extract_execution_config(actor_config)
    if isinstance(execution, dict):
        lane = execution.get("sync_lane")
    elif execution is not None:
        lane = getattr(execution, "sync_lane", None)

    if lane is None:
        if isinstance(actor_config, dict):
            lane = actor_config.get("sync_lane")
        elif actor_config is not None:
            lane = getattr(actor_config, "sync_lane", None)

    if lane is None:
        return DEFAULT_SYNC_LANE

    normalized_lane = str(lane).strip().lower()
    if normalized_lane not in SUPPORTED_SYNC_LANES:
        raise ValueError(f"unsupported_sync_lane:{normalized_lane}")
    return normalized_lane


def resolve_policy_max_workers(actor_config: Any | None) -> int | None:
    task_policy = _extract_task_policy(actor_config)
    if task_policy is None:
        return None
    raw_value = task_policy.get("max_workers")
    if raw_value is None:
        return None
    max_workers = int(raw_value)
    if max_workers <= 0:
        raise ValueError("max_workers must be > 0 when provided.")
    return max_workers


def run_in_executor_with_context(
    loop: Any,
    func,
    *args,
    executor: Executor | None = None,
    **kwargs,
):
    ctx = contextvars.copy_context()
    bound = partial(func, *args, **kwargs)
    return loop.run_in_executor(executor, ctx.run, bound)


class ExecutorLanes:
    """Executor lane registry for v1 sync actor execution."""

    def __init__(
        self,
        *,
        default_cpu_max_workers: int | None = None,
        thread_name_prefix: str = "flownet-v1",
    ) -> None:
        if default_cpu_max_workers is not None and int(default_cpu_max_workers) <= 0:
            raise ValueError("default_cpu_max_workers must be > 0 when provided.")
        self._default_cpu_max_workers = (
            int(default_cpu_max_workers) if default_cpu_max_workers is not None else None
        )
        self._thread_name_prefix = str(thread_name_prefix)
        self._default_cpu_executor: ThreadPoolExecutor | None = None
        self._policy_cpu_executors: dict[str, ThreadPoolExecutor] = {}
        self._torch_dedicated_executors: dict[str, ThreadPoolExecutor] = {}
        self._shutdown = False
        self._lock = Lock()

    def lane_for(self, *, actor_config: Any | None) -> str:
        return resolve_sync_lane(actor_config)

    def executor_for(self, *, actor_id: str, actor_config: Any | None = None) -> ThreadPoolExecutor:
        normalized_actor_id = _normalize_actor_id(actor_id)
        lane = resolve_sync_lane(actor_config)
        policy_max_workers = resolve_policy_max_workers(actor_config)

        with self._lock:
            if self._shutdown:
                raise RuntimeError("executor_lanes_already_shutdown")

            if lane == DEFAULT_SYNC_LANE:
                if policy_max_workers is not None:
                    executor = self._policy_cpu_executors.get(normalized_actor_id)
                    if executor is None:
                        executor = ThreadPoolExecutor(
                            max_workers=policy_max_workers,
                            thread_name_prefix=(
                                f"{self._thread_name_prefix}-cpu-policy-"
                                f"{_executor_actor_suffix(normalized_actor_id)}"
                            ),
                        )
                        self._policy_cpu_executors[normalized_actor_id] = executor
                    return executor
                if self._default_cpu_executor is None:
                    self._default_cpu_executor = ThreadPoolExecutor(
                        max_workers=self._default_cpu_max_workers,
                        thread_name_prefix=f"{self._thread_name_prefix}-cpu",
                    )
                return self._default_cpu_executor

            executor = self._torch_dedicated_executors.get(normalized_actor_id)
            if executor is None:
                executor = ThreadPoolExecutor(
                    max_workers=policy_max_workers or 1,
                    thread_name_prefix=(
                        f"{self._thread_name_prefix}-torch-{_executor_actor_suffix(normalized_actor_id)}"
                    ),
                )
                self._torch_dedicated_executors[normalized_actor_id] = executor
            return executor

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = False) -> None:
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True
            default_executor = self._default_cpu_executor
            policy_executors = list(self._policy_cpu_executors.values())
            dedicated_executors = list(self._torch_dedicated_executors.values())
            self._default_cpu_executor = None
            self._policy_cpu_executors = {}
            self._torch_dedicated_executors = {}

        executors = dedicated_executors + policy_executors
        if default_executor is not None:
            executors.append(default_executor)

        for executor in executors:
            executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    def observability_snapshot(self) -> dict[str, Any]:
        with self._lock:
            default_executor = self._default_cpu_executor
            policy_cpu_executors = dict(self._policy_cpu_executors)
            torch_dedicated_executors = dict(self._torch_dedicated_executors)
            default_cpu_max_workers = self._default_cpu_max_workers

        return {
            "default_cpu": {
                "configured_max_workers": default_cpu_max_workers,
                "executor_max_workers": _executor_max_workers(
                    default_executor, default_cpu_max_workers
                ),
                "active_executor": default_executor is not None,
                "policy_executor_max_workers": {
                    actor_id: _executor_max_workers(executor, None)
                    for actor_id, executor in sorted(policy_cpu_executors.items())
                },
            },
            "torch_dedicated": {
                "executor_max_workers": {
                    actor_id: _executor_max_workers(executor, None)
                    for actor_id, executor in sorted(torch_dedicated_executors.items())
                },
            },
        }


def _normalize_actor_id(actor_id: str) -> str:
    normalized = str(actor_id).strip()
    if not normalized:
        raise ValueError("actor_id must be non-empty.")
    return normalized


def _extract_execution_config(actor_config: Any | None) -> Any | None:
    if actor_config is None:
        return None
    if isinstance(actor_config, dict):
        execution = actor_config.get("execution")
        if execution is not None:
            return execution
        return None
    return getattr(actor_config, "execution", None)


def _extract_task_policy(actor_config: Any | None) -> dict[str, Any] | None:
    if actor_config is None:
        return None
    if isinstance(actor_config, dict):
        task_policy = actor_config.get("task_policy")
        if task_policy is None:
            policies = actor_config.get("policies")
            if isinstance(policies, dict):
                task_policy = policies.get("task")
        if task_policy is None:
            execution_policy = actor_config.get("execution_policy")
            if isinstance(execution_policy, dict):
                task_policy = execution_policy.get("task")
    else:
        task_policy = getattr(actor_config, "task_policy", None)
        if task_policy is None:
            policies = getattr(actor_config, "policies", None)
            if isinstance(policies, dict):
                task_policy = policies.get("task")
        if task_policy is None:
            execution_policy = getattr(actor_config, "execution_policy", None)
            if isinstance(execution_policy, dict):
                task_policy = execution_policy.get("task")
    if task_policy is None:
        return None
    if not isinstance(task_policy, dict):
        raise TypeError("task_policy must be a mapping when provided.")
    return dict(task_policy)


def _executor_actor_suffix(actor_id: str) -> str:
    compact = actor_id.replace("/", "_").replace(":", "_")
    if len(compact) > 12:
        return compact[-12:]
    return compact


def _executor_max_workers(executor: ThreadPoolExecutor | None, fallback: int | None) -> int | None:
    if executor is None:
        return fallback
    raw = getattr(executor, "_max_workers", None)
    if raw is None:
        return fallback
    try:
        normalized = int(raw)
    except (TypeError, ValueError):
        return fallback
    if normalized <= 0:
        return fallback
    return normalized


__all__ = [
    "DEFAULT_SYNC_LANE",
    "TORCH_DEDICATED_SYNC_LANE",
    "SUPPORTED_SYNC_LANES",
    "resolve_sync_lane",
    "resolve_policy_max_workers",
    "run_in_executor_with_context",
    "ExecutorLanes",
]
