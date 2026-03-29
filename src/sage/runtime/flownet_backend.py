"""FlowNet runtime adapter reclaimed into the main SAGE repository."""

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
    __slots__ = ("_actor_id", "_method_name", "_registry")

    def __init__(self, actor_id: str, method_name: str, registry: Any) -> None:
        self._actor_id = actor_id
        self._method_name = method_name
        self._registry = registry

    def call(self, *args: Any, **kwargs: Any) -> Any:
        record = self._registry.resolve_local_actor(self._actor_id)
        method = getattr(record.object, self._method_name)
        return method(*args, **kwargs)

    def async_call(self, *args: Any, **kwargs: Any) -> MethodCallFuture:
        fut = _get_async_executor().submit(self.call, *args, **kwargs)
        return _FlowNetMethodCallFuture(fut)

    def cancel(self) -> bool:
        return False


class _FlowNetActorHandle(ActorHandleProtocol):
    def __init__(self, actor_id: str, registry: Any) -> None:
        object.__setattr__(self, "_actor_id", actor_id)
        object.__setattr__(self, "_registry", registry)

    def get_method(self, name: str) -> MethodRefProtocol:
        return _FlowNetMethodRef(self._actor_id, name, self._registry)

    def cancel(self) -> bool:
        try:
            return bool(self._registry.delete_local_actor(self._actor_id))
        except Exception:
            return False


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
        instance = actor_class(*args, **kwargs)
        actor_id = self._registry.register_local_actor(instance, config=actor_config)
        return _FlowNetActorHandle(actor_id, self._registry)

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
