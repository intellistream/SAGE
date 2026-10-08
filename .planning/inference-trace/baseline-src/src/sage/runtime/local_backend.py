"""In-process runtime backend used by the reclaimed local execution path."""

from __future__ import annotations

import concurrent.futures
import hashlib
from threading import Lock
from typing import Any

from sage.foundation import CustomLogger

from .backend_protocol import (
    ActorHandleProtocol,
    FlowRunHandleProtocol,
    MethodCallFuture,
    MethodRefProtocol,
    NodeInfoProtocol,
    RuntimeBackendProtocol,
)

__all__ = ["LocalRuntimeAdapter", "get_local_runtime_backend"]


def _replica_count_from_actor_config(actor_config: Any) -> int:
    if not isinstance(actor_config, dict):
        return 1
    raw_parallelism = actor_config.get("parallelism")
    try:
        if raw_parallelism is not None:
            return max(1, int(raw_parallelism))
    except (TypeError, ValueError):
        return 1
    return 1


def _stable_replica_index(route_key: Any, replica_count: int) -> int:
    if replica_count <= 1:
        return 0
    digest = hashlib.blake2b(repr(route_key).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False) % replica_count


class _LocalReplicaExecutionContext:
    def __init__(self, name: str, *, parallel_index: int, parallelism: int) -> None:
        self.name = name
        self.parallel_index = parallel_index
        self.parallelism = parallelism
        self._logger = CustomLogger(name=name)
        self._current_key: Any = None

    @property
    def logger(self) -> CustomLogger:
        return self._logger

    def set_current_key(self, key: Any) -> None:
        self._current_key = key

    def clear_key(self) -> None:
        self._current_key = None

    def get_key(self) -> Any:
        return self._current_key


def _build_local_actor_instance(
    actor_class: type,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    replica_index: int,
    replica_count: int,
) -> Any:
    instance = actor_class(*args, **kwargs)
    function = getattr(instance, "_fn", None)
    if function is not None and getattr(function, "ctx", None) is None:
        context_name = actor_class.__name__
        if replica_count > 1:
            context_name = f"{context_name}_r{replica_index}"
        function.ctx = _LocalReplicaExecutionContext(
            context_name,
            parallel_index=replica_index,
            parallelism=replica_count,
        )
    return instance


def _extract_route_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any | None:
    if kwargs.get("partition_key") is not None:
        return kwargs["partition_key"]
    if not args:
        return None
    candidate = args[0]
    partition_key = getattr(candidate, "partition_key", None)
    if partition_key is not None:
        return partition_key
    return None


class _LocalMethodCallFuture(MethodCallFuture):
    def __init__(self, future: concurrent.futures.Future) -> None:
        self._future = future

    def result(self, timeout: float | None = None) -> Any:
        return self._future.result(timeout=timeout)

    def cancel(self) -> bool:
        return self._future.cancel()

    @property
    def done(self) -> bool:
        return self._future.done()


class _LocalMethodRef(MethodRefProtocol):
    def __init__(
        self, target: Any, method_name: str, executor: concurrent.futures.Executor
    ) -> None:
        self._target = target
        self._method_name = method_name
        self._executor = executor

    def call(self, *args: Any, **kwargs: Any) -> Any:
        return getattr(self._target, self._method_name)(*args, **kwargs)

    def async_call(self, *args: Any, **kwargs: Any) -> MethodCallFuture:
        future = self._executor.submit(self.call, *args, **kwargs)
        return _LocalMethodCallFuture(future)

    def cancel(self) -> bool:
        return False


class _LocalReplicaPoolMethodRef(MethodRefProtocol):
    def __init__(
        self,
        targets: tuple[Any, ...],
        method_name: str,
        executor: concurrent.futures.Executor,
    ) -> None:
        self._targets = targets
        self._method_name = method_name
        self._executor = executor
        self._selection_lock = Lock()
        self._rr_cursor = 0

    def _select_target(self, *args: Any, **kwargs: Any) -> Any:
        route_key = _extract_route_key(args, kwargs)
        if route_key is not None:
            return self._targets[_stable_replica_index(route_key, len(self._targets))]

        with self._selection_lock:
            selected = self._targets[self._rr_cursor % len(self._targets)]
            self._rr_cursor += 1
            return selected

    def call(self, *args: Any, **kwargs: Any) -> Any:
        target = self._select_target(*args, **kwargs)
        return getattr(target, self._method_name)(*args, **kwargs)

    def async_call(self, *args: Any, **kwargs: Any) -> MethodCallFuture:
        future = self._executor.submit(self.call, *args, **kwargs)
        return _LocalMethodCallFuture(future)

    def cancel(self) -> bool:
        return False


class _LocalActorHandle(ActorHandleProtocol):
    def __init__(
        self,
        target: Any | tuple[Any, ...],
        executor: concurrent.futures.Executor,
    ) -> None:
        if isinstance(target, tuple):
            self._targets = target
        else:
            self._targets = (target,)
        self._executor = executor

    def get_method(self, name: str) -> MethodRefProtocol:
        if len(self._targets) == 1:
            return _LocalMethodRef(self._targets[0], name, self._executor)
        return _LocalReplicaPoolMethodRef(self._targets, name, self._executor)

    @property
    def replica_count(self) -> int:
        return len(self._targets)


class _UnsupportedFlowHandle(FlowRunHandleProtocol):
    def call(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("LocalRuntimeAdapter does not submit external flow handles directly")

    def cancel(self) -> None:
        return None


class _LocalNodeInfo(NodeInfoProtocol):
    @property
    def node_id(self) -> str:
        return "local"

    @property
    def address(self) -> str:
        return "127.0.0.1"

    @property
    def is_schedulable(self) -> bool:
        return True

    @property
    def resource_summary(self) -> dict[str, Any]:
        return {"schedulable": True, "mode": "in-process"}


class LocalRuntimeAdapter(RuntimeBackendProtocol):
    def __init__(self) -> None:
        self._started = False
        self._lock = Lock()
        self._executor: concurrent.futures.ThreadPoolExecutor | None = None

    def start(self, config: Any | None = None) -> None:
        with self._lock:
            if self._started:
                return
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=8,
                thread_name_prefix="sage_local_runtime",
            )
            self._started = True

    def stop(self) -> None:
        with self._lock:
            if self._executor is not None:
                self._executor.shutdown(wait=True)
                self._executor = None
            self._started = False

    def create(
        self,
        actor_class: type,
        /,
        *args: Any,
        actor_config: Any | None = None,
        **kwargs: Any,
    ) -> ActorHandleProtocol:
        if not self._started:
            self.start()
        replica_count = _replica_count_from_actor_config(actor_config)
        instances = tuple(
            _build_local_actor_instance(
                actor_class,
                args,
                kwargs,
                replica_index=replica_index,
                replica_count=replica_count,
            )
            for replica_index in range(replica_count)
        )
        assert self._executor is not None
        return _LocalActorHandle(instances, self._executor)

    def submit(
        self,
        flow_obj: Any,
        *,
        ingress: Any | None = None,
        egress: Any | None = None,
        run_config: Any | None = None,
    ) -> FlowRunHandleProtocol:
        return _UnsupportedFlowHandle()

    def list_nodes(self) -> list[NodeInfoProtocol]:
        return [_LocalNodeInfo()]


_LOCAL_BACKEND: LocalRuntimeAdapter | None = None


def get_local_runtime_backend() -> LocalRuntimeAdapter:
    global _LOCAL_BACKEND
    if _LOCAL_BACKEND is None:
        _LOCAL_BACKEND = LocalRuntimeAdapter()
        _LOCAL_BACKEND.start()
    return _LOCAL_BACKEND
