from __future__ import annotations

import atexit
import os
import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sage.runtime.flownet.client.bootstrap import (
    V1BootstrapHandle,
    bootstrap_node_runtime,
    bootstrap_runtime,
)
from sage.runtime.flownet.client.cluster_context import resolve_cluster_context
from sage.runtime.flownet.client.inspect import V1RuntimeInspector, build_runtime_inspector
from sage.runtime.flownet.client.node_runtime import (
    build_http_node_control_caller,
    resolve_default_node_control_caller,
)
from sage.runtime.flownet.client.runtime_client import (
    V1RuntimeClient,
    build_runtime_client,
    client_scope,
)
from sage.runtime.flownet.runtime import V1CommHub, V1RuntimeHost, V1TransportBackend

_DEFAULT_CONNECT_LOCAL_ADDRESS = "127.0.0.1:9920"
_DEFAULT_LOCAL_RUNTIME_LOCAL_ADDRESS = "127.0.0.1:19931"
_DEFAULT_LOCAL_RUNTIME_ENTRY_NODE = "127.0.0.1:18787"
_DEFAULT_CONNECT_PROBE_TIMEOUT = 1.5
_DEFAULT_SESSION_NODE_CONTROL_TIMEOUT = 3.0

_SESSION_LOCK = threading.RLock()
_ACTIVE_SESSION: V1Session | None = None
_ATEXIT_REGISTERED = False


@dataclass
class LocalClusterHandle:
    bootstrap: V1BootstrapHandle
    entry_node: str
    node_id: str
    _closed: bool = field(default=False, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    @property
    def runtime_host(self) -> V1RuntimeHost:
        return self.bootstrap.runtime_host

    @property
    def node_runtime(self) -> Any | None:
        return self.bootstrap.node_runtime

    @property
    def is_closed(self) -> bool:
        with self._lock:
            return self._closed

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = False) -> bool:
        with self._lock:
            if self._closed:
                return False
            self._closed = True
        self.bootstrap.shutdown(wait=wait, cancel_futures=cancel_futures)
        return True

    def __enter__(self) -> LocalClusterHandle:
        with self._lock:
            if self._closed:
                raise RuntimeError("flownet_local_cluster_closed")
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self.shutdown()
        return False

    def connect(
        self,
        *,
        owner: str = "local-owner",
        local_address: str | None = None,
        mode: str = "connect",
        runtime_host: V1RuntimeHost | None = None,
        owns_runtime_host: bool = False,
        comm_hub: V1CommHub | None = None,
        comm_transport: V1TransportBackend | None = None,
        comm_transport_mode: str | None = None,
        connect_timeout: float | None = None,
        probe_entry: bool = True,
        env: Mapping[str, str] | None = None,
        config_path: str | os.PathLike[str] | None = None,
        clusters_dir: str | os.PathLike[str] | None = None,
    ) -> V1Session:
        return connect(
            owner=owner,
            cluster=self,
            local_address=local_address,
            mode=mode,
            runtime_host=runtime_host,
            owns_runtime_host=owns_runtime_host,
            comm_hub=comm_hub,
            comm_transport=comm_transport,
            comm_transport_mode=comm_transport_mode,
            connect_timeout=connect_timeout,
            probe_entry=probe_entry,
            env=env,
            config_path=config_path,
            clusters_dir=clusters_dir,
        )


@dataclass
class V1Session:
    owner: str
    mode: str
    client: V1RuntimeClient
    runtime_host: V1RuntimeHost
    bootstrap: V1BootstrapHandle | None
    cluster_name: str | None
    resolved_entry_node: str | None
    resolved_by: str
    metadata: dict[str, Any] = field(default_factory=dict)
    local_node_runtime: Any | None = None
    owns_runtime_host: bool = True
    _closed: bool = field(default=False, init=False, repr=False)
    _scope_cm: Any | None = field(default=None, init=False, repr=False)
    _config_key: tuple[Any, ...] = field(default_factory=tuple, init=False, repr=False)
    _inspector: V1RuntimeInspector | None = field(default=None, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __enter__(self) -> V1Session:
        with self._lock:
            if self._closed:
                raise RuntimeError("flownet_session_closed")
            if self._scope_cm is None:
                scope_cm = client_scope(self.client)
                scope_cm.__enter__()
                self._scope_cm = scope_cm
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self._exit_scope(exc_type=exc_type, exc=exc, tb=tb)
        close_session(expected=self)
        return False

    @property
    def is_closed(self) -> bool:
        with self._lock:
            return self._closed

    @property
    def flows(self) -> Any:
        self._ensure_open()
        return self.client.flows

    @property
    def actors(self) -> Any:
        self._ensure_open()
        return self.client.actors

    @property
    def stateless(self) -> Any:
        self._ensure_open()
        return self.client.stateless

    @property
    def sources(self) -> Any:
        self._ensure_open()
        return self.client.sources

    @property
    def services(self) -> Any:
        self._ensure_open()
        return self.client.services

    @property
    def processes(self) -> Any:
        self._ensure_open()
        return self.client.processes

    @property
    def producers(self) -> Any:
        self._ensure_open()
        return self.client.producers

    def submit_flow_program(
        self,
        flow_uri: str,
        *,
        version: str | None = None,
        bindings: Mapping[str, Any] | None = None,
        ingress: Any = None,
        egress: Any = None,
        run_config: Mapping[str, Any] | None = None,
        node_address: str | None = None,
    ) -> dict[str, Any]:
        inspector = self._runtime_inspector()
        return inspector.submit_flow_program(
            flow_uri,
            version=version,
            bindings=dict(bindings) if bindings is not None else None,
            ingress=ingress,
            egress=egress,
            run_config=dict(run_config) if run_config is not None else None,
            node_address=node_address,
        )

    def lookup_flow_run_descriptor(
        self,
        run_id: str,
        *,
        node_address: str | None = None,
    ) -> Any:
        return self._runtime_inspector().lookup_flow_run_descriptor(
            run_id,
            node_address=node_address,
        )

    def cancel_flow_run(
        self,
        run_id: str,
        *,
        node_address: str | None = None,
    ) -> bool:
        return bool(
            self._runtime_inspector().cancel_flow_run(
                run_id,
                node_address=node_address,
            )
        )

    def flow_run_request_delivery_status(
        self,
        run_id: str,
        request_id: str,
        *,
        node_address: str | None = None,
    ) -> Any:
        return self._runtime_inspector().flow_run_request_delivery_status(
            run_id,
            request_id,
            node_address=node_address,
        )

    def flow_run_read(
        self,
        run_id: str,
        *,
        request_id: str | None = None,
        timeout: float = 5.0,
        from_seq: int | None = None,
        node_address: str | None = None,
    ) -> dict[str, Any] | None:
        return self._runtime_inspector().flow_run_read(
            run_id,
            request_id=request_id,
            timeout=timeout,
            from_seq=from_seq,
            node_address=node_address,
        )

    def cluster_view_snapshot(
        self,
        *,
        schema: str = "v1",
        node_address: str | None = None,
    ) -> Any:
        return self._runtime_inspector().cluster_view_snapshot(
            schema=schema,
            node_address=node_address,
        )

    def cluster_gossip_stats(self, *, node_address: str | None = None) -> Any:
        return self._runtime_inspector().cluster_gossip_stats(
            node_address=node_address,
        )

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = False) -> bool:
        scope_cm = None
        with self._lock:
            if self._closed:
                return False
            self._closed = True
            scope_cm = self._scope_cm
            self._scope_cm = None
            self._inspector = None
        if scope_cm is not None:
            try:
                scope_cm.__exit__(None, None, None)
            except Exception:
                pass
        try:
            if self.bootstrap is not None:
                self.bootstrap.shutdown(wait=wait, cancel_futures=cancel_futures)
            elif self.owns_runtime_host:
                self.runtime_host.shutdown(wait=wait, cancel_futures=cancel_futures)
        finally:
            _clear_active_session_if_matches(self)
        return True

    def _exit_scope(self, *, exc_type: Any, exc: Any, tb: Any) -> None:
        scope_cm = None
        with self._lock:
            scope_cm = self._scope_cm
            self._scope_cm = None
        if scope_cm is not None:
            scope_cm.__exit__(exc_type, exc, tb)

    def _ensure_open(self) -> None:
        if self.is_closed:
            raise RuntimeError("flownet_session_closed")

    def _runtime_inspector(self) -> V1RuntimeInspector:
        self._ensure_open()
        with self._lock:
            if self._inspector is not None:
                return self._inspector
            node_control_call = self._resolve_node_control_call_locked()
            inspector = build_runtime_inspector(
                runtime_host=self.runtime_host,
                node_control_call=node_control_call,
                default_node_address=self.resolved_entry_node,
            )
            self._inspector = inspector
            return inspector

    def _resolve_node_control_call_locked(self):
        bootstrap = self.bootstrap
        if bootstrap is not None:
            node_control_call = getattr(bootstrap, "node_control_call", None)
            if callable(node_control_call):
                return node_control_call
        default_node_control_call = resolve_default_node_control_caller()
        if callable(default_node_control_call):
            return default_node_control_call
        return build_http_node_control_caller(
            timeout_s=_DEFAULT_SESSION_NODE_CONTROL_TIMEOUT,
        )


def start_local_cluster(
    *,
    owner: str = "local-owner",
    node_id: str | None = None,
    bind_address: str | None = None,
    local_address: str | None = None,
    seeds: Iterable[str] | str | None = None,
    metadata: Mapping[str, Any] | None = None,
    join_timeout: float = 3.0,
    gossip_interval: float = 1.0,
    offline_timeout: float = 8.0,
    http_timeout: float = 2.0,
    comm_hub: V1CommHub | None = None,
    comm_transport: V1TransportBackend | None = None,
    comm_transport_mode: str | None = None,
) -> LocalClusterHandle:
    normalized_owner = _normalize_non_empty(owner, field_name="owner")
    resolved_bind_address = _normalize_entry_node_address(
        bind_address or _DEFAULT_LOCAL_RUNTIME_ENTRY_NODE,
        field_name="bind_address",
    )
    resolved_node_id = _normalize_optional_non_empty(node_id) or _build_local_node_id(
        normalized_owner
    )
    bootstrap = bootstrap_node_runtime(
        node_id=resolved_node_id,
        bind_address=resolved_bind_address,
        seeds=seeds,
        metadata=metadata,
        join_timeout=join_timeout,
        gossip_interval=gossip_interval,
        offline_timeout=offline_timeout,
        http_timeout=http_timeout,
        local_address=local_address,
        comm_hub=comm_hub,
        comm_transport=comm_transport,
        comm_transport_mode=comm_transport_mode,
    )
    return LocalClusterHandle(
        bootstrap=bootstrap,
        entry_node=resolved_bind_address,
        node_id=resolved_node_id,
    )


def connect(
    *,
    owner: str = "local-owner",
    entry_node: str | None = None,
    node_address: str | None = None,
    cluster: str | LocalClusterHandle | Any | None = None,
    local_address: str | None = None,
    mode: str = "connect",
    runtime_host: V1RuntimeHost | None = None,
    owns_runtime_host: bool = False,
    comm_hub: V1CommHub | None = None,
    comm_transport: V1TransportBackend | None = None,
    comm_transport_mode: str | None = None,
    connect_timeout: float | None = None,
    probe_entry: bool = True,
    env: Mapping[str, str] | None = None,
    config_path: str | os.PathLike[str] | None = None,
    clusters_dir: str | os.PathLike[str] | None = None,
) -> V1Session:
    normalized_owner = _normalize_non_empty(owner, field_name="owner")
    normalized_mode = _normalize_mode(mode)
    normalized_connect_timeout = _normalize_optional_non_negative_float(
        connect_timeout,
        field_name="connect_timeout",
    )
    resolved_local_address = _resolve_local_address(
        local_address=local_address,
        mode=normalized_mode,
    )
    normalized_cluster, cluster_entry_override = _normalize_cluster_target(cluster)

    if runtime_host is not None and (
        comm_hub is not None or comm_transport is not None or comm_transport_mode is not None
    ):
        raise ValueError(
            "connect runtime_host mode does not accept comm_hub/comm_transport/comm_transport_mode.",
        )

    resolved_context = resolve_cluster_context(
        mode=normalized_mode,
        entry_node=entry_node if entry_node is not None else cluster_entry_override,
        node_address=node_address,
        cluster=normalized_cluster,
        env=env,
        config_path=config_path,
        clusters_dir=clusters_dir,
        default_local_entry_node=_DEFAULT_LOCAL_RUNTIME_ENTRY_NODE,
        transport_mode=comm_transport_mode,
        connect_timeout=normalized_connect_timeout,
    )

    resolved_entry_node = resolved_context.resolved_entry_node
    requested_config_key = _build_config_key(
        owner=normalized_owner,
        mode=normalized_mode,
        local_address=resolved_local_address,
        cluster_name=resolved_context.cluster_name,
        resolved_entry_node=resolved_entry_node,
        resolved_by=resolved_context.resolved_by,
        transport_mode=resolved_context.transport_mode,
        connect_timeout=normalized_connect_timeout,
        runtime_host_ref_key=(
            ("provided", id(runtime_host)) if runtime_host is not None else ("managed", None)
        ),
        owns_runtime_host=(bool(owns_runtime_host) if runtime_host is not None else True),
    )
    existing = _get_existing_session_or_raise(requested_config_key)
    if existing is not None:
        return existing

    if runtime_host is not None:
        bootstrap = None
        client = build_runtime_client(owner=normalized_owner, runtime_host=runtime_host)
        session = V1Session(
            owner=normalized_owner,
            mode=normalized_mode,
            client=client,
            runtime_host=runtime_host,
            bootstrap=bootstrap,
            cluster_name=resolved_context.cluster_name,
            resolved_entry_node=resolved_entry_node,
            resolved_by=resolved_context.resolved_by,
            metadata=dict(resolved_context.metadata),
            local_node_runtime=None,
            owns_runtime_host=bool(owns_runtime_host),
        )
    elif normalized_mode == "local_runtime":
        local_node_id = _build_local_node_id(normalized_owner)
        if resolved_entry_node is None:
            raise RuntimeError(
                "cluster_target_unresolved: local_runtime requires resolvable entry node."
            )
        bootstrap = bootstrap_node_runtime(
            node_id=local_node_id,
            bind_address=resolved_entry_node,
            local_address=resolved_local_address,
            join_timeout=normalized_connect_timeout or 3.0,
            comm_hub=comm_hub,
            comm_transport=comm_transport,
            comm_transport_mode=comm_transport_mode,
        )
        runtime_host = bootstrap.runtime_host
        client = build_runtime_client(owner=normalized_owner, runtime_host=runtime_host)
        session = V1Session(
            owner=normalized_owner,
            mode=normalized_mode,
            client=client,
            runtime_host=runtime_host,
            bootstrap=bootstrap,
            cluster_name=resolved_context.cluster_name,
            resolved_entry_node=resolved_entry_node,
            resolved_by=resolved_context.resolved_by,
            metadata=dict(resolved_context.metadata),
            local_node_runtime=bootstrap.node_runtime,
            owns_runtime_host=True,
        )
    else:
        if resolved_entry_node is None:
            raise RuntimeError(
                "cluster_target_unresolved:"
                " connect mode requires resolvable entry_node or cluster target.",
            )
        if probe_entry:
            _probe_entry_node(
                entry_node=resolved_entry_node,
                timeout_s=normalized_connect_timeout or _DEFAULT_CONNECT_PROBE_TIMEOUT,
            )
        bootstrap = bootstrap_runtime(
            local_address=resolved_local_address,
            node_mode="connect_only",
            node_address=resolved_entry_node,
            connect_timeout=normalized_connect_timeout,
            comm_hub=comm_hub,
            comm_transport=comm_transport,
            comm_transport_mode=comm_transport_mode,
        )
        runtime_host = bootstrap.runtime_host
        client = build_runtime_client(owner=normalized_owner, runtime_host=runtime_host)
        session = V1Session(
            owner=normalized_owner,
            mode=normalized_mode,
            client=client,
            runtime_host=runtime_host,
            bootstrap=bootstrap,
            cluster_name=resolved_context.cluster_name,
            resolved_entry_node=resolved_entry_node,
            resolved_by=resolved_context.resolved_by,
            metadata=dict(resolved_context.metadata),
            local_node_runtime=None,
            owns_runtime_host=True,
        )

    session._config_key = requested_config_key
    return _register_or_reuse_session(session)


def init_local(
    *,
    owner: str = "local-owner",
    entry_node: str | None = None,
    local_address: str | None = None,
    comm_hub: V1CommHub | None = None,
    comm_transport: V1TransportBackend | None = None,
    comm_transport_mode: str | None = None,
    connect_timeout: float | None = None,
) -> V1Session:
    return connect(
        owner=owner,
        entry_node=entry_node,
        local_address=local_address,
        mode="local_runtime",
        comm_hub=comm_hub,
        comm_transport=comm_transport,
        comm_transport_mode=comm_transport_mode,
        connect_timeout=connect_timeout,
        probe_entry=False,
    )


def open_session(**kwargs: Any) -> V1Session:
    return connect(**kwargs)


def get_session() -> V1Session | None:
    with _SESSION_LOCK:
        session = _ACTIVE_SESSION
        if session is not None and session.is_closed:
            _set_active_session(None)
            return None
        return session


def require_session() -> V1Session:
    session = get_session()
    if session is None:
        raise RuntimeError(
            "flownet_session_required: call flownet.connect(...) or flownet.init_local(...)."
        )
    return session


def close_session(*, expected: V1Session | None = None) -> bool:
    with _SESSION_LOCK:
        session = _ACTIVE_SESSION
        if session is None:
            return False
        if expected is not None and session is not expected:
            return False
        _set_active_session(None)
    session.shutdown()
    return True


def _register_or_reuse_session(candidate: V1Session) -> V1Session:
    with _SESSION_LOCK:
        existing = _ACTIVE_SESSION
        if existing is not None and not existing.is_closed:
            if existing._config_key == candidate._config_key:
                candidate.shutdown()
                return existing
            candidate.shutdown()
            raise RuntimeError(
                "session_already_open:"
                f" existing_mode={existing.mode},existing_owner={existing.owner},"
                f" requested_mode={candidate.mode},requested_owner={candidate.owner}",
            )
        _set_active_session(candidate)
        _ensure_atexit_registered()
        return candidate


def _get_existing_session_or_raise(config_key: tuple[Any, ...]) -> V1Session | None:
    with _SESSION_LOCK:
        existing = _ACTIVE_SESSION
        if existing is None or existing.is_closed:
            return None
        if existing._config_key == config_key:
            return existing
        raise RuntimeError(
            f"session_already_open: existing_mode={existing.mode},existing_owner={existing.owner}",
        )


def _clear_active_session_if_matches(session: V1Session) -> None:
    with _SESSION_LOCK:
        if _ACTIVE_SESSION is session:
            _set_active_session(None)


def _set_active_session(session: V1Session | None) -> None:
    global _ACTIVE_SESSION
    _ACTIVE_SESSION = session


def _ensure_atexit_registered() -> None:
    global _ATEXIT_REGISTERED
    if _ATEXIT_REGISTERED:
        return
    atexit.register(_close_session_best_effort)
    _ATEXIT_REGISTERED = True


def _close_session_best_effort() -> None:
    try:
        close_session()
    except Exception:
        return


def _build_local_node_id(owner: str) -> str:
    normalized_owner = "".join(
        char if (char.isalnum() or char in "._-") else "-" for char in owner
    ).strip("-.")
    if not normalized_owner:
        normalized_owner = "local-owner"
    return f"local-{normalized_owner}-{os.getpid()}"


def _probe_entry_node(*, entry_node: str, timeout_s: float) -> None:
    normalized_timeout = (
        _normalize_optional_non_negative_float(
            timeout_s,
            field_name="timeout_s",
        )
        or _DEFAULT_CONNECT_PROBE_TIMEOUT
    )
    caller = build_http_node_control_caller(timeout_s=normalized_timeout)
    try:
        caller("cluster_view_snapshot", schema="v1", node_address=entry_node)
    except Exception as exc:
        raise RuntimeError(
            f"cluster_entry_unreachable: entry_node={entry_node} detail={exc}",
        ) from exc


def _normalize_mode(raw_mode: str | None) -> str:
    token = _normalize_optional_non_empty(raw_mode) or "connect"
    lowered = token.lower()
    if lowered in {"connect", "remote"}:
        return "connect"
    if lowered in {"local_runtime", "local_backend", "local"}:
        return "local_runtime"
    raise ValueError("mode must be one of: connect, local_runtime, local_backend, local.")


def _resolve_local_address(*, local_address: str | None, mode: str) -> str:
    if _normalize_optional_non_empty(local_address) is not None:
        return _normalize_address(local_address, field_name="local_address")
    if mode == "local_runtime":
        return _DEFAULT_LOCAL_RUNTIME_LOCAL_ADDRESS
    return _DEFAULT_CONNECT_LOCAL_ADDRESS


def _normalize_cluster_target(cluster: Any) -> tuple[str | None, str | None]:
    if cluster is None:
        return None, None
    if isinstance(cluster, str):
        return cluster, None
    cluster_entry = _normalize_optional_non_empty(getattr(cluster, "entry_node", None))
    if cluster_entry is None:
        raise TypeError("cluster must be a profile name (str) or a cluster handle with entry_node.")
    return None, _normalize_entry_node_address(cluster_entry, field_name="cluster.entry_node")


def _normalize_entry_node_address(raw_value: Any, *, field_name: str) -> str:
    normalized = _normalize_optional_non_empty(raw_value)
    if normalized is None:
        raise ValueError(f"{field_name} must be non-empty.")
    if ":" in normalized:
        return normalized
    return f"{normalized}:18787"


def _build_config_key(
    *,
    owner: str,
    mode: str,
    local_address: str,
    cluster_name: str | None,
    resolved_entry_node: str | None,
    resolved_by: str,
    transport_mode: str | None,
    connect_timeout: float | None,
    runtime_host_ref_key: tuple[str, int | None],
    owns_runtime_host: bool,
) -> tuple[Any, ...]:
    return (
        owner,
        mode,
        local_address,
        cluster_name,
        resolved_entry_node,
        resolved_by,
        transport_mode,
        connect_timeout,
        runtime_host_ref_key,
        bool(owns_runtime_host),
    )


def _normalize_address(raw_value: Any, *, field_name: str) -> str:
    normalized = _normalize_optional_non_empty(raw_value)
    if normalized is None:
        raise ValueError(f"{field_name} must be non-empty.")
    if ":" in normalized:
        return normalized
    return f"{normalized}:9920"


def _normalize_non_empty(raw_value: Any, *, field_name: str) -> str:
    normalized = _normalize_optional_non_empty(raw_value)
    if normalized is None:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _normalize_optional_non_empty(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    return normalized or None


def _normalize_optional_non_negative_float(raw_value: Any, *, field_name: str) -> float | None:
    if raw_value is None:
        return None
    normalized = float(raw_value)
    if normalized < 0:
        raise ValueError(f"{field_name} must be >= 0 when provided.")
    return normalized


__all__ = [
    "LocalClusterHandle",
    "V1Session",
    "close_session",
    "connect",
    "get_session",
    "init_local",
    "open_session",
    "require_session",
    "start_local_cluster",
]
