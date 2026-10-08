"""FlowNet runtime adapter reclaimed into the main SAGE repository."""

from __future__ import annotations

import asyncio
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
from .exception_hooks import register_kernel_exception_handler_hook

__all__ = ["FlowNetRuntimeAdapter", "get_flownet_adapter"]


def _require_flownet(operation: str) -> None:
    try:
        import sage.runtime.flownet  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            f"FlowNetRuntimeAdapter.{operation}() requires the in-tree flownet runtime package.\n"
            "Install/update SAGE from this repository so src/sage/runtime/flownet is available.\n"
            f"Original error: {exc}"
        ) from exc


_async_executor: concurrent.futures.ThreadPoolExecutor | None = None
_async_executor_lock: Lock = Lock()


def _get_async_executor() -> concurrent.futures.ThreadPoolExecutor:
    global _async_executor
    with _async_executor_lock:
        if _async_executor is None:
            _async_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=32,
                thread_name_prefix="sage_flownet_async",
            )
    return _async_executor


class _FlowNetMethodCallFuture(MethodCallFuture):
    __slots__ = ("_fut",)

    def __init__(self, fut: concurrent.futures.Future) -> None:
        self._fut = fut

    def result(self, timeout: float | None = None) -> Any:
        try:
            return self._fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(f"Actor method call did not complete within {timeout}s.") from exc
        except concurrent.futures.CancelledError as exc:
            raise RuntimeError("Actor method call was cancelled.") from exc

    def cancel(self) -> bool:
        return self._fut.cancel()

    @property
    def done(self) -> bool:
        return self._fut.done()


class _FlowNetMethodRef(MethodRefProtocol):
    __slots__ = ("_actor_api", "_actor_id", "_method_name")

    def __init__(self, actor_api: Any, actor_id: str, method_name: str) -> None:
        self._actor_api = actor_api
        self._actor_id = actor_id
        self._method_name = method_name

    def call(self, *args: Any, **kwargs: Any) -> Any:
        return _run_actor_api_call(
            self._actor_api,
            self._actor_id,
            self._method_name,
            *args,
            **kwargs,
        )

    def async_call(self, *args: Any, **kwargs: Any) -> MethodCallFuture:
        fut = _get_async_executor().submit(self.call, *args, **kwargs)
        return _FlowNetMethodCallFuture(fut)

    def cancel(self) -> bool:
        return False


def _stable_replica_index(route_key: Any, replica_count: int) -> int:
    if replica_count <= 1:
        return 0
    digest = hashlib.blake2b(repr(route_key).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False) % replica_count


def _replica_count_from_actor_config(actor_config: Any) -> int:
    if not isinstance(actor_config, dict):
        return 1
    raw_parallelism = actor_config.get("parallelism")
    try:
        if raw_parallelism is not None:
            return max(1, int(raw_parallelism))
    except (TypeError, ValueError):
        pass

    override = actor_config.get("materialization_policy_override")
    if not isinstance(override, dict):
        return 1
    replica_policy = override.get("replica_policy")
    if not isinstance(replica_policy, dict):
        return 1
    try:
        return max(1, int(replica_policy.get("count", 1)))
    except (TypeError, ValueError):
        return 1


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


def _run_actor_api_call(
    actor_api: Any,
    actor_id: str,
    method_name: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    coro = actor_api.call_local(actor_id, method_name, *args, **kwargs)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError(
        "FlowNet actor method refs require a synchronous caller outside a running event loop."
    )


class _FlowNetReplicaExecutionContext:
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


def _build_flow_actor_instance(
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
        function.ctx = _FlowNetReplicaExecutionContext(
            context_name,
            parallel_index=replica_index,
            parallelism=replica_count,
        )
    return instance


class _FlowNetReplicaPoolMethodRef(MethodRefProtocol):
    __slots__ = ("_actor_api", "_actor_ids", "_method_name", "_selection_lock", "_rr_cursor")

    def __init__(self, actor_api: Any, actor_ids: tuple[str, ...], method_name: str) -> None:
        self._actor_api = actor_api
        self._actor_ids = actor_ids
        self._method_name = method_name
        self._selection_lock = Lock()
        self._rr_cursor = 0

    def _select_actor_id(self, *args: Any, **kwargs: Any) -> str:
        route_key = _extract_route_key(args, kwargs)
        if route_key is not None:
            return self._actor_ids[_stable_replica_index(route_key, len(self._actor_ids))]

        with self._selection_lock:
            selected = self._actor_ids[self._rr_cursor % len(self._actor_ids)]
            self._rr_cursor += 1
            return selected

    def call(self, *args: Any, **kwargs: Any) -> Any:
        actor_id = self._select_actor_id(*args, **kwargs)
        return _run_actor_api_call(
            self._actor_api,
            actor_id,
            self._method_name,
            *args,
            **kwargs,
        )

    def async_call(self, *args: Any, **kwargs: Any) -> MethodCallFuture:
        fut = _get_async_executor().submit(self.call, *args, **kwargs)
        return _FlowNetMethodCallFuture(fut)

    def cancel(self) -> bool:
        return False


class _FlowNetActorHandle(ActorHandleProtocol):
    def __init__(self, actor_api: Any, actor_id: str | tuple[str, ...], registry: Any) -> None:
        if isinstance(actor_id, tuple):
            actor_ids = actor_id
        else:
            actor_ids = (actor_id,)
        object.__setattr__(self, "_actor_api", actor_api)
        object.__setattr__(self, "_actor_ids", actor_ids)
        object.__setattr__(self, "_registry", registry)

    def get_method(self, name: str) -> MethodRefProtocol:
        if len(self._actor_ids) == 1:
            return _FlowNetMethodRef(self._actor_api, self._actor_ids[0], name)
        return _FlowNetReplicaPoolMethodRef(self._actor_api, self._actor_ids, name)

    def cancel(self) -> bool:
        try:
            deleted_any = False
            for actor_id in self._actor_ids:
                deleted_any = self._registry.delete_local_actor(actor_id) or deleted_any
            return deleted_any
        except Exception:
            return False

    @property
    def replica_count(self) -> int:
        return len(self._actor_ids)


class _FlowNetFlowRunHandle(FlowRunHandleProtocol):
    __slots__ = ("_handle",)

    def __init__(self, handle: Any) -> None:
        self._handle = handle

    def call(self, *args: Any, **kwargs: Any) -> Any:
        call_fn = getattr(self._handle, "call", None)
        if not callable(call_fn):
            raise TypeError(f"FlowNet flow handle {type(self._handle)!r} does not expose .call().")
        return call_fn(*args, **kwargs)

    def cancel(self) -> None:
        cancel_fn = getattr(self._handle, "cancel", None)
        if cancel_fn is None:
            raise RuntimeError("FlowNet flow run handle does not support cancel().")
        cancel_fn()


class _FlowNetNodeInfo(NodeInfoProtocol):
    __slots__ = ("_node_id", "_address", "_resources")

    def __init__(
        self,
        node_id: str = "local",
        address: str = "127.0.0.1",
        resources: dict[str, Any] | None = None,
    ) -> None:
        self._node_id = node_id
        self._address = address
        self._resources = resources or {}

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def address(self) -> str:
        return self._address

    @property
    def is_schedulable(self) -> bool:
        return bool(self._resources.get("schedulable", True))

    @property
    def resource_summary(self) -> dict[str, Any]:
        return dict(self._resources)


_DEFAULT_LOCAL_ADDRESS = "127.0.0.1:19931"


class FlowNetRuntimeAdapter(RuntimeBackendProtocol):
    def __init__(self) -> None:
        self._started = False
        self._session: Any | None = None
        self._registry: Any | None = None
        self._actor_api: Any | None = None
        self._lock: Lock = Lock()

    def start(self, config: Any | None = None) -> None:
        with self._lock:
            if self._started:
                return
            _require_flownet("start")
            cfg: dict[str, Any] = dict(config) if isinstance(config, dict) else {}
            mode = str(cfg.get("mode", "lightweight")).strip().lower()
            local_address = str(cfg.get("local_address", _DEFAULT_LOCAL_ADDRESS)).strip()

            from sage.runtime.flownet.runtime.actors import ActorAPI
            from sage.runtime.flownet.runtime.actors.registry import LocalActorRegistry

            self._registry = LocalActorRegistry(local_address=local_address)
            self._actor_api = ActorAPI(local_address=local_address, registry=self._registry)

            if mode == "cluster":
                import sage.runtime.flownet as flownet

                self._session = flownet.init_local(
                    owner="sage-runtime", local_address=local_address
                )

            self._register_exception_hooks()
            self._started = True

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return
            if self._session is not None:
                try:
                    self._session.shutdown(wait=True)
                except Exception:
                    pass
                self._session = None
            self._registry = None
            self._actor_api = None
            self._started = False

    def _assert_started(self, op: str) -> None:
        if not self._started:
            raise RuntimeError(
                f"FlowNetRuntimeAdapter.{op}() called before start(). Call start() first or use get_flownet_adapter()."
            )

    @staticmethod
    def _register_exception_hooks() -> None:
        try:
            from sage.runtime.flownet.compiler.exception_scope import (
                flow_exception_handler as _feh,
            )

            def _push(handler: Any) -> None:
                _feh(handler).__enter__()

            def _pop() -> None:
                pass

            register_kernel_exception_handler_hook(_push, _pop)
        except Exception:
            pass

    def create(
        self,
        actor_class: type,
        /,
        *args: Any,
        actor_config: Any | None = None,
        **kwargs: Any,
    ) -> ActorHandleProtocol:
        self._assert_started("create")
        replica_count = _replica_count_from_actor_config(actor_config)
        actor_ids: list[str] = []
        for replica_index in range(replica_count):
            instance = _build_flow_actor_instance(
                actor_class,
                args,
                kwargs,
                replica_index=replica_index,
                replica_count=replica_count,
            )
            actor_id = self._registry.register_local_actor(instance, config=actor_config)
            actor_ids.append(actor_id)
        return _FlowNetActorHandle(self._actor_api, tuple(actor_ids), self._registry)

    def submit(
        self,
        flow_obj: Any,
        *,
        ingress: Any | None = None,
        egress: Any | None = None,
        run_config: Any | None = None,
    ) -> FlowRunHandleProtocol:
        self._assert_started("submit")
        if self._session is None:
            raise RuntimeError(
                "FlowNetRuntimeAdapter.submit() requires cluster mode. Start with config={'mode': 'cluster'}."
            )

        endpoint_fn = getattr(flow_obj, "endpoint", None)
        if callable(endpoint_fn):
            kwargs: dict[str, Any] = {}
            if ingress is not None:
                kwargs["in_topic"] = ingress
            if egress is not None:
                kwargs["out_topic"] = egress
            return _FlowNetFlowRunHandle(endpoint_fn(**kwargs))

        flow_uri = getattr(flow_obj, "flow_uri", None) or getattr(flow_obj, "uri", None)
        if flow_uri:
            result = self._session.submit_flow_program(
                str(flow_uri),
                ingress=ingress,
                egress=egress,
                run_config=dict(run_config) if run_config is not None else None,
            )
            return _FlowNetFlowRunHandle(result)

        raise TypeError(
            f"FlowNetRuntimeAdapter.submit() does not know how to submit {type(flow_obj)!r}. Pass a FlowDeclaration."
        )

    def list_nodes(self) -> list[NodeInfoProtocol]:
        self._assert_started("list_nodes")
        if self._session is not None:
            try:
                inspector_fn = getattr(self._session, "_runtime_inspector", None)
                if callable(inspector_fn):
                    inspector = inspector_fn()
                    snapshot = inspector.cluster_view_snapshot(schema="v1")
                    nodes_raw = snapshot.get("nodes", []) if isinstance(snapshot, dict) else []
                    return [
                        _FlowNetNodeInfo(
                            node_id=str(node.get("node_id", "unknown")),
                            address=str(node.get("address", "unknown")),
                            resources=node.get("resources", {}),
                        )
                        for node in nodes_raw
                    ]
            except Exception:
                pass
        return [_FlowNetNodeInfo()]


_adapter_singleton: FlowNetRuntimeAdapter | None = None
_adapter_lock: Lock = Lock()


def get_flownet_adapter(*, auto_start: bool = True) -> FlowNetRuntimeAdapter:
    global _adapter_singleton
    with _adapter_lock:
        if _adapter_singleton is None:
            _adapter_singleton = FlowNetRuntimeAdapter()
        if auto_start and not _adapter_singleton._started:
            _adapter_singleton.start()
        return _adapter_singleton
