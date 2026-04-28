from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from sage.runtime.flownet.contracts.flow_program_submit_contract import (
    prepare_flow_program_submit_inputs,
)
from sage.runtime.flownet.contracts.flow_run_observation_contract import (
    normalize_flow_run_read_item,
    normalize_flow_run_request_delivery_status,
)
from sage.runtime.flownet.contracts.runtime_telemetry_contract import (
    RUNTIME_TELEMETRY_SCHEMA_VERSION,
    normalize_runtime_scheduler_telemetry,
    normalize_runtime_stream_tracker_summary,
)
from sage.runtime.flownet.runtime import V1RuntimeHost

NodeControlCaller = Callable[..., Any]

_DEFAULT_NODE_PORT = 8787
_DEFAULT_HTTP_TIMEOUT_S = 2.0
_DEFAULT_GOSSIP_INTERVAL_S = 1.0
_DEFAULT_JOIN_TIMEOUT_S = 3.0
_DEFAULT_OFFLINE_TIMEOUT_S = 8.0
_ENV_NODE_SEEDS = "FLOWNET_NODE_SEEDS"
_MAX_BOUNDED_ERROR_COUNT = 1_000_000
_FLOW_RUN_EVENT_BUFFER_PER_REQUEST = 1024
_FLOW_RUN_READ_POLL_INTERVAL_S = 0.02
_RUNTIME_STATE_QUERY_WINDOW_MS = 60_000
_RUNTIME_STATE_QUERY_MAX_PER_WINDOW = 120
_RUNTIME_STATE_QUERY_DEFAULT_LIMIT = 100
_RUNTIME_STATE_QUERY_MAX_LIMIT = 1_000
_RUNTIME_STATE_QUERY_REDACTED_PLACEHOLDER = "<redacted>"
_RUNTIME_STATE_QUERY_REVEAL_PERMISSION = "runtime_state.reveal_values"

_DEFAULT_NODE_CONTROL_CALLER_LOCK = threading.Lock()
_DEFAULT_NODE_CONTROL_CALLER: NodeControlCaller | None = None


def set_default_node_control_caller(caller: NodeControlCaller | None) -> None:
    global _DEFAULT_NODE_CONTROL_CALLER
    with _DEFAULT_NODE_CONTROL_CALLER_LOCK:
        _DEFAULT_NODE_CONTROL_CALLER = caller


def clear_default_node_control_caller(caller: NodeControlCaller | None = None) -> None:
    global _DEFAULT_NODE_CONTROL_CALLER
    with _DEFAULT_NODE_CONTROL_CALLER_LOCK:
        if caller is None or _DEFAULT_NODE_CONTROL_CALLER is caller:
            _DEFAULT_NODE_CONTROL_CALLER = None


def resolve_default_node_control_caller() -> NodeControlCaller | None:
    with _DEFAULT_NODE_CONTROL_CALLER_LOCK:
        return _DEFAULT_NODE_CONTROL_CALLER


def build_http_node_control_caller(
    *,
    timeout_s: float = _DEFAULT_HTTP_TIMEOUT_S,
    local_address: str | None = None,
    local_invoke: Callable[[str, tuple[Any, ...], dict[str, Any]], Any] | None = None,
) -> NodeControlCaller:
    normalized_timeout_s = _normalize_positive_float(timeout_s, field_name="timeout_s")
    normalized_local_address = _normalize_optional_node_address(local_address)

    def _call(op: str, *args: Any, node_address: str | None = None, **kwargs: Any) -> Any:
        normalized_op = _normalize_non_empty(op, field_name="op")
        resolved_node_address = _normalize_optional_node_address(node_address)
        if (
            local_invoke is not None
            and normalized_local_address is not None
            and resolved_node_address in {None, normalized_local_address}
        ):
            return local_invoke(normalized_op, args, kwargs)
        if resolved_node_address is None:
            raise ValueError(
                "node_address is required when local node-control invoke is not configured."
            )
        payload = {
            "op": normalized_op,
            "args": list(args),
            "kwargs": dict(kwargs),
        }
        response_payload = _http_post_json(
            resolved_node_address,
            path="/node-control",
            payload=payload,
            timeout_s=normalized_timeout_s,
        )
        if not isinstance(response_payload, Mapping):
            raise RuntimeError("node_control_response_must_be_mapping")
        if not bool(response_payload.get("ok")):
            error_payload = response_payload.get("error")
            if isinstance(error_payload, Mapping):
                code = str(error_payload.get("code") or "node_control_remote_error")
                message = str(error_payload.get("message") or "node_control_remote_error")
                raise RuntimeError(f"{code}:{message}")
            raise RuntimeError("node_control_remote_error")
        return response_payload.get("result")

    return _call


@dataclass(frozen=True)
class V1MembershipNode:
    node_id: str
    address: str
    incarnation: str
    health: str
    last_seen_ms: int
    clock_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "address": self.address,
            "incarnation": self.incarnation,
            "health": self.health,
            "last_seen_ms": int(self.last_seen_ms),
            "clock_ms": int(self.clock_ms),
            "metadata": dict(self.metadata),
        }


class V1NodeRuntimeService:
    """
    Minimal node membership runtime for seed-join + gossip + inspect.

    Design goals:
    - Keep protocol simple and explicit (HTTP+JSON over node bind address).
    - Maintain eventually-consistent membership with periodic gossip snapshots.
    - Expose node-control style inspect operations used by `V1RuntimeInspector`.
    """

    def __init__(
        self,
        *,
        runtime_host: V1RuntimeHost,
        node_id: str,
        node_address: str,
        seed_addresses: list[str] | tuple[str, ...] | set[str] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
        join_timeout_s: float = _DEFAULT_JOIN_TIMEOUT_S,
        gossip_interval_s: float = _DEFAULT_GOSSIP_INTERVAL_S,
        offline_timeout_s: float = _DEFAULT_OFFLINE_TIMEOUT_S,
        http_timeout_s: float = _DEFAULT_HTTP_TIMEOUT_S,
        state_backend: str = "memory",
        state_sqlite_path: str | None = None,
    ) -> None:
        self._runtime_host = runtime_host
        self._node_id = _normalize_non_empty(node_id, field_name="node_id")
        self._node_address = _normalize_node_address(node_address)
        self._seed_addresses = tuple(
            addr for addr in resolve_seed_addresses(seed_addresses) if addr != self._node_address
        )
        self._metadata = dict(metadata or {})
        self._join_timeout_s = _normalize_positive_float(
            join_timeout_s,
            field_name="join_timeout_s",
        )
        self._gossip_interval_s = _normalize_positive_float(
            gossip_interval_s,
            field_name="gossip_interval_s",
        )
        self._offline_timeout_s = _normalize_positive_float(
            offline_timeout_s,
            field_name="offline_timeout_s",
        )
        self._http_timeout_s = _normalize_positive_float(
            http_timeout_s,
            field_name="http_timeout_s",
        )
        self._state_backend = str(state_backend or "memory").strip().lower() or "memory"
        self._state_sqlite_path = _normalize_optional_non_empty(state_sqlite_path)
        self._incarnation = uuid.uuid4().hex
        self._view_epoch = 0
        now_ms = _now_ms()
        self._members: dict[str, V1MembershipNode] = {
            self._node_id: V1MembershipNode(
                node_id=self._node_id,
                address=self._node_address,
                incarnation=self._incarnation,
                health="healthy",
                last_seen_ms=now_ms,
                clock_ms=now_ms,
                metadata=dict(self._metadata),
            )
        }
        self._stats: dict[str, Any] = {
            "join_attempt_total": 0,
            "join_success_total": 0,
            "join_failure_total": 0,
            "gossip_sent_total": 0,
            "gossip_send_error_total": 0,
            "gossip_recv_total": 0,
            "gossip_malformed_total": 0,
            "gossip_transport_error_total": 0,
            "gossip_merge_added_total": 0,
            "gossip_merge_updated_total": 0,
            "gossip_merge_ignored_total": 0,
            "membership_conflict_total": 0,
            "offline_mark_total": 0,
            "rejoin_total": 0,
            "leave_soft_total": 0,
            "leave_hard_total": 0,
            "leave_notify_attempt_total": 0,
            "leave_notify_success_total": 0,
            "leave_notify_error_total": 0,
            "leave_notify_skipped_total": 0,
            "last_leave_mode": None,
            "last_leave_ms": None,
            "last_gossip_sent_ms": None,
            "last_gossip_recv_ms": None,
            "last_error": None,
            "runtime_state_query_total": 0,
            "runtime_state_query_denied_total": 0,
            "runtime_state_query_rate_limited_total": 0,
            "last_runtime_state_query_ms": None,
        }
        self._runtime_state_query_windows: dict[str, deque[int]] = {}
        self._runtime_state_query_audit: deque[dict[str, Any]] = deque(maxlen=2048)
        self._lock = threading.RLock()
        self._http_server: ThreadingHTTPServer | None = None
        self._http_server_thread: threading.Thread | None = None
        self._gossip_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._started = False

        self._node_control_service = _V1NodeControlService(
            runtime_host=runtime_host,
            membership=self,
        )
        self._node_control_call = build_http_node_control_caller(
            timeout_s=self._http_timeout_s,
            local_address=self._node_address,
            local_invoke=lambda op, args, kwargs: self._node_control_service.invoke(
                op, *args, **kwargs
            ),
        )
        self._cluster_backend_router = _RuntimeNodeControlClusterBackendRouter(
            node_control_call=self._node_control_call,
            default_node_address=self._node_address,
        )
        configure_cluster_backend_router = getattr(
            self._runtime_host,
            "configure_cluster_backend_router",
            None,
        )
        if callable(configure_cluster_backend_router):
            configure_cluster_backend_router(self._cluster_backend_router)
        self._configure_state_runtime_backend()

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def node_address(self) -> str:
        return self._node_address

    @property
    def seed_addresses(self) -> tuple[str, ...]:
        return self._seed_addresses

    @property
    def node_control_call(self) -> NodeControlCaller:
        return self._node_control_call

    def _configure_state_runtime_backend(self) -> None:
        if (
            self._state_backend in {"memory", "in-memory", "mem"}
            and self._state_sqlite_path is None
        ):
            return

        flow_process_execution = getattr(self._runtime_host, "_flow_process_execution", None)
        flow_engine = getattr(flow_process_execution, "_flow_engine", None)
        if flow_engine is None:
            if self._state_backend in {"memory", "in-memory", "mem"}:
                return
            raise RuntimeError("state_backend_requires_flow_engine")

        from sage.runtime.flownet.runtime.flowengine import StatefulProcessRuntime

        existing_state_runtime = getattr(flow_engine, "_state_runtime", None)
        replacement_state_runtime = StatefulProcessRuntime(
            backend=self._state_backend,
            sqlite_path=self._state_sqlite_path,
        )
        flow_engine._state_runtime = replacement_state_runtime
        if existing_state_runtime is replacement_state_runtime:
            return
        close_existing = getattr(existing_state_runtime, "close", None)
        if callable(close_existing):
            try:
                close_existing()
            except Exception:
                pass

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._stop_event.clear()
            self._start_http_server_locked()
            self._started = True
        try:
            self._bootstrap_join()
        except Exception:
            self.stop()
            raise
        set_default_node_control_caller(self._node_control_call)
        self._start_gossip_thread()

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return
            self._started = False
            self._stop_event.set()
            http_server = self._http_server
            self._http_server = None
            http_server_thread = self._http_server_thread
            self._http_server_thread = None
            gossip_thread = self._gossip_thread
            self._gossip_thread = None

        clear_default_node_control_caller(self._node_control_call)
        clear_cluster_backend_router = getattr(
            self._runtime_host,
            "clear_cluster_backend_router",
            None,
        )
        if callable(clear_cluster_backend_router):
            try:
                clear_cluster_backend_router()
            except Exception:
                pass

        if http_server is not None:
            try:
                http_server.shutdown()
            except Exception:
                pass
            try:
                http_server.server_close()
            except Exception:
                pass

        if http_server_thread is not None and http_server_thread.is_alive():
            http_server_thread.join(timeout=1.0)
        if gossip_thread is not None and gossip_thread.is_alive():
            gossip_thread.join(timeout=1.0)

    def list_runtime_nodes(self) -> list[dict[str, Any]]:
        with self._lock:
            nodes = sorted(self._members.values(), key=lambda item: item.node_id)
        result: list[dict[str, Any]] = []
        for node in nodes:
            row = node.as_dict()
            row["healthy"] = row["health"] == "healthy"
            result.append(row)
        return result

    def cluster_view_snapshot(self, *, schema: str = "v1") -> dict[str, Any]:
        normalized_schema = str(schema or "").strip().lower() or "v1"
        if normalized_schema != "v1":
            raise ValueError(f"unsupported_cluster_view_schema:{schema}")
        with self._lock:
            nodes = sorted(self._members.values(), key=lambda item: item.node_id)
            view_epoch = int(self._view_epoch)
        healthy_count = sum(1 for node in nodes if node.health == "healthy")
        return {
            "schema_version": "v1",
            "generated_at": time.time(),
            "view_epoch": view_epoch,
            "local_node_id": self._node_id,
            "health_summary": {
                "healthy": healthy_count,
                "degraded": max(0, len(nodes) - healthy_count),
                "total": len(nodes),
            },
            "nodes": [
                {
                    **node.as_dict(),
                    "healthy": node.health == "healthy",
                }
                for node in nodes
            ],
        }

    def cluster_gossip_stats(self) -> dict[str, Any]:
        with self._lock:
            stats = dict(self._stats)
            membership_entries = len(self._members)
        sender = {
            "sent_total": int(stats.get("gossip_sent_total", 0)),
            "send_error_total": int(stats.get("gossip_send_error_total", 0)),
            "last_sent_ms": stats.get("last_gossip_sent_ms"),
        }
        received = {
            "received_total": int(stats.get("gossip_recv_total", 0)),
            "malformed_total": int(stats.get("gossip_malformed_total", 0)),
            "transport_error_total": int(stats.get("gossip_transport_error_total", 0)),
            "merge_added_total": int(stats.get("gossip_merge_added_total", 0)),
            "merge_updated_total": int(stats.get("gossip_merge_updated_total", 0)),
            "merge_ignored_total": int(stats.get("gossip_merge_ignored_total", 0)),
            "last_recv_ms": stats.get("last_gossip_recv_ms"),
        }
        return {
            "sender": sender,
            "received": received,
            "join": {
                "attempt_total": int(stats.get("join_attempt_total", 0)),
                "success_total": int(stats.get("join_success_total", 0)),
                "failure_total": int(stats.get("join_failure_total", 0)),
            },
            "membership": {
                "entries": membership_entries,
                "conflict_total": int(stats.get("membership_conflict_total", 0)),
                "offline_mark_total": int(stats.get("offline_mark_total", 0)),
                "rejoin_total": int(stats.get("rejoin_total", 0)),
                "leave": self._leave_counters_from_stats(stats),
            },
            "last_error": stats.get("last_error"),
        }

    def cluster_contract_snapshot(self) -> dict[str, Any]:
        view = self.cluster_view_snapshot(schema="v1")
        stats = self.cluster_gossip_stats()
        return {
            "schema_version": "v1.cluster.contract",
            "generated_at": time.time(),
            "cluster_view": view,
            "crdt_profile": {
                "membership": {"type": "lww_map", "clock": "wallclock_ms"},
            },
            "gossip_defaults": {
                "join_timeout_s": self._join_timeout_s,
                "gossip_interval_s": self._gossip_interval_s,
                "offline_timeout_s": self._offline_timeout_s,
            },
            "peer_view": {
                "total": int(view["health_summary"]["total"]),
                "healthy": int(view["health_summary"]["healthy"]),
                "degraded": int(view["health_summary"]["degraded"]),
            },
            "gossip_stats": stats,
        }

    def list_runtime_topics(self) -> list[dict[str, Any]]:
        topic_api = getattr(self._runtime_host, "topic_api", None)
        routing_directory = getattr(topic_api, "routing_directory", None)
        raw_routes = getattr(routing_directory, "_routes", None)
        if not isinstance(raw_routes, dict):
            return []
        rows: list[dict[str, Any]] = []
        for route in raw_routes.values():
            topic_uri = str(getattr(route, "topic_uri", "")).strip()
            coordinator_address = str(getattr(route, "coordinator_address", "")).strip()
            epoch = int(getattr(route, "epoch", 0))
            if not topic_uri:
                continue
            rows.append(
                {
                    "topic_uri": topic_uri,
                    "coordinator_address": coordinator_address,
                    "epoch": epoch,
                }
            )
        rows.sort(key=lambda item: (item["topic_uri"], item["epoch"]))
        return rows

    def list_runtime_actors(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        actor_records = self._runtime_host.actor_api.list_local_actors()
        for record in actor_records:
            actor_id = str(getattr(record, "actor_id", "")).strip()
            if not actor_id:
                continue
            rows.append(
                {
                    "actor_id": actor_id,
                    "address": self._runtime_host.comm_hub.local_address,
                }
            )
        return rows

    def list_shared_state_services(self) -> list[dict[str, Any]]:
        registry = getattr(self._runtime_host, "shared_state_registry", None)
        snapshot = getattr(registry, "observability_snapshot", None)
        if not callable(snapshot):
            return []
        rows = snapshot()
        if not isinstance(rows, list):
            return []
        normalized_rows = [dict(row) for row in rows if isinstance(row, Mapping)]
        normalized_rows.sort(
            key=lambda item: (
                str(item.get("namespace") or ""),
                str(item.get("service_name") or ""),
                str(item.get("contract_id") or ""),
            )
        )
        return normalized_rows

    def list_published_endpoints(self) -> list[dict[str, Any]]:
        registry = getattr(self._runtime_host, "endpoint_registry", None)
        snapshot = getattr(registry, "observability_snapshot", None)
        if not callable(snapshot):
            return []
        rows = snapshot(include_released=True)
        if not isinstance(rows, list):
            return []
        normalized_rows = [dict(row) for row in rows if isinstance(row, Mapping)]
        normalized_rows.sort(
            key=lambda item: (
                str(item.get("namespace") or ""),
                str(item.get("name") or ""),
                str(item.get("version") or ""),
            )
        )
        return normalized_rows

    def list_collective_executors(self) -> list[dict[str, Any]]:
        snapshot = self._runtime_host.list_collective_executors()
        rows = snapshot.get("registrations", ()) if isinstance(snapshot, Mapping) else ()
        if not isinstance(rows, (list, tuple)):
            return []
        normalized_rows = [dict(row) for row in rows if isinstance(row, Mapping)]
        normalized_rows.sort(
            key=lambda item: (
                str(item.get("mode") or ""),
                str(item.get("executor_type") or ""),
            )
        )
        return normalized_rows

    def cluster_scheduler_metrics(self) -> dict[str, Any]:
        return _build_runtime_scheduler_telemetry(
            self._runtime_host,
            node_id=self._node_id,
            node_address=self._node_address,
        )

    def query_runtime_state(
        self,
        namespace: str,
        *,
        prefix: str,
        principal: str,
        roles: list[str] | None = None,
        allowed_namespaces: list[str] | None = None,
        permissions: list[str] | None = None,
        limit: int | None = None,
        cursor: int | str | None = None,
        include_values: bool = True,
        reveal_values: bool = False,
    ) -> dict[str, Any]:
        normalized_namespace = _normalize_non_empty(namespace, field_name="namespace")
        normalized_prefix = _normalize_non_empty(prefix, field_name="prefix")
        normalized_principal = _normalize_non_empty(principal, field_name="principal")
        normalized_roles = _normalize_optional_str_list(roles)
        normalized_allowed_namespaces = _normalize_optional_str_list(allowed_namespaces)
        normalized_permissions = _normalize_optional_str_list(permissions)
        normalized_cursor = (
            _normalize_non_negative_int(cursor, field_name="cursor") if cursor is not None else 0
        )
        normalized_limit = (
            _normalize_non_negative_int(limit, field_name="limit")
            if limit is not None
            else _RUNTIME_STATE_QUERY_DEFAULT_LIMIT
        )
        if normalized_limit <= 0:
            normalized_limit = _RUNTIME_STATE_QUERY_DEFAULT_LIMIT
        normalized_limit = min(normalized_limit, _RUNTIME_STATE_QUERY_MAX_LIMIT)

        include_values_flag = bool(include_values)
        reveal_values_flag = bool(reveal_values)

        now_ms = _now_ms()
        with self._lock:
            self._stats["runtime_state_query_total"] = (
                int(self._stats.get("runtime_state_query_total", 0)) + 1
            )
            self._stats["last_runtime_state_query_ms"] = now_ms

            if normalized_allowed_namespaces and not _namespace_acl_match(
                normalized_namespace,
                normalized_allowed_namespaces,
            ):
                self._stats["runtime_state_query_denied_total"] = (
                    int(self._stats.get("runtime_state_query_denied_total", 0)) + 1
                )
                self._record_runtime_state_query_audit_locked(
                    principal=normalized_principal,
                    namespace=normalized_namespace,
                    prefix=normalized_prefix,
                    limit=normalized_limit,
                    cursor=normalized_cursor,
                    allowed=False,
                    reason="namespace_forbidden",
                    reveal_values=reveal_values_flag,
                    result_count=0,
                )
                raise PermissionError(
                    f"runtime_state_query_namespace_forbidden:{normalized_namespace}"
                )

            if reveal_values_flag and not _has_runtime_state_permission(
                normalized_permissions,
                _RUNTIME_STATE_QUERY_REVEAL_PERMISSION,
            ):
                # Per Issue 1493: downgrade to masked response instead of hard rejection.
                # Caller can still see which keys exist, just not their values.
                # ("使调用方能判断状态存在但无法读取内容")
                reveal_values_flag = False
                self._record_runtime_state_query_audit_locked(
                    principal=normalized_principal,
                    namespace=normalized_namespace,
                    prefix=normalized_prefix,
                    limit=normalized_limit,
                    cursor=normalized_cursor,
                    allowed=False,
                    reason="reveal_values_permission_required",
                    reveal_values=True,
                    result_count=0,
                )
                # Note: do NOT increment runtime_state_query_denied_total;
                # the query is NOT rejected—it continues with masked values.

            if not self._runtime_state_query_allow_locked(
                principal=normalized_principal,
                now_ms=now_ms,
            ):
                self._stats["runtime_state_query_rate_limited_total"] = (
                    int(self._stats.get("runtime_state_query_rate_limited_total", 0)) + 1
                )
                self._record_runtime_state_query_audit_locked(
                    principal=normalized_principal,
                    namespace=normalized_namespace,
                    prefix=normalized_prefix,
                    limit=normalized_limit,
                    cursor=normalized_cursor,
                    allowed=False,
                    reason="rate_limited",
                    reveal_values=reveal_values_flag,
                    result_count=0,
                )
                raise RuntimeError("runtime_state_query_rate_limited")

        query_entries = self._resolve_runtime_state_query_entries()
        raw_items: list[dict[str, Any]] = []
        next_cursor: int | None = None
        if callable(query_entries):
            raw_items, next_cursor = query_entries(
                namespace=normalized_namespace,
                prefix=normalized_prefix,
                limit=normalized_limit,
                cursor=normalized_cursor,
            )

        items: list[dict[str, Any]] = []
        masked_values = False
        for row in raw_items:
            item: dict[str, Any] = {
                "key": str(row.get("key") or ""),
                "updated_at_ms": int(row.get("updated_at_ms") or 0),
            }
            value = row.get("value")
            if include_values_flag:
                if reveal_values_flag:
                    item["value"] = value
                else:
                    item["value"] = _mask_runtime_state_value(value)
                    masked_values = True
            items.append(item)

        with self._lock:
            self._record_runtime_state_query_audit_locked(
                principal=normalized_principal,
                namespace=normalized_namespace,
                prefix=normalized_prefix,
                limit=normalized_limit,
                cursor=normalized_cursor,
                allowed=True,
                reason="ok",
                reveal_values=reveal_values_flag,
                result_count=len(items),
            )

        return {
            "namespace": normalized_namespace,
            "prefix": normalized_prefix,
            "principal": normalized_principal,
            "roles": normalized_roles,
            "allowed_namespaces": normalized_allowed_namespaces,
            "permissions": normalized_permissions,
            "limit": normalized_limit,
            "cursor": normalized_cursor,
            "include_values": include_values_flag,
            "reveal_values": reveal_values_flag,
            "items": items,
            "next_cursor": next_cursor,
            "masked_values": masked_values,
        }

    def stream_tracker_stats(self) -> dict[str, Any]:
        return _runtime_stream_tracker_summary(self._runtime_host)

    def stream_tracker_request_status(self, request_id: str) -> dict[str, Any]:
        normalized_request_id = _normalize_non_empty(request_id, field_name="request_id")
        return {
            "request_ref_id": normalized_request_id,
            "status": "unknown",
            "pending": 0,
            "delivery_done": False,
        }

    def _leave_counters_from_stats(self, stats: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "soft_total": int(stats.get("leave_soft_total", 0)),
            "hard_total": int(stats.get("leave_hard_total", 0)),
            "notify_attempt_total": int(stats.get("leave_notify_attempt_total", 0)),
            "notify_success_total": int(stats.get("leave_notify_success_total", 0)),
            "notify_error_total": int(stats.get("leave_notify_error_total", 0)),
            "notify_skipped_total": int(stats.get("leave_notify_skipped_total", 0)),
            "last_mode": stats.get("last_leave_mode"),
            "last_leave_ms": stats.get("last_leave_ms"),
        }

    def _leave_counters_snapshot_locked(self) -> dict[str, Any]:
        return self._leave_counters_from_stats(self._stats)

    def _record_leave_locked(self, *, mode: str, at_ms: int) -> None:
        if mode == "soft":
            key = "leave_soft_total"
        else:
            key = "leave_hard_total"
        self._stats[key] = int(self._stats.get(key, 0)) + 1
        self._stats["last_leave_mode"] = mode
        self._stats["last_leave_ms"] = int(at_ms)

    def node_leave(self, *, mode: str = "soft") -> dict[str, Any]:
        normalized_mode = str(mode or "soft").strip().lower() or "soft"
        if normalized_mode not in {"soft", "hard"}:
            raise ValueError(f"unsupported leave mode: {mode!r}")
        stop_strategy = "graceful" if normalized_mode == "soft" else "fast"
        peer_notify_mode = "broadcast" if normalized_mode == "soft" else "skipped"

        with self._lock:
            if not self._started:
                leave_counters = self._leave_counters_snapshot_locked()
                return {
                    "ok": True,
                    "mode": normalized_mode,
                    "node_id": self._node_id,
                    "already_stopped": True,
                    "marked_offline": False,
                    "stop_strategy": stop_strategy,
                    "peer_notify_mode": peer_notify_mode,
                    "peer_notify_attempted": 0,
                    "peer_notify_succeeded": 0,
                    "peer_notify_failed": 0,
                    "notified_peers": [],
                    "notify_errors": [],
                    "leave_counters": leave_counters,
                }
            now_ms = _now_ms()
            current = self._members.get(self._node_id)
            if current is None:
                current = V1MembershipNode(
                    node_id=self._node_id,
                    address=self._node_address,
                    incarnation=self._incarnation,
                    health="healthy",
                    last_seen_ms=now_ms,
                    clock_ms=now_ms,
                    metadata=dict(self._metadata),
                )
            marked_offline = False
            if current.health != "offline":
                self._members[self._node_id] = replace(
                    current,
                    health="offline",
                    last_seen_ms=now_ms,
                    clock_ms=now_ms,
                )
                self._view_epoch += 1
                self._stats["offline_mark_total"] = (
                    int(self._stats.get("offline_mark_total", 0)) + 1
                )
                marked_offline = True
            self._record_leave_locked(mode=normalized_mode, at_ms=now_ms)
            if normalized_mode == "soft":
                snapshot = self.cluster_view_snapshot(schema="v1")
                peers = sorted(
                    {
                        node.address
                        for node in self._members.values()
                        if node.node_id != self._node_id and node.address
                    }
                )
                self._stats["leave_notify_attempt_total"] = int(
                    self._stats.get("leave_notify_attempt_total", 0)
                ) + len(peers)
            else:
                snapshot = None
                peers = []
                self._stats["leave_notify_skipped_total"] = (
                    int(self._stats.get("leave_notify_skipped_total", 0)) + 1
                )
            peer_notify_attempted = len(peers)

        notified_peers: list[str] = []
        notify_errors: list[str] = []
        if normalized_mode == "soft":
            assert snapshot is not None
            for peer in peers:
                try:
                    _http_post_json(
                        peer,
                        path="/gossip",
                        payload={
                            "from_node_id": self._node_id,
                            "from_address": self._node_address,
                            "from_incarnation": self._incarnation,
                            "from_health": "offline",
                            "snapshot": snapshot,
                        },
                        timeout_s=self._http_timeout_s,
                    )
                    notified_peers.append(peer)
                except Exception as exc:
                    notify_errors.append(f"{peer}:{exc}")

        with self._lock:
            self._stats["leave_notify_success_total"] = int(
                self._stats.get("leave_notify_success_total", 0)
            ) + len(notified_peers)
            self._stats["leave_notify_error_total"] = int(
                self._stats.get("leave_notify_error_total", 0)
            ) + len(notify_errors)
            leave_counters = self._leave_counters_snapshot_locked()

        self.stop()
        return {
            "ok": True,
            "mode": normalized_mode,
            "node_id": self._node_id,
            "already_stopped": False,
            "marked_offline": marked_offline,
            "stop_strategy": stop_strategy,
            "peer_notify_mode": peer_notify_mode,
            "peer_notify_attempted": peer_notify_attempted,
            "peer_notify_succeeded": len(notified_peers),
            "peer_notify_failed": len(notify_errors),
            "notified_peers": notified_peers,
            "notify_errors": notify_errors,
            "leave_counters": leave_counters,
        }

    def _start_http_server_locked(self) -> None:
        host, port = _split_host_port(self._node_address)
        handler_cls = self._build_http_handler()
        server = ThreadingHTTPServer((host, port), handler_cls)
        server.daemon_threads = True
        thread = threading.Thread(
            target=server.serve_forever,
            name=f"flownet-node-http:{self._node_id}",
            daemon=True,
        )
        self._http_server = server
        self._http_server_thread = thread
        thread.start()

    def _start_gossip_thread(self) -> None:
        thread = threading.Thread(
            target=self._gossip_loop,
            name=f"flownet-node-gossip:{self._node_id}",
            daemon=True,
        )
        self._gossip_thread = thread
        thread.start()

    def _build_http_handler(self) -> type[BaseHTTPRequestHandler]:
        service = self

        class _Handler(BaseHTTPRequestHandler):
            def _respond_json(
                self,
                *,
                status_code: int,
                payload: Mapping[str, Any],
                path: str,
            ) -> None:
                write_error = _try_write_json_response(
                    self,
                    status_code=status_code,
                    payload=payload,
                )
                if write_error is None:
                    return
                if path == "/gossip":
                    service._record_gossip_transport_error(
                        detail=f"path={path},write_error={write_error}",
                    )

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse.urlsplit(self.path)
                query = urlparse.parse_qs(parsed.query)
                try:
                    payload = service._handle_get(parsed.path, query)
                    self._respond_json(status_code=200, payload=payload, path=parsed.path)
                except Exception as exc:
                    self._respond_json(
                        status_code=500,
                        payload={
                            "ok": False,
                            "error": {
                                "code": "http_get_failed",
                                "type": exc.__class__.__name__,
                                "message": str(exc),
                            },
                        },
                        path=parsed.path,
                    )

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse.urlsplit(self.path)
                try:
                    payload = _read_json_request(self)
                    result = service._handle_post(parsed.path, payload)
                    self._respond_json(status_code=200, payload=result, path=parsed.path)
                except ValueError as exc:
                    error_code = "invalid_request"
                    if parsed.path == "/gossip":
                        service._record_gossip_malformed_request(detail=str(exc))
                        error_code = "invalid_gossip_payload"
                    self._respond_json(
                        status_code=400,
                        payload={
                            "ok": False,
                            "error": {
                                "code": error_code,
                                "type": exc.__class__.__name__,
                                "message": str(exc),
                            },
                        },
                        path=parsed.path,
                    )
                except Exception as exc:
                    self._respond_json(
                        status_code=500,
                        payload={
                            "ok": False,
                            "error": {
                                "code": "http_post_failed",
                                "type": exc.__class__.__name__,
                                "message": str(exc),
                            },
                        },
                        path=parsed.path,
                    )

            def log_message(self, _format: str, *_args: Any) -> None:
                return

        return _Handler

    def _handle_get(
        self,
        path: str,
        query: Mapping[str, list[str]],
    ) -> dict[str, Any]:
        normalized_path = str(path or "").strip()
        if normalized_path == "/healthz":
            return {
                "ok": True,
                "node_id": self._node_id,
                "address": self._node_address,
            }
        if normalized_path == "/membership":
            schema = "v1"
            if "schema" in query and query["schema"]:
                schema = str(query["schema"][-1] or "v1")
            return {
                "ok": True,
                "snapshot": self.cluster_view_snapshot(schema=schema),
            }
        if normalized_path == "/gossip-stats":
            return {
                "ok": True,
                "stats": self.cluster_gossip_stats(),
            }
        raise ValueError(f"unsupported_get_path:{normalized_path}")

    def _handle_post(self, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        normalized_path = str(path or "").strip()
        if normalized_path == "/join":
            return self._handle_join(payload)
        if normalized_path == "/gossip":
            return self._handle_gossip(payload)
        if normalized_path == "/node-control":
            return self._handle_node_control(payload)
        raise ValueError(f"unsupported_post_path:{normalized_path}")

    def _handle_join(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        incoming = _coerce_member_payload(payload)
        with self._lock:
            now_ms = _now_ms()
            self._touch_local_member_locked(now_ms)
            result = self._merge_member_locked(
                replace(incoming, last_seen_ms=now_ms, health="healthy"),
                source="join",
            )
            if result == "conflict":
                return {
                    "ok": False,
                    "error": {
                        "code": "node_conflict",
                        "message": (
                            f"address {incoming.address} already occupied by another healthy node"
                        ),
                    },
                    "snapshot": self.cluster_view_snapshot(schema="v1"),
                }
            snapshot = self.cluster_view_snapshot(schema="v1")
        return {
            "ok": True,
            "snapshot": snapshot,
        }

    def _handle_gossip(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        from_node_id = _normalize_non_empty(payload.get("from_node_id"), field_name="from_node_id")
        from_address = _normalize_node_address(
            payload.get("from_address") or payload.get("address")
        )
        from_incarnation = _normalize_non_empty(
            payload.get("from_incarnation"),
            field_name="from_incarnation",
        )
        from_health = str(payload.get("from_health") or "healthy").strip().lower() or "healthy"
        if from_health not in {"healthy", "offline"}:
            from_health = "healthy"
        raw_snapshot = payload.get("snapshot")
        with self._lock:
            now_ms = _now_ms()
            self._touch_local_member_locked(now_ms)
            self._stats["gossip_recv_total"] = int(self._stats.get("gossip_recv_total", 0)) + 1
            self._stats["last_gossip_recv_ms"] = now_ms
            self._mark_peer_alive_locked(
                node_id=from_node_id,
                address=from_address,
                incarnation=from_incarnation,
                health=from_health,
                seen_at_ms=now_ms,
            )
            if isinstance(raw_snapshot, Mapping):
                merge_stats = self._merge_snapshot_locked(
                    raw_snapshot, source=f"gossip:{from_node_id}"
                )
                self._stats["gossip_merge_added_total"] = int(
                    self._stats.get("gossip_merge_added_total", 0)
                ) + int(merge_stats["added"])
                self._stats["gossip_merge_updated_total"] = int(
                    self._stats.get("gossip_merge_updated_total", 0)
                ) + int(merge_stats["updated"])
                self._stats["gossip_merge_ignored_total"] = int(
                    self._stats.get("gossip_merge_ignored_total", 0)
                ) + int(merge_stats["ignored"])
            self._apply_offline_sweep_locked(now_ms)
            snapshot = self.cluster_view_snapshot(schema="v1")
        return {"ok": True, "snapshot": snapshot}

    def _handle_node_control(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        op = _normalize_non_empty(payload.get("op"), field_name="op")
        raw_args = payload.get("args")
        args: tuple[Any, ...]
        if raw_args is None:
            args = ()
        elif isinstance(raw_args, list):
            args = tuple(raw_args)
        else:
            raise ValueError("node_control args must be list when provided.")
        raw_kwargs = payload.get("kwargs")
        if raw_kwargs is None:
            kwargs: dict[str, Any] = {}
        elif isinstance(raw_kwargs, Mapping):
            kwargs = dict(raw_kwargs)
        else:
            raise ValueError("node_control kwargs must be mapping when provided.")
        try:
            result = self._node_control_service.invoke(op, *args, **kwargs)
            return {"ok": True, "result": result}
        except Exception as exc:
            return {
                "ok": False,
                "error": {
                    "code": "node_control_invoke_failed",
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            }

    def _bootstrap_join(self) -> None:
        if not self._seed_addresses:
            return
        failures: list[str] = []
        success_count = 0
        for seed in self._seed_addresses:
            deadline = time.monotonic() + self._join_timeout_s
            last_exc: Exception | None = None
            joined = False
            while True:
                with self._lock:
                    self._stats["join_attempt_total"] = (
                        int(self._stats.get("join_attempt_total", 0)) + 1
                    )
                try:
                    remaining_s = max(0.0, deadline - time.monotonic())
                    request_timeout_s = max(
                        0.1, min(self._http_timeout_s, remaining_s or self._join_timeout_s)
                    )
                    response = _http_post_json(
                        seed,
                        path="/join",
                        payload={
                            "node_id": self._node_id,
                            "address": self._node_address,
                            "incarnation": self._incarnation,
                            "health": "healthy",
                            "last_seen_ms": _now_ms(),
                            "clock_ms": _now_ms(),
                            "metadata": dict(self._metadata),
                        },
                        timeout_s=request_timeout_s,
                    )
                    if not isinstance(response, Mapping):
                        raise RuntimeError("join_response_must_be_mapping")
                    if not bool(response.get("ok")):
                        message = "seed_join_rejected"
                        error_payload = response.get("error")
                        if isinstance(error_payload, Mapping):
                            message = str(error_payload.get("message") or message)
                        raise RuntimeError(message)
                    snapshot = response.get("snapshot")
                    if isinstance(snapshot, Mapping):
                        with self._lock:
                            self._merge_snapshot_locked(snapshot, source=f"seed:{seed}")
                    success_count += 1
                    with self._lock:
                        self._stats["join_success_total"] = (
                            int(self._stats.get("join_success_total", 0)) + 1
                        )
                    joined = True
                    break
                except Exception as exc:
                    last_exc = exc
                    if time.monotonic() >= deadline:
                        break
                    time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))

            if joined:
                continue

            detail = str(last_exc) if last_exc is not None else "unknown"
            failures.append(f"{seed}:{detail}")
            with self._lock:
                self._stats["join_failure_total"] = (
                    int(self._stats.get("join_failure_total", 0)) + 1
                )
                self._stats["last_error"] = f"join_failed:{seed}:{detail}"
        if success_count <= 0:
            joined = ", ".join(self._seed_addresses)
            details = "; ".join(failures) if failures else "unknown"
            raise RuntimeError(f"seed_unreachable:seeds={joined}:details={details}")

    def _gossip_loop(self) -> None:
        while not self._stop_event.wait(self._gossip_interval_s):
            try:
                self._gossip_once()
            except Exception as exc:
                with self._lock:
                    self._stats["last_error"] = f"gossip_loop_error:{exc}"

    def _gossip_once(self) -> None:
        with self._lock:
            now_ms = _now_ms()
            self._touch_local_member_locked(now_ms)
            self._apply_offline_sweep_locked(now_ms)
            snapshot = self.cluster_view_snapshot(schema="v1")
            peers = [
                node.address for node in self._members.values() if node.node_id != self._node_id
            ]

        for peer in sorted(set(peers)):
            try:
                response = _http_post_json(
                    peer,
                    path="/gossip",
                    payload={
                        "from_node_id": self._node_id,
                        "from_address": self._node_address,
                        "from_incarnation": self._incarnation,
                        "from_health": "healthy",
                        "snapshot": snapshot,
                    },
                    timeout_s=self._http_timeout_s,
                )
                if isinstance(response, Mapping):
                    reply_snapshot = response.get("snapshot")
                    if isinstance(reply_snapshot, Mapping):
                        with self._lock:
                            self._merge_snapshot_locked(
                                reply_snapshot, source=f"gossip_reply:{peer}"
                            )
                with self._lock:
                    self._stats["gossip_sent_total"] = (
                        int(self._stats.get("gossip_sent_total", 0)) + 1
                    )
                    self._stats["last_gossip_sent_ms"] = _now_ms()
            except Exception as exc:
                with self._lock:
                    self._stats["gossip_send_error_total"] = (
                        int(self._stats.get("gossip_send_error_total", 0)) + 1
                    )
                    self._stats["last_error"] = f"gossip_send_failed:{peer}:{exc}"

    def _touch_local_member_locked(self, now_ms: int) -> None:
        local = self._members.get(self._node_id)
        if local is None:
            self._members[self._node_id] = V1MembershipNode(
                node_id=self._node_id,
                address=self._node_address,
                incarnation=self._incarnation,
                health="healthy",
                last_seen_ms=now_ms,
                clock_ms=now_ms,
                metadata=dict(self._metadata),
            )
            self._view_epoch += 1
            return
        next_clock = max(int(local.clock_ms) + 1, now_ms)
        self._members[self._node_id] = replace(
            local,
            address=self._node_address,
            health="healthy",
            last_seen_ms=now_ms,
            clock_ms=next_clock,
            metadata=dict(self._metadata),
        )

    def _mark_peer_alive_locked(
        self,
        *,
        node_id: str,
        address: str,
        incarnation: str,
        health: str = "healthy",
        seen_at_ms: int,
    ) -> None:
        normalized_health = str(health or "healthy").strip().lower() or "healthy"
        if normalized_health not in {"healthy", "offline"}:
            normalized_health = "healthy"
        incoming = V1MembershipNode(
            node_id=node_id,
            address=address,
            incarnation=incarnation,
            health=normalized_health,
            last_seen_ms=seen_at_ms,
            clock_ms=seen_at_ms,
            metadata={},
        )
        self._merge_member_locked(incoming, source="peer_seen")

    def _merge_snapshot_locked(
        self,
        snapshot: Mapping[str, Any],
        *,
        source: str,
    ) -> dict[str, int]:
        raw_nodes = snapshot.get("nodes")
        if not isinstance(raw_nodes, list):
            return {"added": 0, "updated": 0, "ignored": 0}
        added = 0
        updated = 0
        ignored = 0
        for raw_node in raw_nodes:
            if not isinstance(raw_node, Mapping):
                continue
            try:
                incoming = _coerce_member_payload(raw_node)
            except Exception:
                ignored += 1
                continue
            result = self._merge_member_locked(incoming, source=source)
            if result == "added":
                added += 1
            elif result == "updated":
                updated += 1
            else:
                ignored += 1
        return {"added": added, "updated": updated, "ignored": ignored}

    def _merge_member_locked(self, incoming: V1MembershipNode, *, source: str) -> str:
        conflict_owner = self._find_conflict_owner_locked(
            address=incoming.address,
            exclude_node_id=incoming.node_id,
        )
        if conflict_owner is not None and conflict_owner.health == "healthy":
            self._stats["membership_conflict_total"] = (
                int(self._stats.get("membership_conflict_total", 0)) + 1
            )
            self._stats["last_error"] = (
                "membership_conflict:"
                f"source={source},address={incoming.address},"
                f"owner={conflict_owner.node_id},incoming={incoming.node_id}"
            )
            return "conflict"

        existing = self._members.get(incoming.node_id)
        if existing is None:
            self._members[incoming.node_id] = incoming
            self._view_epoch += 1
            return "added"

        if _is_member_newer(existing, incoming):
            was_offline = existing.health == "offline"
            self._members[incoming.node_id] = incoming
            self._view_epoch += 1
            if was_offline and incoming.health == "healthy":
                self._stats["rejoin_total"] = int(self._stats.get("rejoin_total", 0)) + 1
            return "updated"
        return "ignored"

    def _find_conflict_owner_locked(
        self,
        *,
        address: str,
        exclude_node_id: str,
    ) -> V1MembershipNode | None:
        for node in self._members.values():
            if node.node_id == exclude_node_id:
                continue
            if node.address == address:
                return node
        return None

    def _apply_offline_sweep_locked(self, now_ms: int) -> None:
        timeout_ms = int(self._offline_timeout_s * 1000.0)
        for node_id, node in list(self._members.items()):
            if node_id == self._node_id:
                continue
            delta = now_ms - int(node.last_seen_ms)
            if delta <= timeout_ms:
                continue
            if node.health == "offline":
                continue
            self._members[node_id] = replace(node, health="offline")
            self._view_epoch += 1
            self._stats["offline_mark_total"] = int(self._stats.get("offline_mark_total", 0)) + 1

    def _record_gossip_malformed_request(self, *, detail: str) -> None:
        normalized_detail = str(detail or "").strip() or "unknown"
        with self._lock:
            self._increment_bounded_stat_locked("gossip_malformed_total")
            self._stats["last_error"] = f"gossip_malformed:{normalized_detail}"

    def _record_gossip_transport_error(self, *, detail: str) -> None:
        normalized_detail = str(detail or "").strip() or "unknown"
        with self._lock:
            self._increment_bounded_stat_locked("gossip_transport_error_total")
            self._stats["last_error"] = f"gossip_transport_error:{normalized_detail}"

    def _increment_bounded_stat_locked(self, stat_key: str) -> None:
        current = int(self._stats.get(stat_key, 0))
        if current >= _MAX_BOUNDED_ERROR_COUNT:
            return
        self._stats[stat_key] = current + 1

    def _resolve_runtime_state_query_entries(self) -> Callable[..., Any] | None:
        flow_process_execution = getattr(self._runtime_host, "_flow_process_execution", None)
        flow_engine = getattr(flow_process_execution, "_flow_engine", None)
        state_runtime = getattr(flow_engine, "_state_runtime", None)
        query_entries = getattr(state_runtime, "query_namespace_entries", None)
        if callable(query_entries):
            return query_entries
        return None

    def _runtime_state_query_allow_locked(self, *, principal: str, now_ms: int) -> bool:
        window = self._runtime_state_query_windows.setdefault(principal, deque())
        floor_ms = int(now_ms) - _RUNTIME_STATE_QUERY_WINDOW_MS
        while window and int(window[0]) < floor_ms:
            window.popleft()
        if len(window) >= _RUNTIME_STATE_QUERY_MAX_PER_WINDOW:
            return False
        window.append(int(now_ms))
        return True

    def _record_runtime_state_query_audit_locked(
        self,
        *,
        principal: str,
        namespace: str,
        prefix: str,
        limit: int,
        cursor: int,
        allowed: bool,
        reason: str,
        reveal_values: bool,
        result_count: int,
    ) -> None:
        self._runtime_state_query_audit.append(
            {
                "at_ms": _now_ms(),
                "principal": principal,
                "namespace": namespace,
                "prefix": prefix,
                "limit": int(limit),
                "cursor": int(cursor),
                "allowed": bool(allowed),
                "reason": str(reason),
                "reveal_values": bool(reveal_values),
                "result_count": int(result_count),
            }
        )


class _RuntimeNodeControlClusterBackendRouter:
    def __init__(
        self,
        *,
        node_control_call: NodeControlCaller,
        default_node_address: str,
    ) -> None:
        if not callable(node_control_call):
            raise TypeError("node_control_call must be callable.")
        self._node_control_call = node_control_call
        self._default_node_address = _normalize_node_address(default_node_address)

    def list_cluster_backends(
        self,
        *,
        required_tags: Mapping[str, str] | None = None,
        required_capabilities: Mapping[str, Any] | None = None,
        include_metrics: bool = True,
    ) -> tuple[dict[str, Any], ...]:
        snapshot = self._call_node_control_with_transport_retry(
            "cluster_backend_container_snapshot",
            required_tags=_normalize_string_mapping(required_tags) or None,
            required_capabilities=_normalize_mapping(required_capabilities) or None,
            include_metrics=bool(include_metrics),
            node_address=self._default_node_address,
        )
        if not isinstance(snapshot, Mapping):
            raise RuntimeError("cluster_backend_snapshot_invalid:payload_must_be_mapping")
        records = snapshot.get("records")
        if not isinstance(records, (list, tuple)):
            return ()
        normalized: list[dict[str, Any]] = []
        for item in records:
            if not isinstance(item, Mapping):
                continue
            normalized.append(dict(item))
        return tuple(normalized)

    def submit_remote_backend_job(
        self,
        *,
        node_address: str,
        request: Mapping[str, Any],
        backend_id: str | None = None,
        required_tags: Mapping[str, str] | None = None,
        required_capabilities: Mapping[str, Any] | None = None,
        preferred_backend_id: str | None = None,
        request_epoch: int | None = None,
    ) -> Mapping[str, Any]:
        payload = self._call_node_control_with_transport_retry(
            "submit_runtime_backend_job",
            request=dict(request),
            backend_id=backend_id,
            required_tags=_normalize_string_mapping(required_tags) or None,
            required_capabilities=_normalize_mapping(required_capabilities) or None,
            preferred_backend_id=preferred_backend_id,
            request_epoch=request_epoch,
            node_address=_normalize_node_address(node_address),
        )
        if not isinstance(payload, Mapping):
            raise RuntimeError("submit_runtime_backend_job_invalid:payload_must_be_mapping")
        return dict(payload)

    def poll_remote_backend_job(
        self,
        *,
        node_address: str,
        job_token: str,
        auto_ack: bool = False,
    ) -> Mapping[str, Any] | None:
        payload = self._call_node_control_with_transport_retry(
            "poll_runtime_backend_job",
            _normalize_non_empty(job_token, field_name="job_token"),
            auto_ack=bool(auto_ack),
            node_address=_normalize_node_address(node_address),
        )
        if payload is None:
            return None
        if not isinstance(payload, Mapping):
            raise RuntimeError("poll_runtime_backend_job_invalid:payload_must_be_mapping")
        return dict(payload)

    def cancel_remote_backend_job(
        self,
        *,
        node_address: str,
        job_token: str,
        reason: str = "",
    ) -> bool:
        return bool(
            self._call_node_control_with_transport_retry(
                "cancel_runtime_backend_job",
                _normalize_non_empty(job_token, field_name="job_token"),
                reason=str(reason or ""),
                node_address=_normalize_node_address(node_address),
            )
        )

    def ack_remote_backend_job(
        self,
        *,
        node_address: str,
        job_token: str,
    ) -> bool:
        return bool(
            self._call_node_control_with_transport_retry(
                "ack_runtime_backend_job",
                _normalize_non_empty(job_token, field_name="job_token"),
                node_address=_normalize_node_address(node_address),
            )
        )

    def _call_node_control_with_transport_retry(self, op: str, *args: Any, **kwargs: Any) -> Any:
        for attempt in (0, 1):
            try:
                return self._node_control_call(op, *args, **kwargs)
            except Exception as exc:
                message = str(exc)
                if "http_post_failed:" not in message or attempt >= 1:
                    raise


class _V1NodeControlService:
    def __init__(
        self,
        *,
        runtime_host: V1RuntimeHost,
        membership: V1NodeRuntimeService,
    ) -> None:
        self._runtime_host = runtime_host
        self._membership = membership
        self._flow_run_event_buffer: dict[tuple[str, str], deque[dict[str, Any]]] = {}
        self._flow_run_read_cursor_by_request: dict[tuple[str, str], int] = {}
        self._backend_job_refs_by_token: dict[str, dict[str, Any]] = {}
        self._backend_job_lock = threading.RLock()
        self._flow_run_lock = threading.RLock()
        self._topic_event_listener_id = f"node_control_flow_run:{id(self)}"
        self._attach_topic_event_listener()

    def invoke(self, op: str, *args: Any, **kwargs: Any) -> Any:
        normalized_op = str(op or "").strip()
        if not normalized_op:
            raise ValueError("node_control op must be non-empty.")
        method = getattr(self, normalized_op, None)
        if method is None or normalized_op.startswith("_"):
            raise ValueError(f"unsupported_node_control_op:{normalized_op}")
        return method(*args, **kwargs)

    def cluster_view_snapshot(self, schema: str = "v1") -> dict[str, Any]:
        return self._membership.cluster_view_snapshot(schema=schema)

    def cluster_gossip_stats(self) -> dict[str, Any]:
        return self._membership.cluster_gossip_stats()

    def cluster_contract_snapshot(self) -> dict[str, Any]:
        return self._membership.cluster_contract_snapshot()

    def list_runtime_nodes(self) -> list[dict[str, Any]]:
        return self._membership.list_runtime_nodes()

    def list_runtime_topics(self) -> list[dict[str, Any]]:
        return self._membership.list_runtime_topics()

    def list_runtime_actors(self) -> list[dict[str, Any]]:
        return self._membership.list_runtime_actors()

    def list_shared_state_services(self) -> list[dict[str, Any]]:
        return self._membership.list_shared_state_services()

    def list_published_endpoints(self) -> list[dict[str, Any]]:
        return self._membership.list_published_endpoints()

    def list_collective_executors(self) -> list[dict[str, Any]]:
        return self._membership.list_collective_executors()

    def cluster_scheduler_metrics(self) -> dict[str, Any]:
        return self._membership.cluster_scheduler_metrics()

    def list_runtime_backend_containers(
        self,
        *,
        required_tags: Mapping[str, str] | None = None,
        required_capabilities: Mapping[str, Any] | None = None,
        include_metrics: bool = True,
    ) -> list[dict[str, Any]]:
        runtime_host = self._runtime_host
        normalized_required_tags = _normalize_string_mapping(required_tags)
        normalized_required_capabilities = _normalize_mapping(required_capabilities)
        if normalized_required_tags or normalized_required_capabilities:
            records = runtime_host.find_backend_containers(
                required_tags=normalized_required_tags,
                required_capabilities=normalized_required_capabilities,
                include_metrics=bool(include_metrics),
            )
        else:
            records = runtime_host.list_backend_containers(
                include_metrics=bool(include_metrics),
            )
        node_id = _normalize_optional_non_empty(getattr(self._membership, "node_id", None))
        node_address = _normalize_optional_non_empty(
            getattr(self._membership, "node_address", None)
        )
        rows: list[dict[str, Any]] = []
        for raw_record in records:
            if not isinstance(raw_record, Mapping):
                continue
            row = dict(raw_record)
            if node_id is not None:
                row["node_id"] = node_id
            if node_address is not None:
                row["node_address"] = node_address
            rows.append(row)
        rows.sort(
            key=lambda item: (
                str(item.get("node_id") or ""),
                str(item.get("backend_id") or ""),
            )
        )
        return rows

    def cluster_backend_container_snapshot(
        self,
        *,
        required_tags: Mapping[str, str] | None = None,
        required_capabilities: Mapping[str, Any] | None = None,
        include_metrics: bool = True,
        per_node_timeout_s: float | None = None,
    ) -> dict[str, Any]:
        normalized_required_tags = _normalize_string_mapping(required_tags)
        normalized_required_capabilities = _normalize_mapping(required_capabilities)
        timeout_s = float(getattr(self._membership, "_http_timeout_s", _DEFAULT_HTTP_TIMEOUT_S))
        if per_node_timeout_s is not None:
            timeout_s = _normalize_positive_float(
                per_node_timeout_s,
                field_name="per_node_timeout_s",
            )

        caller = build_http_node_control_caller(
            timeout_s=timeout_s,
            local_address=getattr(self._membership, "node_address", None),
            local_invoke=lambda op, args, kwargs: self.invoke(op, *args, **kwargs),
        )
        view = self._membership.cluster_view_snapshot(schema="v1")
        view_epoch = int(view.get("view_epoch") or 0) if isinstance(view, Mapping) else 0

        nodes = self._membership.list_runtime_nodes()
        records: list[dict[str, Any]] = []
        failed_nodes: list[dict[str, Any]] = []
        for node in sorted(nodes, key=lambda item: str(item.get("node_id") or "")):
            node_id = _normalize_optional_non_empty(node.get("node_id"))
            node_address = _normalize_optional_non_empty(node.get("address"))
            if node_id is None or node_address is None:
                continue
            if not bool(node.get("healthy")):
                continue
            try:
                node_records = caller(
                    "list_runtime_backend_containers",
                    required_tags=normalized_required_tags or None,
                    required_capabilities=normalized_required_capabilities or None,
                    include_metrics=bool(include_metrics),
                    node_address=node_address,
                )
            except Exception as exc:
                failed_nodes.append(
                    {
                        "node_id": node_id,
                        "node_address": node_address,
                        "error": str(exc),
                    }
                )
                continue
            if not isinstance(node_records, (list, tuple)):
                failed_nodes.append(
                    {
                        "node_id": node_id,
                        "node_address": node_address,
                        "error": "backend_snapshot_invalid_payload",
                    }
                )
                continue
            for raw_record in node_records:
                if not isinstance(raw_record, Mapping):
                    continue
                record = dict(raw_record)
                record.setdefault("node_id", node_id)
                record.setdefault("node_address", node_address)
                records.append(record)

        records.sort(
            key=lambda item: (
                str(item.get("node_id") or ""),
                str(item.get("backend_id") or ""),
            )
        )
        return {
            "schema_version": "v1.cluster.backend.snapshot",
            "generated_at": time.time(),
            "view_epoch": view_epoch,
            "records": records,
            "failed_nodes": failed_nodes,
        }

    def submit_runtime_backend_job(
        self,
        *,
        request: Mapping[str, Any],
        backend_id: str | None = None,
        required_tags: Mapping[str, str] | None = None,
        required_capabilities: Mapping[str, Any] | None = None,
        preferred_backend_id: str | None = None,
        request_epoch: int | None = None,
    ) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            raise TypeError("request must be mapping.")
        runtime_host = self._runtime_host
        normalized_backend_id = _normalize_optional_non_empty(backend_id)
        normalized_required_tags = _normalize_string_mapping(required_tags)
        normalized_required_capabilities = _normalize_mapping(required_capabilities)
        normalized_preferred_backend_id = _normalize_optional_non_empty(preferred_backend_id)
        normalized_request_epoch = (
            _normalize_optional_epoch(request_epoch)
            if request_epoch is not None
            else _resolve_backend_request_epoch(request)
        )

        selection_trace: dict[str, Any] | None = None
        if normalized_backend_id is None:
            selection = runtime_host.select_backend_container(
                required_tags=normalized_required_tags or None,
                required_capabilities=normalized_required_capabilities or None,
                preferred_backend_id=normalized_preferred_backend_id,
                request_epoch=normalized_request_epoch,
            )
            normalized_backend_id = _normalize_optional_non_empty(selection.get("backend_id"))
            selection_trace = {
                "backend_id": selection.get("backend_id"),
                "request_epoch": selection.get("request_epoch"),
                "matched_request_epoch": selection.get("matched_request_epoch"),
                "epoch_policy": selection.get("epoch_policy"),
                "selection_reason": selection.get("selection_reason"),
                "required_tags": dict(normalized_required_tags),
                "required_capabilities": dict(normalized_required_capabilities),
            }
            if isinstance(selection.get("selection_reason_codes"), list):
                selection_trace["selection_reason_codes"] = list(
                    selection["selection_reason_codes"]
                )
            if isinstance(selection.get("selected_backend_state"), Mapping):
                selection_trace["selected_backend_state"] = dict(
                    selection["selected_backend_state"]
                )
            if isinstance(selection.get("candidate_backend_states"), list):
                selection_trace["candidate_backend_states"] = [
                    dict(item)
                    for item in selection["candidate_backend_states"]
                    if isinstance(item, Mapping)
                ]
            if isinstance(selection.get("excluded_backend_states"), list):
                selection_trace["excluded_backend_states"] = [
                    dict(item)
                    for item in selection["excluded_backend_states"]
                    if isinstance(item, Mapping)
                ]
        if normalized_backend_id is None:
            raise RuntimeError("backend_container_selection_failed")

        if normalized_required_tags or normalized_required_capabilities:
            tag_matched_records = runtime_host.find_backend_containers(
                required_tags=normalized_required_tags,
                required_capabilities=normalized_required_capabilities,
                include_metrics=False,
            )
            allowed_backend_ids = {
                _normalize_optional_non_empty(record.get("backend_id"))
                for record in tag_matched_records
            }
            if normalized_backend_id not in allowed_backend_ids:
                raise RuntimeError(
                    f"backend_container_requirement_constraint_mismatch:backend_id={normalized_backend_id}",
                )

        backend = runtime_host.get_backend_container(normalized_backend_id)
        if backend is None:
            raise RuntimeError(f"backend_container_not_found:{normalized_backend_id}")

        request_payload = dict(request)
        if normalized_request_epoch is not None:
            request_payload.setdefault("request_epoch", normalized_request_epoch)
        if selection_trace is not None:
            request_payload.setdefault("backend_selection", selection_trace)

        submit_result = backend.submit(request_payload)
        response = (
            dict(submit_result)
            if isinstance(submit_result, Mapping)
            else {"submit_result": submit_result}
        )
        response.setdefault("backend_id", normalized_backend_id)
        response["node_id"] = self._membership.node_id
        response["node_address"] = self._membership.node_address

        job_id = _normalize_optional_non_empty(response.get("job_id"))
        if job_id is None:
            return response

        job_token = self._register_backend_job_ref(
            backend_id=normalized_backend_id,
            job_id=job_id,
        )
        response["job_id"] = job_id
        response["job_token"] = job_token
        return response

    def poll_runtime_backend_job(
        self,
        job_token: str,
        *,
        auto_ack: bool = False,
    ) -> dict[str, Any] | None:
        normalized_job_token = _normalize_non_empty(job_token, field_name="job_token")
        backend_id, job_id = self._resolve_backend_job_ref(normalized_job_token)
        backend = self._runtime_host.get_backend_container(backend_id)
        if backend is None:
            raise RuntimeError(f"backend_container_not_found:{backend_id}")
        poll_result = backend.poll(job_id)
        if poll_result is None:
            return None
        response = (
            dict(poll_result) if isinstance(poll_result, Mapping) else {"result": poll_result}
        )
        response.setdefault("backend_id", backend_id)
        response.setdefault("job_id", job_id)
        response.setdefault("job_token", normalized_job_token)
        if auto_ack:
            acked = bool(backend.ack(job_id))
            response["acked"] = acked
            if acked:
                self._drop_backend_job_ref(normalized_job_token)
        return response

    def cancel_runtime_backend_job(
        self,
        job_token: str,
        *,
        reason: str = "",
    ) -> bool:
        normalized_job_token = _normalize_non_empty(job_token, field_name="job_token")
        backend_id, job_id = self._resolve_backend_job_ref(normalized_job_token)
        backend = self._runtime_host.get_backend_container(backend_id)
        if backend is None:
            raise RuntimeError(f"backend_container_not_found:{backend_id}")
        canceled = bool(backend.cancel(job_id, reason=str(reason or "")))
        if canceled:
            self._drop_backend_job_ref(normalized_job_token)
        return canceled

    def ack_runtime_backend_job(self, job_token: str) -> bool:
        normalized_job_token = _normalize_non_empty(job_token, field_name="job_token")
        backend_id, job_id = self._resolve_backend_job_ref(normalized_job_token)
        backend = self._runtime_host.get_backend_container(backend_id)
        if backend is None:
            raise RuntimeError(f"backend_container_not_found:{backend_id}")
        acked = bool(backend.ack(job_id))
        if acked:
            self._drop_backend_job_ref(normalized_job_token)
        return acked

    def query_runtime_state(
        self,
        namespace: str,
        *,
        prefix: str,
        principal: str,
        roles: list[str] | None = None,
        allowed_namespaces: list[str] | None = None,
        permissions: list[str] | None = None,
        limit: int | None = None,
        cursor: int | str | None = None,
        include_values: bool = True,
        reveal_values: bool = False,
    ) -> dict[str, Any]:
        return self._membership.query_runtime_state(
            namespace,
            prefix=prefix,
            principal=principal,
            roles=roles,
            allowed_namespaces=allowed_namespaces,
            permissions=permissions,
            limit=limit,
            cursor=cursor,
            include_values=include_values,
            reveal_values=reveal_values,
        )

    def stream_tracker_stats(self) -> dict[str, Any]:
        return self._membership.stream_tracker_stats()

    def stream_tracker_request_status(self, request_id: str) -> dict[str, Any]:
        return self._membership.stream_tracker_request_status(request_id)

    def submit_flow_program_accept(
        self,
        flow_uri: str,
        version: str | None = None,
        *,
        bindings: Mapping[str, Any] | None = None,
        ingress: Any | None = None,
        egress: Any | None = None,
        run_config: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        topic_api = self._require_topic_api()
        normalized_flow_uri = _normalize_non_empty(flow_uri, field_name="flow_uri")
        scoped_registration = self._resolve_scoped_flow_registration(normalized_flow_uri)
        registration_metadata_raw = (
            getattr(scoped_registration, "metadata", None)
            if scoped_registration is not None
            else None
        )
        registration_metadata = (
            dict(registration_metadata_raw)
            if isinstance(registration_metadata_raw, Mapping)
            else None
        )
        flow_program = (
            getattr(scoped_registration, "declaration", None)
            if scoped_registration is not None
            else None
        )
        resolved_flow_program_rev = self._resolve_submit_flow_program_rev(
            requested_version=version,
            registration_metadata=registration_metadata,
            flow_program=flow_program,
        )
        io_contract = self._resolve_submit_io_contract(
            registration_metadata=registration_metadata,
            flow_program=flow_program,
        )
        (
            normalized_bindings,
            effective_ingress,
            effective_egress,
            effective_run_config,
        ) = prepare_flow_program_submit_inputs(
            io_contract=io_contract,
            bindings=bindings,
            ingress=ingress,
            egress=egress,
            run_config=run_config,
        )
        if normalized_bindings is not None:
            effective_run_config.setdefault("bindings", dict(normalized_bindings))

        requested_run_id = self._resolve_submit_requested_run_id(effective_run_config)
        requested_instance_id = self._resolve_submit_requested_instance_id(effective_run_config)
        flow_process_uri, flow_instance_id = self._allocate_submit_flow_process_uri(
            topic_api=topic_api,
            requested_run_id=requested_run_id,
            requested_instance_id=requested_instance_id,
        )
        in_topic_uri = self._resolve_submit_topic_uri(
            direction="in",
            flow_instance_id=flow_instance_id,
            bindings=normalized_bindings,
            connector=effective_ingress,
            run_config=effective_run_config,
        )
        out_topic_uri = self._resolve_submit_topic_uri(
            direction="out",
            flow_instance_id=flow_instance_id,
            bindings=normalized_bindings,
            connector=effective_egress,
            run_config=effective_run_config,
        )

        local_address = _normalize_optional_non_empty(
            getattr(getattr(self._runtime_host, "comm_hub", None), "local_address", None),
        )
        if local_address is not None:
            self._ensure_submit_topic_route(
                topic_api=topic_api,
                topic_uri=in_topic_uri,
                coordinator_address=local_address,
            )
            self._ensure_submit_topic_route(
                topic_api=topic_api,
                topic_uri=out_topic_uri,
                coordinator_address=local_address,
            )

        existing_flow_program = self._resolve_registered_flow_program(
            topic_api=topic_api,
            flow_program_uri=normalized_flow_uri,
            flow_program_rev=resolved_flow_program_rev,
        )
        if existing_flow_program is None:
            register_flow_program = getattr(topic_api, "register_flow_program", None)
            if not callable(register_flow_program):
                raise RuntimeError("register_flow_program_not_supported")
            if flow_program is None:
                raise RuntimeError(
                    f"flow_program_not_registered:{normalized_flow_uri}@{resolved_flow_program_rev}"
                )
            register_flow_program(
                flow_program_uri=normalized_flow_uri,
                flow_program_rev=resolved_flow_program_rev,
                flow_program=flow_program,
            )

        register_flow_process = getattr(topic_api, "register_flow_process", None)
        if not callable(register_flow_process):
            raise RuntimeError("register_flow_process_not_supported")
        register_kwargs: dict[str, Any] = {}
        if local_address is not None:
            register_kwargs["flow_program_owner_address"] = local_address
        flow_process_metadata = {
            "flow_instance_id": flow_instance_id,
            "flow_uri": normalized_flow_uri,
            "submit_api": "submit_flow_program_accept",
        }
        flow_owner = _normalize_optional_non_empty(
            getattr(scoped_registration, "owner", None)
            if scoped_registration is not None
            else None,
        )
        if flow_owner is not None:
            flow_process_metadata["owner"] = flow_owner
        record = register_flow_process(
            flow_process_uri=flow_process_uri,
            flow_program_uri=normalized_flow_uri,
            flow_program_rev=resolved_flow_program_rev,
            in_topic_uri=in_topic_uri,
            out_topic_uri=out_topic_uri,
            metadata=flow_process_metadata,
            **register_kwargs,
        )
        return self._build_flow_run_descriptor(record)

    def lookup_flow_run_descriptor(self, run_id: str) -> dict[str, Any] | None:
        record = self._resolve_flow_process_record(run_id)
        if record is None:
            return None
        return self._build_flow_run_descriptor(record)

    def cancel_flow_run(self, run_id: str) -> bool:
        record = self._resolve_flow_process_record(run_id)
        if record is None:
            return False

        topic_api = self._require_topic_api()
        flow_process_uri = _normalize_non_empty(
            getattr(record, "flow_process_uri", None),
            field_name="flow_process_uri",
        )

        removed = False
        unregister_flow_process = getattr(topic_api, "unregister_flow_process", None)
        if callable(unregister_flow_process):
            removed = bool(
                unregister_flow_process(
                    flow_process_uri=flow_process_uri,
                )
            )
        if not removed:
            flow_process_catalog = getattr(topic_api, "flow_process_catalog", None)
            delete_flow_process = getattr(flow_process_catalog, "delete", None)
            if callable(delete_flow_process):
                removed = bool(delete_flow_process(flow_process_uri))

        if removed:
            self._drop_flow_run_read_state(flow_process_uri=flow_process_uri)
        return removed

    def flow_run_request_delivery_status(
        self,
        run_id: str,
        request_id: str,
    ) -> dict[str, Any] | None:
        record = self._resolve_flow_process_record(run_id)
        if record is None:
            return None

        normalized_request_id = _normalize_non_empty(request_id, field_name="request_id")
        out_topic_uri = _normalize_non_empty(
            getattr(record, "out_topic_uri", None),
            field_name="out_topic_uri",
        )
        ledger = self._event_group_ledger(
            topic_uri=out_topic_uri,
            event_group_id=normalized_request_id,
        )
        if not isinstance(ledger, Mapping):
            return None

        status_payload = {
            "request_ref_id": normalized_request_id,
            "event_chain_pending": int(ledger.get("event_chain_pending") or 0),
            "producer_done": bool(ledger.get("producer_done")),
            "request_done": bool(ledger.get("request_done_emitted")),
            "final_seq": ledger.get("final_seq"),
            "expected_total_events": ledger.get("expected_total_events_hint"),
        }
        return normalize_flow_run_request_delivery_status(
            status_payload,
            fallback_request_id=normalized_request_id,
            run_status=ledger.get("outcome_status"),
        )

    def flow_run_read(
        self,
        run_id: str,
        *,
        request_id: str | None = None,
        timeout: float = 5.0,
        from_seq: int | None = None,
    ) -> dict[str, Any] | None:
        record = self._resolve_flow_process_record(run_id)
        if record is None:
            return None

        out_topic_uri = _normalize_non_empty(
            getattr(record, "out_topic_uri", None),
            field_name="out_topic_uri",
        )
        flow_process_uri = _normalize_non_empty(
            getattr(record, "flow_process_uri", None),
            field_name="flow_process_uri",
        )

        timeout_s = float(timeout)
        if timeout_s < 0.0:
            raise ValueError("timeout must be >= 0.")

        start_seq = 1
        if from_seq is not None:
            start_seq = _normalize_non_negative_int(from_seq, field_name="from_seq")

        resolved_request_id = self._resolve_request_id_for_read(
            out_topic_uri=out_topic_uri,
            explicit_request_id=request_id,
        )
        if resolved_request_id is None:
            return None

        cursor_key = (flow_process_uri, resolved_request_id)
        if from_seq is None:
            with self._flow_run_lock:
                start_seq = int(self._flow_run_read_cursor_by_request.get(cursor_key, 1))

        deadline = time.time() + timeout_s
        while True:
            event = self._find_buffered_event(
                topic_uri=out_topic_uri,
                event_group_id=resolved_request_id,
                from_seq=start_seq,
            )
            if event is not None:
                next_seq = int(event["seq"]) + 1
                if from_seq is None:
                    with self._flow_run_lock:
                        self._flow_run_read_cursor_by_request[cursor_key] = next_seq
                read_item = {
                    "kind": "data",
                    "request_id": resolved_request_id,
                    "request_ref_id": resolved_request_id,
                    "seq": int(event["seq"]),
                    "value": event.get("payload"),
                }
                return normalize_flow_run_read_item(read_item)

            done = self._build_done_read_item(
                topic_uri=out_topic_uri,
                event_group_id=resolved_request_id,
            )
            if done is not None:
                if from_seq is None:
                    final_seq = done.get("final_seq")
                    if isinstance(final_seq, int):
                        with self._flow_run_lock:
                            self._flow_run_read_cursor_by_request[cursor_key] = max(
                                int(self._flow_run_read_cursor_by_request.get(cursor_key, 1)),
                                int(final_seq) + 1,
                            )
                return normalize_flow_run_read_item(done)

            if timeout_s <= 0.0 or time.time() >= deadline:
                return None
            remaining = max(0.0, deadline - time.time())
            time.sleep(min(_FLOW_RUN_READ_POLL_INTERVAL_S, remaining))

    def node_leave(self, mode: str = "soft") -> dict[str, Any]:
        return self._membership.node_leave(mode=mode)

    def _require_topic_api(self) -> Any:
        topic_api = getattr(self._runtime_host, "topic_api", None)
        if topic_api is None:
            raise RuntimeError("topic_api_not_available")
        return topic_api

    def _resolve_scoped_flow_registration(self, flow_uri: str) -> Any | None:
        try:
            from sage.runtime.flownet.client.runtime_client import get_scoped_runtime_client
        except Exception:
            return None
        scoped_client = get_scoped_runtime_client()
        if scoped_client is None:
            return None
        flows_surface = getattr(scoped_client, "flows", None)
        get_discoverable = getattr(flows_surface, "get_discoverable", None)
        if not callable(get_discoverable):
            return None
        try:
            return get_discoverable(flow_uri)
        except Exception:
            return None

    def _resolve_submit_flow_program_rev(
        self,
        *,
        requested_version: str | None,
        registration_metadata: Mapping[str, Any] | None,
        flow_program: Any,
    ) -> str:
        if requested_version is not None:
            return _normalize_non_empty(requested_version, field_name="version")
        metadata_candidates = (
            registration_metadata,
            getattr(flow_program, "metadata", None),
        )
        for metadata in metadata_candidates:
            if not isinstance(metadata, Mapping):
                continue
            for key in ("flow_program_rev", "program_rev", "version"):
                candidate = _normalize_optional_non_empty(metadata.get(key))
                if candidate is not None:
                    return candidate
        return "v1"

    def _resolve_submit_io_contract(
        self,
        *,
        registration_metadata: Mapping[str, Any] | None,
        flow_program: Any,
    ) -> Mapping[str, Any] | None:
        metadata_candidates = (
            registration_metadata,
            getattr(flow_program, "metadata", None),
        )
        for metadata in metadata_candidates:
            if not isinstance(metadata, Mapping):
                continue
            raw_contract = metadata.get("io_contract")
            if raw_contract is None:
                continue
            if not isinstance(raw_contract, Mapping):
                raise TypeError("io_contract must be a mapping when provided in flow metadata.")
            return dict(raw_contract)
        return None

    def _resolve_registered_flow_program(
        self,
        *,
        topic_api: Any,
        flow_program_uri: str,
        flow_program_rev: str,
    ) -> Any | None:
        resolve_registered = getattr(topic_api, "resolve_registered_flow_program", None)
        if not callable(resolve_registered):
            return None
        try:
            return resolve_registered(
                flow_program_uri=flow_program_uri,
                flow_program_rev=flow_program_rev,
            )
        except Exception:
            return None

    @staticmethod
    def _resolve_submit_requested_run_id(run_config: Mapping[str, Any]) -> str | None:
        if "run_id" not in run_config:
            return None
        raw_run_id = run_config.get("run_id")
        if raw_run_id is None:
            return None
        return _normalize_non_empty(raw_run_id, field_name="run_config.run_id")

    @staticmethod
    def _resolve_submit_requested_instance_id(run_config: Mapping[str, Any]) -> str | None:
        for key in ("flow_instance_id", "instance_id"):
            if key not in run_config:
                continue
            raw_value = run_config.get(key)
            if raw_value is None:
                continue
            return _normalize_non_empty(raw_value, field_name=f"run_config.{key}")
        return None

    def _allocate_submit_flow_process_uri(
        self,
        *,
        topic_api: Any,
        requested_run_id: str | None,
        requested_instance_id: str | None,
    ) -> tuple[str, str]:
        flow_process_catalog = getattr(topic_api, "flow_process_catalog", None)
        get_flow_process = getattr(flow_process_catalog, "get", None)

        if requested_run_id is not None:
            normalized_run_id = self._normalize_submit_run_id(requested_run_id)
            if callable(get_flow_process) and get_flow_process(normalized_run_id) is not None:
                raise RuntimeError(f"flow_process_already_exists:{normalized_run_id}")
            return normalized_run_id, self._resolve_flow_instance_id_from_process_uri(
                normalized_run_id
            )

        instance_id = _normalize_optional_non_empty(requested_instance_id)
        if instance_id is None:
            instance_id = uuid.uuid4().hex
        while True:
            candidate_uri = f"flowprocess://{instance_id}"
            if not callable(get_flow_process) or get_flow_process(candidate_uri) is None:
                return candidate_uri, instance_id
            instance_id = uuid.uuid4().hex

    @staticmethod
    def _normalize_submit_run_id(run_id: str) -> str:
        normalized_run_id = _normalize_non_empty(run_id, field_name="run_id")
        if normalized_run_id.startswith("flowprocess://"):
            return normalized_run_id
        return f"flowprocess://{normalized_run_id}"

    @staticmethod
    def _resolve_flow_instance_id_from_process_uri(flow_process_uri: str) -> str:
        prefix = "flowprocess://"
        if flow_process_uri.startswith(prefix):
            normalized = _normalize_optional_non_empty(flow_process_uri[len(prefix) :])
            if normalized is not None:
                return normalized
        return flow_process_uri

    def _resolve_submit_topic_uri(
        self,
        *,
        direction: str,
        flow_instance_id: str,
        bindings: Mapping[str, Any] | None,
        connector: Any,
        run_config: Mapping[str, Any],
    ) -> str:
        normalized_direction = str(direction or "").strip().lower()
        if normalized_direction not in {"in", "out"}:
            raise ValueError(f"submit topic direction unsupported: {direction!r}")
        binding_keys = (
            ("in_topic", "ingress_topic", "topic_in")
            if normalized_direction == "in"
            else ("out_topic", "egress_topic", "topic_out")
        )
        run_config_keys = (
            ("in_topic", "ingress_topic", "input_topic")
            if normalized_direction == "in"
            else ("out_topic", "egress_topic", "output_topic")
        )
        candidate = self._resolve_topic_from_mapping(bindings, keys=binding_keys)
        if candidate is None:
            candidate = _resolve_submit_topic_binding(connector)
        if candidate is None:
            candidate = self._resolve_topic_from_mapping(
                run_config.get("bindings"),
                keys=binding_keys,
            )
        if candidate is None:
            candidate = self._resolve_topic_from_mapping(run_config, keys=run_config_keys)
        if candidate is not None:
            return candidate
        suffix = "in" if normalized_direction == "in" else "out"
        return f"topic:flow.submit/{flow_instance_id}/{suffix}"

    @staticmethod
    def _resolve_topic_from_mapping(
        raw_value: Any,
        *,
        keys: tuple[str, ...],
    ) -> str | None:
        if not isinstance(raw_value, Mapping):
            return None
        for key in keys:
            if key not in raw_value:
                continue
            candidate = _resolve_submit_topic_binding(raw_value.get(key))
            if candidate is not None:
                return candidate
        return None

    def _ensure_submit_topic_route(
        self,
        *,
        topic_api: Any,
        topic_uri: str,
        coordinator_address: str,
    ) -> None:
        routing_directory = getattr(topic_api, "routing_directory", None)
        resolve = getattr(routing_directory, "resolve", None)
        upsert_route = getattr(routing_directory, "upsert_route", None)
        if not callable(resolve) or not callable(upsert_route):
            return
        try:
            existing = resolve(topic_uri)
        except Exception:
            existing = None
        if existing is not None:
            return
        upsert_route(
            topic_uri=topic_uri,
            coordinator_address=coordinator_address,
            epoch=1,
        )

    def _resolve_flow_process_record(self, run_id: str) -> Any | None:
        normalized_run_id = _normalize_non_empty(run_id, field_name="run_id")
        topic_api = self._require_topic_api()
        flow_process_catalog = getattr(topic_api, "flow_process_catalog", None)
        get_flow_process = getattr(flow_process_catalog, "get", None)
        if not callable(get_flow_process):
            return None

        candidates = [normalized_run_id]
        if not normalized_run_id.startswith("flowprocess://"):
            candidates.append(f"flowprocess://{normalized_run_id}")
        for candidate in candidates:
            record = get_flow_process(candidate)
            if record is not None:
                return record
        return None

    def _build_flow_run_descriptor(self, record: Any) -> dict[str, Any]:
        flow_process_uri = _normalize_non_empty(
            getattr(record, "flow_process_uri", None),
            field_name="flow_process_uri",
        )
        flow_program_uri = _normalize_non_empty(
            getattr(record, "flow_program_uri", None),
            field_name="flow_program_uri",
        )
        flow_program_rev = _normalize_non_empty(
            getattr(record, "flow_program_rev", None),
            field_name="flow_program_rev",
        )
        in_topic_uri = _normalize_non_empty(
            getattr(record, "in_topic_uri", None),
            field_name="in_topic_uri",
        )
        out_topic_uri = _normalize_non_empty(
            getattr(record, "out_topic_uri", None),
            field_name="out_topic_uri",
        )
        descriptor = {
            "run_id": flow_process_uri,
            "flow_process_uri": flow_process_uri,
            "flow_program_uri": flow_program_uri,
            "flow_program_rev": flow_program_rev,
            "in_topic_uri": in_topic_uri,
            "out_topic_uri": out_topic_uri,
            "status": "running",
            "accept_schema": "flow_program_submit_accept.v1",
        }
        node_address = _normalize_optional_non_empty(
            getattr(getattr(self._runtime_host, "comm_hub", None), "local_address", None)
        )
        if node_address is not None:
            descriptor["target_node"] = node_address
            descriptor["node_address"] = node_address
        metadata = getattr(record, "metadata", None)
        if isinstance(metadata, Mapping):
            flow_instance_id = _normalize_optional_non_empty(metadata.get("flow_instance_id"))
            if flow_instance_id is not None:
                descriptor["flow_instance_id"] = flow_instance_id
        return descriptor

    def _event_group_ledger(
        self,
        *,
        topic_uri: str,
        event_group_id: str,
    ) -> dict[str, Any] | None:
        topic_api = self._require_topic_api()
        event_group_ledger = getattr(topic_api, "event_group_ledger", None)
        if not callable(event_group_ledger):
            return None
        try:
            result = event_group_ledger(
                topic_uri=topic_uri,
                event_group_id=event_group_id,
            )
        except Exception:
            return None
        if isinstance(result, Mapping):
            return dict(result)
        return None

    def _resolve_request_id_for_read(
        self,
        *,
        out_topic_uri: str,
        explicit_request_id: str | None,
    ) -> str | None:
        if explicit_request_id is not None:
            return _normalize_non_empty(explicit_request_id, field_name="request_id")

        topic_api = self._require_topic_api()
        routing_directory = getattr(topic_api, "routing_directory", None)
        coordinator_registry = getattr(topic_api, "coordinator_registry", None)
        require_route = getattr(routing_directory, "require", None)
        get_state = getattr(coordinator_registry, "get", None)
        if callable(require_route) and callable(get_state):
            try:
                route = require_route(out_topic_uri)
                state = get_state(route.topic_uri, route.epoch)
                ledgers = getattr(state, "event_group_ledgers", None) if state is not None else None
                if isinstance(ledgers, Mapping) and ledgers:
                    latest = max(
                        ledgers.values(),
                        key=lambda ledger: float(getattr(ledger, "updated_at", 0.0)),
                    )
                    request_id = _normalize_optional_non_empty(
                        getattr(latest, "event_group_id", None),
                    )
                    if request_id is not None:
                        return request_id
            except Exception:
                pass

        with self._flow_run_lock:
            candidates: list[tuple[float, str]] = []
            for (topic_uri, event_group_id), events in self._flow_run_event_buffer.items():
                if topic_uri != out_topic_uri or not events:
                    continue
                last_event = events[-1]
                observed_at = float(last_event.get("published_at") or 0.0)
                candidates.append((observed_at, event_group_id))
            if not candidates:
                return None
            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1]

    def _attach_topic_event_listener(self) -> None:
        topic_api = getattr(self._runtime_host, "topic_api", None)
        add_topic_event_listener = getattr(topic_api, "add_topic_event_listener", None)
        if not callable(add_topic_event_listener):
            return
        try:
            add_topic_event_listener(
                listener_id=self._topic_event_listener_id,
                listener=self._capture_topic_event,
            )
        except Exception:
            return

    def _capture_topic_event(self, event_record: dict[str, Any]) -> None:
        if not isinstance(event_record, Mapping):
            return
        topic_uri = _normalize_optional_non_empty(event_record.get("topic_uri"))
        event_group_id = _normalize_optional_non_empty(event_record.get("event_group_id"))
        if topic_uri is None or event_group_id is None:
            return
        try:
            seq = int(event_record.get("seq"))
        except (TypeError, ValueError):
            return
        if seq < 0:
            return
        replay_item = {
            "seq": seq,
            "payload": event_record.get("payload"),
            "published_at": float(event_record.get("published_at") or time.time()),
        }
        with self._flow_run_lock:
            key = (topic_uri, event_group_id)
            events = self._flow_run_event_buffer.get(key)
            if events is None:
                events = deque(maxlen=_FLOW_RUN_EVENT_BUFFER_PER_REQUEST)
                self._flow_run_event_buffer[key] = events
            if events and int(events[-1].get("seq", -1)) >= seq:
                return
            events.append(replay_item)

    def _find_buffered_event(
        self,
        *,
        topic_uri: str,
        event_group_id: str,
        from_seq: int,
    ) -> dict[str, Any] | None:
        with self._flow_run_lock:
            events = self._flow_run_event_buffer.get((topic_uri, event_group_id))
            if not events:
                return None
            for item in events:
                seq = int(item.get("seq", -1))
                if seq >= from_seq:
                    return dict(item)
        return None

    def _build_done_read_item(
        self,
        *,
        topic_uri: str,
        event_group_id: str,
    ) -> dict[str, Any] | None:
        ledger = self._event_group_ledger(
            topic_uri=topic_uri,
            event_group_id=event_group_id,
        )
        if not isinstance(ledger, Mapping):
            return None
        if not bool(ledger.get("request_done_emitted")):
            return None
        final_seq_raw = ledger.get("final_seq")
        final_seq = int(final_seq_raw) if isinstance(final_seq_raw, int) else None
        expected_total_events_raw = ledger.get("expected_total_events_hint")
        expected_total_events = (
            int(expected_total_events_raw)
            if isinstance(expected_total_events_raw, int)
            else final_seq
        )
        outcome_status = str(ledger.get("outcome_status") or "succeeded").strip().lower()
        status = "completed"
        if outcome_status in {"failed", "aborted", "dropped"}:
            status = outcome_status
        done_item: dict[str, Any] = {
            "kind": "done",
            "request_id": event_group_id,
            "request_ref_id": event_group_id,
            "request_done": True,
            "producer_done": bool(ledger.get("producer_done")),
            "status": status,
        }
        if final_seq is not None:
            done_item["final_seq"] = final_seq
        if expected_total_events is not None:
            done_item["expected_total_events"] = expected_total_events
        return done_item

    def _drop_flow_run_read_state(self, *, flow_process_uri: str) -> None:
        with self._flow_run_lock:
            for key in list(self._flow_run_read_cursor_by_request.keys()):
                if key[0] == flow_process_uri:
                    self._flow_run_read_cursor_by_request.pop(key, None)

    def _register_backend_job_ref(self, *, backend_id: str, job_id: str) -> str:
        token = uuid.uuid4().hex
        with self._backend_job_lock:
            self._backend_job_refs_by_token[token] = {
                "backend_id": backend_id,
                "job_id": job_id,
                "created_at_ms": _now_ms(),
            }
        return token

    def _resolve_backend_job_ref(self, job_token: str) -> tuple[str, str]:
        with self._backend_job_lock:
            record = self._backend_job_refs_by_token.get(job_token)
        if not isinstance(record, Mapping):
            raise RuntimeError(f"backend_job_token_not_found:{job_token}")
        backend_id = _normalize_optional_non_empty(record.get("backend_id"))
        job_id = _normalize_optional_non_empty(record.get("job_id"))
        if backend_id is None or job_id is None:
            raise RuntimeError(f"backend_job_token_corrupt:{job_token}")
        return backend_id, job_id

    def _drop_backend_job_ref(self, job_token: str) -> None:
        with self._backend_job_lock:
            self._backend_job_refs_by_token.pop(job_token, None)


def _normalize_optional_str_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        normalized = _normalize_optional_non_empty(raw)
        return [normalized] if normalized is not None else []
    if not isinstance(raw, (list, tuple, set, frozenset)):
        normalized = _normalize_optional_non_empty(raw)
        return [normalized] if normalized is not None else []
    values: list[str] = []
    for item in raw:
        normalized = _normalize_optional_non_empty(item)
        if normalized is None:
            continue
        values.append(normalized)
    return values


def _normalize_string_mapping(raw: Any) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_value in raw.items():
        key = _normalize_optional_non_empty(raw_key)
        value = _normalize_optional_non_empty(raw_value)
        if key is None or value is None:
            continue
        normalized[key] = value
    return normalized


def _normalize_mapping(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {}
    return dict(raw)


def _normalize_optional_epoch(raw_value: Any) -> int | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, bool):
        return int(raw_value)
    if isinstance(raw_value, int):
        return raw_value
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    try:
        return int(normalized)
    except Exception:
        return None


def _resolve_backend_request_epoch(request: Mapping[str, Any]) -> int | None:
    request_candidates = (
        request.get("request_epoch"),
        request.get("epoch"),
        request.get("route_epoch"),
        request.get("topic_epoch"),
    )
    for candidate in request_candidates:
        normalized = _normalize_optional_epoch(candidate)
        if normalized is not None:
            return normalized

    metadata = request.get("metadata")
    if isinstance(metadata, Mapping):
        metadata_candidates = (
            metadata.get("request_epoch"),
            metadata.get("epoch"),
            metadata.get("route_epoch"),
            metadata.get("topic_epoch"),
        )
        for candidate in metadata_candidates:
            normalized = _normalize_optional_epoch(candidate)
            if normalized is not None:
                return normalized
    return None


def _namespace_acl_match(namespace: str, allowed_namespaces: list[str]) -> bool:
    if not allowed_namespaces:
        return True
    for rule in allowed_namespaces:
        normalized_rule = str(rule or "").strip()
        if not normalized_rule:
            continue
        if normalized_rule == "*":
            return True
        if normalized_rule.endswith("*"):
            if namespace.startswith(normalized_rule[:-1]):
                return True
            continue
        if namespace == normalized_rule:
            return True
    return False


def _has_runtime_state_permission(permissions: list[str], required_permission: str) -> bool:
    required = str(required_permission or "").strip()
    if not required:
        return True
    for permission in permissions:
        normalized_permission = str(permission or "").strip()
        if not normalized_permission:
            continue
        if normalized_permission == "*":
            return True
        if normalized_permission == required:
            return True
    return False


def _mask_runtime_state_value(value: Any) -> str:
    del value
    return _RUNTIME_STATE_QUERY_REDACTED_PLACEHOLDER


def resolve_seed_addresses(
    raw_seeds: list[str] | tuple[str, ...] | set[str] | str | None,
) -> tuple[str, ...]:
    values: list[str] = []
    if raw_seeds is None:
        env_raw = os.environ.get(_ENV_NODE_SEEDS, "")
        if env_raw.strip():
            values.extend(env_raw.split(","))
    elif isinstance(raw_seeds, str):
        values.extend(raw_seeds.split(","))
    else:
        values.extend(str(item) for item in raw_seeds)

    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        token = str(item or "").strip()
        if not token:
            continue
        if "@" in token:
            token = token.rsplit("@", 1)[-1]
        address = _normalize_node_address(token)
        if address in seen:
            continue
        seen.add(address)
        normalized.append(address)
    return tuple(normalized)


def _is_member_newer(current: V1MembershipNode, incoming: V1MembershipNode) -> bool:
    if current.incarnation != incoming.incarnation:
        return int(incoming.clock_ms) >= int(current.clock_ms)
    if int(incoming.clock_ms) > int(current.clock_ms):
        return True
    if int(incoming.last_seen_ms) > int(current.last_seen_ms):
        return True
    if current.health == "offline" and incoming.health == "healthy":
        return True
    return False


def _coerce_member_payload(raw_payload: Mapping[str, Any]) -> V1MembershipNode:
    node_id = _normalize_non_empty(raw_payload.get("node_id"), field_name="node_id")
    address = _normalize_node_address(raw_payload.get("address"))
    incarnation = _normalize_non_empty(raw_payload.get("incarnation"), field_name="incarnation")
    health = _normalize_non_empty(raw_payload.get("health"), field_name="health").lower()
    if health not in {"healthy", "offline", "unknown"}:
        health = "unknown"
    last_seen_ms = _normalize_non_negative_int(
        raw_payload.get("last_seen_ms"), field_name="last_seen_ms"
    )
    clock_ms = _normalize_non_negative_int(raw_payload.get("clock_ms"), field_name="clock_ms")
    metadata_raw = raw_payload.get("metadata")
    metadata = dict(metadata_raw) if isinstance(metadata_raw, Mapping) else {}
    return V1MembershipNode(
        node_id=node_id,
        address=address,
        incarnation=incarnation,
        health=health,
        last_seen_ms=last_seen_ms,
        clock_ms=clock_ms,
        metadata=metadata,
    )


def _read_json_request(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    raw_length = handler.headers.get("Content-Length")
    if raw_length is None:
        return {}
    try:
        content_length = int(raw_length)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid Content-Length header.") from exc
    if content_length <= 0:
        return {}
    body = handler.rfile.read(content_length)
    if not body:
        return {}
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise ValueError("request body is not valid JSON.") from exc
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise ValueError("request JSON payload must be an object.")
    return dict(payload)


def _write_json_response(
    handler: BaseHTTPRequestHandler,
    *,
    status_code: int,
    payload: Mapping[str, Any],
) -> None:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    handler.send_response(int(status_code))
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _try_write_json_response(
    handler: BaseHTTPRequestHandler,
    *,
    status_code: int,
    payload: Mapping[str, Any],
) -> str | None:
    try:
        _write_json_response(handler, status_code=status_code, payload=payload)
    except (BrokenPipeError, ConnectionResetError) as exc:
        return exc.__class__.__name__
    return None


def _http_post_json(
    node_address: str,
    *,
    path: str,
    payload: Mapping[str, Any],
    timeout_s: float,
) -> Any:
    normalized_address = _normalize_node_address(node_address)
    normalized_timeout_s = _normalize_positive_float(timeout_s, field_name="timeout_s")
    normalized_path = str(path or "").strip()
    if not normalized_path.startswith("/"):
        normalized_path = "/" + normalized_path
    url = f"http://{normalized_address}{normalized_path}"
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=normalized_timeout_s) as response:
            raw = response.read()
    except urlerror.URLError as exc:
        raise RuntimeError(
            f"http_post_failed:{normalized_address}:{normalized_path}:{exc}"
        ) from exc
    if not raw:
        return {}
    decoded = json.loads(raw.decode("utf-8"))
    return decoded


def _split_host_port(address: str) -> tuple[str, int]:
    normalized = _normalize_node_address(address)
    host, raw_port = normalized.rsplit(":", 1)
    return host, int(raw_port)


def _normalize_optional_node_address(raw_address: str | None) -> str | None:
    if raw_address is None:
        return None
    return _normalize_node_address(raw_address)


def _normalize_node_address(raw_address: Any) -> str:
    normalized = str(raw_address or "").strip()
    if not normalized:
        raise ValueError("node address must be non-empty.")
    if ":" not in normalized:
        normalized = f"{normalized}:{_DEFAULT_NODE_PORT}"
    host, raw_port = normalized.rsplit(":", 1)
    host = str(host or "").strip()
    if not host:
        raise ValueError("node address host must be non-empty.")
    try:
        port = int(raw_port)
    except (TypeError, ValueError) as exc:
        raise ValueError("node address port must be an integer.") from exc
    if port <= 0 or port > 65535:
        raise ValueError("node address port must be between 1 and 65535.")
    return f"{host}:{port}"


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _build_runtime_scheduler_telemetry(
    runtime_host: V1RuntimeHost,
    *,
    node_id: str,
    node_address: str,
) -> dict[str, Any]:
    backend_summary = _runtime_backend_summary(
        runtime_host,
        node_id=node_id,
        node_address=node_address,
    )
    actor_records = runtime_host.actor_api.list_local_actors()
    callback_count: int | None
    try:
        callback_count = int(runtime_host.actor_api.active_topic_callback_count())
    except RuntimeError:
        callback_count = None

    scheduler_observability = _runtime_scheduler_observability_summary(runtime_host)
    payload = {
        "schema_version": RUNTIME_TELEMETRY_SCHEMA_VERSION,
        "generated_at_ms": _now_ms(),
        "source": "flownet.runtime.node_control",
        "node": {
            "node_id": node_id,
            "node_address": node_address,
            "local_address": runtime_host.comm_hub.local_address,
            "runtime_loop_running": bool(runtime_host.runtime_loop.is_running),
            "user_loop_running": bool(runtime_host.user_loop.is_running),
            "actor_count": len(actor_records),
            "callback_count": callback_count,
            "topic_event_listener_count": runtime_host.topic_api.topic_event_listener_count(),
            "backend_count": int(backend_summary.get("backend_count", 0)),
        },
        "stream_tracker": _runtime_stream_tracker_summary(runtime_host),
        "backends": backend_summary,
        "workload_lanes": _runtime_workload_lane_summary(runtime_host),
        "scheduler_resource_fallback_rate": scheduler_observability["fallback"],
        "scheduler_spillover": scheduler_observability["spillover"],
        "governance": _runtime_governance_summary(runtime_host),
        "transport": _runtime_transport_summary(runtime_host),
    }
    return normalize_runtime_scheduler_telemetry(payload)


def _runtime_stream_tracker_summary(runtime_host: V1RuntimeHost) -> dict[str, Any]:
    topic_api = getattr(runtime_host, "topic_api", None)
    coordinator_registry = getattr(topic_api, "coordinator_registry", None)
    snapshot = getattr(coordinator_registry, "observability_snapshot", None)
    if callable(snapshot):
        try:
            raw = snapshot()
        except Exception:
            raw = {}
    else:
        raw = {}
    return normalize_runtime_stream_tracker_summary(raw)


def _runtime_backend_summary(
    runtime_host: V1RuntimeHost,
    *,
    node_id: str,
    node_address: str,
) -> dict[str, Any]:
    list_backends = getattr(runtime_host, "list_backend_containers", None)
    raw_records: tuple[dict[str, Any], ...] | list[dict[str, Any]]
    if callable(list_backends):
        try:
            raw_records = list_backends(include_metrics=True)
        except Exception:
            raw_records = ()
    else:
        raw_records = ()

    records: list[dict[str, Any]] = []
    for item in raw_records:
        if not isinstance(item, Mapping):
            continue
        row = dict(item)
        row.setdefault("node_id", node_id)
        row.setdefault("node_address", node_address)
        records.append(row)

    healthy = 0
    schedulable = 0
    queue_depth = 0
    inflight = 0
    for record in records:
        raw_metrics = record.get("metrics")
        metrics = dict(raw_metrics) if isinstance(raw_metrics, Mapping) else {}
        if bool(metrics.get("healthy")):
            healthy += 1
        if bool(metrics.get("schedulable")):
            schedulable += 1
        queue_depth += _coerce_optional_int(metrics.get("queue_depth")) or 0
        inflight += _coerce_optional_int(metrics.get("inflight")) or 0

    return {
        "records": records,
        "backend_count": len(records),
        "healthy": healthy,
        "schedulable": schedulable,
        "queue_depth": queue_depth,
        "inflight": inflight,
        "inventory": {
            "backend_ids": [str(record.get("backend_id") or "") for record in records],
            "capability_keys": sorted(
                {
                    str(key)
                    for record in records
                    for key in dict(record.get("capabilities") or {}).keys()
                    if str(key).strip()
                }
            ),
            "tag_keys": sorted(
                {
                    str(key)
                    for record in records
                    for key in dict(record.get("tags") or {}).keys()
                    if str(key).strip()
                }
            ),
            "queue_depth": queue_depth,
            "inflight": inflight,
        },
    }


def _runtime_workload_lane_summary(runtime_host: V1RuntimeHost) -> dict[str, Any]:
    actor_api = getattr(runtime_host, "actor_api", None)
    invocation_snapshot = getattr(actor_api, "invocation_observability_snapshot", None)
    executor_snapshot = getattr(actor_api, "executor_lane_observability_snapshot", None)
    raw_invocation = invocation_snapshot() if callable(invocation_snapshot) else {}
    raw_executor = executor_snapshot() if callable(executor_snapshot) else {}

    default_cpu = (
        dict(raw_executor.get("default_cpu"))
        if isinstance(raw_executor, Mapping)
        and isinstance(raw_executor.get("default_cpu"), Mapping)
        else {}
    )
    torch_dedicated = (
        dict(raw_executor.get("torch_dedicated"))
        if isinstance(raw_executor, Mapping)
        and isinstance(raw_executor.get("torch_dedicated"), Mapping)
        else {}
    )
    policy_executor_max_workers = (
        dict(default_cpu.get("policy_executor_max_workers"))
        if isinstance(default_cpu.get("policy_executor_max_workers"), Mapping)
        else {}
    )
    torch_executor_max_workers = (
        dict(torch_dedicated.get("executor_max_workers"))
        if isinstance(torch_dedicated.get("executor_max_workers"), Mapping)
        else {}
    )

    records: list[dict[str, Any]] = []
    pending = 0
    running = 0
    queued = 0
    raw_records = raw_invocation.get("records") if isinstance(raw_invocation, Mapping) else None
    if isinstance(raw_records, list):
        for item in raw_records:
            if not isinstance(item, Mapping):
                continue
            lane = str(item.get("lane") or "default_cpu").strip() or "default_cpu"
            lane_pending = _coerce_optional_int(item.get("pending")) or 0
            lane_running = _coerce_optional_int(item.get("running")) or 0
            lane_queued = _coerce_optional_int(item.get("queued")) or max(
                0, lane_pending - lane_running
            )
            worker_capacity: int | None = None
            if lane == "default_cpu":
                default_executor_workers = _coerce_optional_int(
                    default_cpu.get("executor_max_workers")
                )
                policy_worker_total = sum(
                    value
                    for value in (
                        _coerce_optional_int(raw_value)
                        for raw_value in policy_executor_max_workers.values()
                    )
                    if value is not None
                )
                if default_executor_workers is not None or policy_worker_total > 0:
                    worker_capacity = (default_executor_workers or 0) + policy_worker_total
            elif lane == "torch_dedicated":
                torch_worker_total = sum(
                    value
                    for value in (
                        _coerce_optional_int(raw_value)
                        for raw_value in torch_executor_max_workers.values()
                    )
                    if value is not None
                )
                if torch_worker_total > 0:
                    worker_capacity = torch_worker_total
            pending += lane_pending
            running += lane_running
            queued += lane_queued
            records.append(
                {
                    "lane": lane,
                    "actor_count": _coerce_optional_int(item.get("actor_count")) or 0,
                    "pending": lane_pending,
                    "running": lane_running,
                    "queued": lane_queued,
                    "worker_capacity": worker_capacity,
                }
            )

    records.sort(key=lambda item: str(item["lane"]))
    return {
        "records": records,
        "pending": pending,
        "running": running,
        "queued": queued,
    }


def _runtime_scheduler_observability_summary(runtime_host: V1RuntimeHost) -> dict[str, Any]:
    snapshot_fn = getattr(runtime_host, "scheduler_observability_snapshot", None)
    scheduler_snapshot = snapshot_fn() if callable(snapshot_fn) else {}
    process_factory_snapshot = _runtime_process_factory_summary(runtime_host)

    selection_total = (
        _coerce_optional_int(
            scheduler_snapshot.get("selection_total")
            if isinstance(scheduler_snapshot, Mapping)
            else None
        )
        or 0
    )
    scheduler_fallback_count = (
        _coerce_optional_int(
            scheduler_snapshot.get("fallback_count")
            if isinstance(scheduler_snapshot, Mapping)
            else None
        )
        or 0
    )
    factory_calls_total = (
        _coerce_optional_int(process_factory_snapshot.get("factory_calls_total")) or 0
    )
    factory_fallback_total = (
        _coerce_optional_int(process_factory_snapshot.get("factory_fallback_total")) or 0
    )

    total = selection_total + factory_calls_total
    fallback_count = scheduler_fallback_count + factory_fallback_total
    spillover = (
        dict(scheduler_snapshot.get("scheduler_spillover"))
        if isinstance(scheduler_snapshot, Mapping)
        and isinstance(scheduler_snapshot.get("scheduler_spillover"), Mapping)
        else {}
    )
    return {
        "fallback": {
            "fallback_count": fallback_count,
            "total": total,
            "rate": round((float(fallback_count) / float(total)) if total > 0 else 0.0, 6),
        },
        "spillover": spillover,
    }


def _runtime_governance_summary(runtime_host: V1RuntimeHost) -> dict[str, Any]:
    governance = getattr(runtime_host, "governance", None)
    snapshot = getattr(governance, "snapshot", None)
    if not callable(snapshot):
        return {}
    try:
        raw = snapshot()
    except Exception:
        return {}
    return dict(raw) if isinstance(raw, Mapping) else {}


def _runtime_process_factory_summary(runtime_host: V1RuntimeHost) -> dict[str, Any]:
    flow_process_execution = getattr(runtime_host, "_flow_process_execution", None)
    snapshot = getattr(flow_process_execution, "process_factory_metrics_snapshot", None)
    if callable(snapshot):
        try:
            raw = snapshot()
        except Exception:
            raw = {}
        return dict(raw) if isinstance(raw, Mapping) else {}
    return {}


def _runtime_transport_summary(runtime_host: V1RuntimeHost) -> dict[str, Any]:
    comm_hub = getattr(runtime_host, "comm_hub", None)
    transport_backend = getattr(comm_hub, "_transport", None)
    snapshot = getattr(transport_backend, "stats_snapshot", None)
    if not callable(snapshot):
        return {}
    try:
        raw = snapshot()
    except Exception:
        return {}
    if not isinstance(raw, Mapping):
        return {}
    transport = dict(raw)
    transport.setdefault("backend_type", type(transport_backend).__name__)
    transport.setdefault("source", f"flownet.runtime.transport.{type(transport_backend).__name__}")
    return transport


def _normalize_optional_non_empty(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized


def _resolve_submit_topic_binding(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        return _normalize_optional_non_empty(raw_value)
    if isinstance(raw_value, Mapping):
        for key in ("topic", "topic_uri", "topic_id", "uri", "in_topic", "out_topic"):
            candidate = _normalize_optional_non_empty(raw_value.get(key))
            if candidate is not None:
                return candidate
    candidate = _normalize_optional_non_empty(getattr(raw_value, "topic_uri", None))
    if candidate is not None:
        return candidate
    return _normalize_optional_non_empty(getattr(raw_value, "uri", None))


def _normalize_non_negative_int(value: Any, *, field_name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc
    if normalized < 0:
        raise ValueError(f"{field_name} must be >= 0.")
    return normalized


def _normalize_positive_float(value: Any, *, field_name: str) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a float.") from exc
    if normalized <= 0.0:
        raise ValueError(f"{field_name} must be > 0.")
    return normalized


def _now_ms() -> int:
    return int(time.time() * 1000.0)


def _coerce_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized


__all__ = [
    "NodeControlCaller",
    "V1MembershipNode",
    "V1NodeRuntimeService",
    "build_http_node_control_caller",
    "clear_default_node_control_caller",
    "resolve_default_node_control_caller",
    "resolve_seed_addresses",
    "set_default_node_control_caller",
]
