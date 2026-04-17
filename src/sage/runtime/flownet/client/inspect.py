from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from sage.runtime.flownet.contracts.flow_program_submit_contract import (
    normalize_flow_program_submit_accept,
)
from sage.runtime.flownet.contracts.flow_run_observation_contract import (
    normalize_flow_run_read_item,
    normalize_request_status_payload,
)
from sage.runtime.flownet.contracts.runtime_state_query_contract import (
    build_runtime_state_query_request,
    normalize_runtime_state_query_response,
)
from sage.runtime.flownet.contracts.runtime_telemetry_contract import (
    normalize_runtime_stream_tracker_summary,
    summarize_runtime_scheduler_observability,
)
from sage.runtime.flownet.runtime import V1RuntimeHost

NodeControlCaller = Callable[..., Any]

_DEFAULT_NODE_PORT = 8787


class V1RuntimeInspector:
    """
    Inspect/control facade for B2.

    This exposes:
    1) local in-process runtime snapshot via `V1RuntimeHost`;
    2) remote typed inspect/control forwarding via injected node-control caller.
    """

    def __init__(
        self,
        *,
        runtime_host: V1RuntimeHost | None = None,
        node_control_call: NodeControlCaller | None = None,
        default_node_address: str | None = None,
    ) -> None:
        self._runtime_host = runtime_host
        self._node_control_call = node_control_call
        self._default_node_address = _normalize_optional_node_address(default_node_address)

    def runtime_snapshot(self, *, include_actor_ids: bool = True) -> dict[str, Any]:
        runtime_host = self._require_runtime_host()
        actor_records = runtime_host.actor_api.list_local_actors()
        actor_ids = [record.actor_id for record in actor_records]
        endpoint_registry = getattr(runtime_host, "endpoint_registry", None)
        published_endpoint_count = 0
        if endpoint_registry is not None:
            snapshot_fn = getattr(endpoint_registry, "observability_snapshot", None)
            if callable(snapshot_fn):
                try:
                    published_endpoint_count = len(snapshot_fn(include_released=False))
                except Exception:
                    published_endpoint_count = 0
        shared_state_registry = getattr(runtime_host, "shared_state_registry", None)
        shared_state_service_count = 0
        if shared_state_registry is not None:
            snapshot_fn = getattr(shared_state_registry, "observability_snapshot", None)
            if callable(snapshot_fn):
                try:
                    shared_state_service_count = len(snapshot_fn())
                except Exception:
                    shared_state_service_count = 0
        governance = getattr(runtime_host, "governance", None)
        governance_snapshot_fn = getattr(governance, "snapshot", None)
        governance_snapshot = governance_snapshot_fn() if callable(governance_snapshot_fn) else {}
        collective_executor_snapshot = runtime_host.list_collective_executors()
        callback_count: int | None
        try:
            callback_count = int(runtime_host.actor_api.active_topic_callback_count())
        except RuntimeError:
            callback_count = None
        snapshot = {
            "schema": "v1.poc.inspect.runtime",
            "status": "poc_stub",
            "local_address": runtime_host.comm_hub.local_address,
            "runtime_loop_running": bool(runtime_host.runtime_loop.is_running),
            "user_loop_running": bool(runtime_host.user_loop.is_running),
            "actor_count": len(actor_ids),
            "published_endpoint_count": int(published_endpoint_count),
            "shared_state_service_count": int(shared_state_service_count),
            "collective_executor_count": int(
                collective_executor_snapshot.get("registration_count", 0)
            ),
            "callback_count": callback_count,
            "topic_event_listener_count": runtime_host.topic_api.topic_event_listener_count(),
            "ingress_handler_registered": runtime_host.topic_api.has_ingress_event_handler(),
            "governance": dict(governance_snapshot) if isinstance(governance_snapshot, Mapping) else {},
        }
        if include_actor_ids:
            snapshot["actor_ids"] = actor_ids
        return snapshot

    def cluster_view_snapshot(
        self,
        *,
        schema: str = "v1",
        node_address: str | None = None,
    ) -> Any:
        return self._call_node_control(
            "cluster_view_snapshot",
            schema=schema,
            node_address=node_address,
        )

    def cluster_gossip_stats(self, *, node_address: str | None = None) -> Any:
        return self._call_node_control(
            "cluster_gossip_stats",
            node_address=node_address,
        )

    def cluster_contract_snapshot(self, *, node_address: str | None = None) -> Any:
        return self._call_node_control(
            "cluster_contract_snapshot",
            node_address=node_address,
        )

    def list_runtime_topics(self, *, node_address: str | None = None) -> Any:
        return self._call_node_control(
            "list_runtime_topics",
            node_address=node_address,
        )

    def list_runtime_actors(self, *, node_address: str | None = None) -> Any:
        return self._call_node_control(
            "list_runtime_actors",
            node_address=node_address,
        )

    def list_shared_state_services(self, *, node_address: str | None = None) -> Any:
        return self._call_node_control(
            "list_shared_state_services",
            node_address=node_address,
        )

    def list_published_endpoints(self, *, node_address: str | None = None) -> Any:
        return self._call_node_control(
            "list_published_endpoints",
            node_address=node_address,
        )

    def list_collective_executors(self, *, node_address: str | None = None) -> Any:
        return self._call_node_control(
            "list_collective_executors",
            node_address=node_address,
        )

    def list_runtime_nodes(self, *, node_address: str | None = None) -> Any:
        return self._call_node_control(
            "list_runtime_nodes",
            node_address=node_address,
        )

    def list_runtime_backend_containers(
        self,
        *,
        required_tags: Mapping[str, str] | None = None,
        required_capabilities: Mapping[str, Any] | None = None,
        include_metrics: bool = True,
        node_address: str | None = None,
    ) -> Any:
        return self._call_node_control(
            "list_runtime_backend_containers",
            required_tags=_normalize_string_mapping(required_tags) or None,
            required_capabilities=dict(required_capabilities or {}) or None,
            include_metrics=bool(include_metrics),
            node_address=node_address,
        )

    def cluster_backend_container_snapshot(
        self,
        *,
        required_tags: Mapping[str, str] | None = None,
        required_capabilities: Mapping[str, Any] | None = None,
        include_metrics: bool = True,
        per_node_timeout_s: float | None = None,
        node_address: str | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "required_tags": _normalize_string_mapping(required_tags) or None,
            "required_capabilities": dict(required_capabilities or {}) or None,
            "include_metrics": bool(include_metrics),
        }
        if per_node_timeout_s is not None:
            kwargs["per_node_timeout_s"] = float(per_node_timeout_s)
        return self._call_node_control(
            "cluster_backend_container_snapshot",
            node_address=node_address,
            **kwargs,
        )

    def submit_runtime_backend_job(
        self,
        *,
        request: Mapping[str, Any],
        backend_id: str | None = None,
        required_tags: Mapping[str, str] | None = None,
        required_capabilities: Mapping[str, Any] | None = None,
        preferred_backend_id: str | None = None,
        request_epoch: int | None = None,
        node_address: str | None = None,
    ) -> Any:
        if not isinstance(request, Mapping):
            raise TypeError("request must be mapping.")
        kwargs: dict[str, Any] = {
            "request": dict(request),
            "backend_id": backend_id,
            "required_tags": _normalize_string_mapping(required_tags) or None,
            "required_capabilities": dict(required_capabilities or {}) or None,
            "preferred_backend_id": preferred_backend_id,
            "request_epoch": request_epoch,
        }
        return self._call_node_control(
            "submit_runtime_backend_job",
            node_address=node_address,
            **kwargs,
        )

    def poll_runtime_backend_job(
        self,
        job_token: str,
        *,
        auto_ack: bool = False,
        node_address: str | None = None,
    ) -> Any:
        normalized_job_token = _normalize_non_empty_string(job_token, field_name="job_token")
        return self._call_node_control(
            "poll_runtime_backend_job",
            normalized_job_token,
            auto_ack=bool(auto_ack),
            node_address=node_address,
        )

    def cancel_runtime_backend_job(
        self,
        job_token: str,
        *,
        reason: str = "",
        node_address: str | None = None,
    ) -> bool:
        normalized_job_token = _normalize_non_empty_string(job_token, field_name="job_token")
        return bool(
            self._call_node_control(
                "cancel_runtime_backend_job",
                normalized_job_token,
                reason=str(reason or ""),
                node_address=node_address,
            )
        )

    def ack_runtime_backend_job(
        self,
        job_token: str,
        *,
        node_address: str | None = None,
    ) -> bool:
        normalized_job_token = _normalize_non_empty_string(job_token, field_name="job_token")
        return bool(
            self._call_node_control(
                "ack_runtime_backend_job",
                normalized_job_token,
                node_address=node_address,
            )
        )

    def submit_flow_program(
        self,
        flow_uri: str,
        *,
        version: str | None = None,
        bindings: dict[str, Any] | None = None,
        ingress: Any = None,
        egress: Any = None,
        run_config: dict[str, Any] | None = None,
        node_address: str | None = None,
    ) -> dict[str, Any]:
        normalized_flow_uri = _normalize_non_empty_string(flow_uri, field_name="flow_uri")
        descriptor = self._call_node_control(
            "submit_flow_program_accept",
            normalized_flow_uri,
            version=version,
            bindings=bindings,
            ingress=ingress,
            egress=egress,
            run_config=run_config,
            node_address=node_address,
        )
        target_node = _resolve_submit_accept_target_node(
            descriptor,
            explicit_node_address=node_address,
            default_node_address=self._default_node_address,
        )
        return normalize_flow_program_submit_accept(
            descriptor,
            target_node=target_node,
        )

    def lookup_flow_run_descriptor(
        self,
        run_id: str,
        *,
        node_address: str | None = None,
    ) -> Any:
        normalized_run_id = _normalize_non_empty_string(run_id, field_name="run_id")
        return self._call_node_control(
            "lookup_flow_run_descriptor",
            normalized_run_id,
            node_address=node_address,
        )

    def cancel_flow_run(
        self,
        run_id: str,
        *,
        node_address: str | None = None,
    ) -> bool:
        normalized_run_id = _normalize_non_empty_string(run_id, field_name="run_id")
        return bool(
            self._call_node_control(
                "cancel_flow_run",
                normalized_run_id,
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
        normalized_run_id = _normalize_non_empty_string(run_id, field_name="run_id")
        normalized_request_id = _normalize_non_empty_string(request_id, field_name="request_id")
        status = self._call_node_control(
            "flow_run_request_delivery_status",
            normalized_run_id,
            normalized_request_id,
            node_address=node_address,
        )
        if status is None:
            return None
        return normalize_request_status_payload(
            status,
            fallback_request_id=normalized_request_id,
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
        normalized_run_id = _normalize_non_empty_string(run_id, field_name="run_id")
        normalized_request_id: str | None = None
        if request_id is not None:
            normalized_request_id = str(request_id).strip()
            if not normalized_request_id:
                raise ValueError("request_id must be a non-empty string when provided.")
        item = self._call_node_control(
            "flow_run_read",
            normalized_run_id,
            request_id=normalized_request_id,
            timeout=float(timeout),
            from_seq=from_seq,
            node_address=node_address,
        )
        return normalize_flow_run_read_item(item)

    def stream_tracker_stats(self, *, node_address: str | None = None) -> Any:
        result = self._call_node_control(
            "stream_tracker_stats",
            node_address=node_address,
        )
        return normalize_runtime_stream_tracker_summary(result)

    def stream_tracker_request_status(
        self,
        request_id: str,
        *,
        node_address: str | None = None,
    ) -> Any:
        normalized_request_id = _normalize_non_empty_string(request_id, field_name="request_id")
        status = self._call_node_control(
            "stream_tracker_request_status",
            normalized_request_id,
            node_address=node_address,
        )
        return normalize_request_status_payload(
            status,
            fallback_request_id=normalized_request_id,
        )

    def query_runtime_state(
        self,
        namespace: str,
        *,
        prefix: str,
        principal: str,
        roles: list[str] | tuple[str, ...] | set[str] | str | None = None,
        allowed_namespaces: list[str] | tuple[str, ...] | set[str] | str | None = None,
        permissions: list[str] | tuple[str, ...] | set[str] | str | None = None,
        limit: int | None = None,
        cursor: int | str | None = None,
        include_values: bool = True,
        reveal_values: bool = False,
        node_address: str | None = None,
    ) -> Any:
        request = build_runtime_state_query_request(
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
        result = self._call_node_control(
            "query_runtime_state",
            request["namespace"],
            prefix=request["prefix"],
            principal=request["principal"],
            roles=request["roles"],
            allowed_namespaces=request["allowed_namespaces"],
            permissions=request["permissions"],
            limit=request["limit"],
            cursor=request["cursor"],
            include_values=request["include_values"],
            reveal_values=request["reveal_values"],
            node_address=node_address,
        )
        return normalize_runtime_state_query_response(result)

    def scheduler_stats(self, *, node_address: str | None = None) -> dict[str, Any]:
        metrics = self._call_node_control(
            "cluster_scheduler_metrics",
            node_address=node_address,
        )
        return summarize_runtime_scheduler_observability(metrics)

    def scheduler_queue_snapshot(self, *, node_address: str | None = None) -> dict[str, int]:
        stats = self.scheduler_stats(node_address=node_address)
        return {
            "queue": int(stats.get("queue", 0)),
            "pending": int(stats.get("pending", 0)),
        }

    def scheduler_worker_snapshot(self, *, node_address: str | None = None) -> dict[str, Any]:
        stats = self.scheduler_stats(node_address=node_address)
        fallback = stats.get("fallback")
        if not isinstance(fallback, dict):
            fallback = {}
        spillover = stats.get("spillover")
        if not isinstance(spillover, dict):
            spillover = {}
        return {
            "running": int(stats.get("running", 0)),
            "inflight": int(stats.get("inflight", 0)),
            "fallback": dict(fallback),
            "spillover": dict(spillover),
        }

    def _call_node_control(
        self,
        op: str,
        *args: Any,
        node_address: str | None = None,
        **kwargs: Any,
    ) -> Any:
        node_control_call = self._node_control_call
        if not callable(node_control_call):
            raise RuntimeError("v1_node_control_caller_not_configured")
        resolved_node_address = _normalize_optional_node_address(
            node_address if node_address is not None else self._default_node_address,
        )
        if resolved_node_address is None:
            return node_control_call(op, *args, **kwargs)
        return node_control_call(
            op,
            *args,
            node_address=resolved_node_address,
            **kwargs,
        )

    def _require_runtime_host(self) -> V1RuntimeHost:
        runtime_host = self._runtime_host
        if runtime_host is None:
            raise RuntimeError("v1_runtime_host_not_configured")
        return runtime_host


def build_runtime_inspector(
    *,
    runtime_host: V1RuntimeHost | None = None,
    node_control_call: NodeControlCaller | None = None,
    default_node_address: str | None = None,
    auto_bind_runtime_node_control: bool = True,
) -> V1RuntimeInspector:
    resolved_node_control_call = node_control_call
    if resolved_node_control_call is None and auto_bind_runtime_node_control:
        resolved_node_control_call = _resolve_runtime_node_control_caller()
    return V1RuntimeInspector(
        runtime_host=runtime_host,
        node_control_call=resolved_node_control_call,
        default_node_address=default_node_address,
    )


def _resolve_runtime_node_control_caller() -> NodeControlCaller | None:
    """
    Legacy auto-bind hook for runtime inspector node-control dispatch.

    Keep this as a narrow extension point so tests and compatibility layers
    can provide a caller without requiring explicit injection everywhere.
    """
    try:
        from sage.runtime.flownet.client.node_runtime import resolve_default_node_control_caller
    except Exception:
        return None
    candidate = resolve_default_node_control_caller()
    if callable(candidate):
        return candidate
    return None


def _normalize_optional_node_address(raw_address: str | None) -> str | None:
    if raw_address is None:
        return None
    normalized = str(raw_address or "").strip()
    if not normalized:
        raise ValueError("node address must not be empty when provided.")
    if ":" in normalized:
        return normalized
    return f"{normalized}:{_DEFAULT_NODE_PORT}"


def _normalize_non_empty_string(raw_value: Any, *, field_name: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return normalized


def _normalize_string_mapping(raw_value: Any) -> dict[str, str]:
    if not isinstance(raw_value, Mapping):
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_item in raw_value.items():
        key = str(raw_key or "").strip()
        value = str(raw_item or "").strip()
        if not key or not value:
            continue
        normalized[key] = value
    return normalized


def _resolve_submit_accept_target_node(
    accept_payload: Any,
    *,
    explicit_node_address: str | None,
    default_node_address: str | None,
) -> str:
    explicit = _normalize_optional_target_node(explicit_node_address)
    if explicit is not None:
        return explicit
    default = _normalize_optional_target_node(default_node_address)
    if default is not None:
        return default

    if isinstance(accept_payload, Mapping):
        direct = _normalize_optional_target_node(
            accept_payload.get("target_node") or accept_payload.get("node_address")
        )
        if direct is not None:
            return direct
        descriptor = accept_payload.get("descriptor")
        if isinstance(descriptor, Mapping):
            nested = _normalize_optional_target_node(
                descriptor.get("target_node") or descriptor.get("node_address")
            )
            if nested is not None:
                return nested

    raise RuntimeError("submit_flow_program_accept payload missing target_node.")


def _normalize_optional_target_node(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    return _normalize_optional_node_address(normalized)


__all__ = [
    "NodeControlCaller",
    "V1RuntimeInspector",
    "build_runtime_inspector",
]
