"""In-process runtime backend used by the reclaimed local execution path."""

from __future__ import annotations

import concurrent.futures
from threading import Lock
from typing import Any

from .backend_protocol import (
    ActorHandleProtocol,
    FlowRunHandleProtocol,
    MethodCallFuture,
    MethodRefProtocol,
    NodeInfoProtocol,
    RuntimeBackendProtocol,
)

__all__ = ["LocalRuntimeAdapter", "get_local_runtime_backend"]


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


class _LocalActorHandle(ActorHandleProtocol):
    def __init__(self, target: Any, executor: concurrent.futures.Executor) -> None:
        self._target = target
        self._executor = executor

    def get_method(self, name: str) -> MethodRefProtocol:
        return _LocalMethodRef(self._target, name, self._executor)


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
        instance = actor_class(*args, **kwargs)
        assert self._executor is not None
        return _LocalActorHandle(instance, self._executor)

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
