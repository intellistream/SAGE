from __future__ import annotations

import copy
import hashlib
import json
import time
import uuid
import warnings
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Lock
from typing import Any
from weakref import WeakKeyDictionary

from sage.runtime.flownet.api.declarations import (
    ActorDeclaration,
    BoundFlowDeclaration,
    BoundFlowTemplate,
    BoundServiceDeclaration,
    BoundSourceDeclaration,
    FlowDeclaration,
    NamedFlowDeclarationRef,
    StatelessDeclaration,
)
from sage.runtime.flownet.client.handles import InstanceHandle, RegistrationHandle, ResourceKind
from sage.runtime.flownet.client.registries import SurfaceRegistry
from sage.runtime.flownet.compiler.targets import (
    coerce_actor_symbol_target,
    coerce_flow_symbol_target,
    coerce_stateless_symbol_target,
)

_BINDING_KEYS = (
    "in_topic",
    "out_topic",
    "subscriptions",
    "publish_targets",
    "name",
    "namespace",
    "selector",
    "tag",
    "mode",
    "parallelism",
    "ctor_args",
    "ctor_kwargs",
)
_FLOW_SYMBOL_MATERIALIZATION_MODES = frozenset({"caller_owned", "global_unique"})
_IO_CONTRACT_MODES = frozenset({"compat", "strict"})
_INTERNAL_BIND_HINT_KEY = "__v1_bind_hint__"

_HOST_LIFECYCLE_STATE_STORES: WeakKeyDictionary[
    object,
    dict[ResourceKind, _LifecycleStateStore],
] = WeakKeyDictionary()
_HOST_LIFECYCLE_STATE_STORES_LOCK = Lock()
_SCOPED_RUNTIME_CLIENT: ContextVar[V1RuntimeClient | None] = ContextVar(
    "flownet_v1_scoped_runtime_client",
    default=None,
)


class V1RuntimeClient:
    """
    v1 canonical client skeleton.

    Provides the frozen three-stage surface:
    declaration -> registration -> instantiation.
    """

    def __init__(
        self,
        *,
        owner: str = "local-owner",
        id_factory: Callable[[], str] | None = None,
        runtime_host: object | None = None,
        io_contract_mode: str = "compat",
    ) -> None:
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)
        self.runtime_host = runtime_host
        self._io_contract_mode = _normalize_io_contract_mode(io_contract_mode)
        self.sources = _LifecycleClientSurface(
            kind="source",
            registry=SurfaceRegistry(kind="source", owner=owner, id_factory=self._id_factory),
            id_factory=self._id_factory,
            runtime_host=runtime_host,
            client=self,
            io_contract_mode=self._io_contract_mode,
            state_store=_resolve_lifecycle_state_store(
                runtime_host=runtime_host,
                kind="source",
            ),
        )
        self.services = _LifecycleClientSurface(
            kind="service",
            registry=SurfaceRegistry(kind="service", owner=owner, id_factory=self._id_factory),
            id_factory=self._id_factory,
            runtime_host=runtime_host,
            client=self,
            io_contract_mode=self._io_contract_mode,
            state_store=_resolve_lifecycle_state_store(
                runtime_host=runtime_host,
                kind="service",
            ),
        )
        flow_registry = SurfaceRegistry(kind="flow", owner=owner, id_factory=self._id_factory)
        self.flows = _LifecycleClientSurface(
            kind="flow",
            registry=flow_registry,
            id_factory=self._id_factory,
            runtime_host=runtime_host,
            client=self,
            io_contract_mode=self._io_contract_mode,
            state_store=_resolve_lifecycle_state_store(
                runtime_host=runtime_host,
                kind="flow",
            ),
        )
        self.producers = _ClientSurface(
            kind="producer",
            registry=SurfaceRegistry(kind="producer", owner=owner, id_factory=self._id_factory),
            id_factory=self._id_factory,
            runtime_host=runtime_host,
            client=self,
            io_contract_mode=self._io_contract_mode,
        )
        self.processes = _ClientSurface(
            kind="process",
            registry=SurfaceRegistry(kind="process", owner=owner, id_factory=self._id_factory),
            id_factory=self._id_factory,
            runtime_host=runtime_host,
            client=self,
            io_contract_mode=self._io_contract_mode,
        )
        self.actors = _ClientSurface(
            kind="actor",
            registry=SurfaceRegistry(kind="actor", owner=owner, id_factory=self._id_factory),
            id_factory=self._id_factory,
            runtime_host=runtime_host,
            client=self,
            io_contract_mode=self._io_contract_mode,
        )
        self.stateless = _ClientSurface(
            kind="stateless",
            registry=SurfaceRegistry(kind="stateless", owner=owner, id_factory=self._id_factory),
            id_factory=self._id_factory,
            runtime_host=runtime_host,
            client=self,
            io_contract_mode=self._io_contract_mode,
        )

    def start_source(
        self,
        source_id: str,
        source_spec: Any,
        *,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> InstanceHandle:
        registration = self.sources.register(
            source_spec,
            uri=_normalize_non_empty(source_id, field_name="source_id"),
            metadata=metadata,
        )
        return self.sources.start(
            registration,
            config=config,
            policies=policies,
            **kwargs,
        )

    def stop_source(self, instance_or_id: InstanceHandle | str) -> bool:
        return self.sources.stop(instance_or_id)

    def list_sources(self, *, include_stopped: bool = False) -> list[dict[str, Any]]:
        records = self.sources.query(include_stopped=include_stopped)
        return records if isinstance(records, list) else []

    def query_source(
        self,
        *,
        instance_id: str | None = None,
        uri: str | None = None,
        include_stopped: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        return self.sources.query(
            instance_id=instance_id,
            uri=uri,
            include_stopped=include_stopped,
        )

    def start_service(
        self,
        service_name: str,
        service_spec: Any,
        *,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> InstanceHandle:
        registration = self.services.register(
            service_spec,
            uri=_normalize_non_empty(service_name, field_name="service_name"),
            metadata=metadata,
        )
        return self.services.start(
            registration,
            config=config,
            policies=policies,
            **kwargs,
        )

    def stop_service(self, instance_or_id: InstanceHandle | str) -> bool:
        return self.services.stop(instance_or_id)

    def unbind_flow_process(self, flow_instance_or_id: InstanceHandle | str) -> bool:
        instance_id = _normalize_instance_id(flow_instance_or_id)
        if self.runtime_host is None:
            return False

        topic_api = getattr(self.runtime_host, "topic_api", None)
        if topic_api is None:
            return False

        flow_process_uri = _build_flow_process_uri(instance_id)
        unregister_flow_process = getattr(topic_api, "unregister_flow_process", None)
        if callable(unregister_flow_process):
            return bool(unregister_flow_process(flow_process_uri=flow_process_uri))

        flow_process_catalog = getattr(topic_api, "flow_process_catalog", None)
        delete_flow_process = getattr(flow_process_catalog, "delete", None)
        if callable(delete_flow_process):
            return bool(delete_flow_process(flow_process_uri))
        return False

    def start_flow(
        self,
        flow_spec: Any,
        *,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> InstanceHandle:
        return self.flows.start(
            flow_spec,
            config=config,
            policies=policies,
            **kwargs,
        )

    def stop_flow(self, instance_or_id: InstanceHandle | str) -> bool:
        return self.flows.stop(instance_or_id)

    def list_flows(self, *, include_stopped: bool = False) -> list[dict[str, Any]]:
        records = self.flows.query(include_stopped=include_stopped)
        return records if isinstance(records, list) else []

    def query_flow(
        self,
        *,
        instance_id: str | None = None,
        uri: str | None = None,
        include_stopped: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        return self.flows.query(
            instance_id=instance_id,
            uri=uri,
            include_stopped=include_stopped,
        )

    def list_services(self, *, include_stopped: bool = False) -> list[dict[str, Any]]:
        records = self.services.query(include_stopped=include_stopped)
        return records if isinstance(records, list) else []

    def query_service(
        self,
        *,
        instance_id: str | None = None,
        uri: str | None = None,
        include_stopped: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        return self.services.query(
            instance_id=instance_id,
            uri=uri,
            include_stopped=include_stopped,
        )


@dataclass
class _EndpointRequestState:
    request_id: str
    outputs: Queue[Any] = field(default_factory=Queue)
    finished: bool = False
    released: bool = False


class FlowRequestOutcomeError(RuntimeError):
    def __init__(
        self,
        *,
        request_id: str,
        outcome_status: str,
        error_type: str | None,
        message: str | None,
        error_stage: str | None,
        outcome_metadata: dict[str, Any] | None,
        outputs: list[Any],
    ) -> None:
        normalized_message = str(message or "flow_request_failed").strip() or "flow_request_failed"
        super().__init__(
            "flow_request_failed:"
            f" request_id={request_id},"
            f" outcome_status={outcome_status},"
            f" error_type={error_type or 'RuntimeError'},"
            f" error_stage={error_stage or 'unknown'},"
            f" message={normalized_message}",
        )
        self.request_id = request_id
        self.outcome_status = outcome_status
        self.error_type = error_type
        self.message = normalized_message
        self.error_stage = error_stage
        self.outcome_metadata = dict(outcome_metadata or {})
        self.outputs = list(outputs)


class FlowRequestRef:
    def __init__(
        self,
        *,
        endpoint: FlowEndpoint,
        request_id: str,
        default_tags: Mapping[str, str] | None = None,
    ) -> None:
        self._endpoint = endpoint
        self.request_id = _normalize_non_empty(request_id, field_name="request_id")
        self._default_tags = {
            str(key): str(value) for key, value in dict(default_tags or {}).items()
        }

    def write(self, payload: Any, *, tags: Mapping[str, str] | None = None) -> dict[str, Any]:
        merged_tags = dict(self._default_tags)
        if tags is not None:
            merged_tags.update({str(key): str(value) for key, value in dict(tags).items()})
        return self._endpoint._write(self.request_id, payload=payload, tags=merged_tags)

    def read(self, *, timeout: float = 5.0) -> Any | None:
        return self._endpoint._read(self.request_id, timeout=timeout)

    def stream(self, *, timeout: float = 5.0):
        while True:
            item = self.read(timeout=timeout)
            if item is not None:
                yield item
                continue
            if self.request_done():
                return

    def finish(self) -> bool:
        return self._endpoint._finish(self.request_id)

    def status(self) -> dict[str, Any]:
        return self._endpoint._status(self.request_id)

    def request_done(self) -> bool:
        return bool(self.status().get("request_done"))

    def collect(
        self,
        *,
        timeout: float = 5.0,
        poll_interval: float = 0.05,
        raise_on_error_outcome: bool = True,
    ) -> list[Any]:
        outputs: list[Any] = []
        started = time.monotonic()
        poll = max(0.001, float(poll_interval))
        while True:
            elapsed = time.monotonic() - started
            remaining = float(timeout) - elapsed
            if remaining <= 0:
                raise TimeoutError(f"flow_request_collect_timeout:request_id={self.request_id}")
            wait_timeout = min(poll, remaining)
            item = self.read(timeout=wait_timeout)
            if item is not None:
                outputs.append(item)
                continue
            if not self.request_done():
                continue
            while True:
                tail = self.read(timeout=0.0)
                if tail is None:
                    status = self.status()
                    if raise_on_error_outcome and _status_has_error_outcome(status):
                        raise FlowRequestOutcomeError(
                            request_id=self.request_id,
                            outcome_status=str(status.get("outcome_status") or "failed"),
                            error_type=_normalize_optional_non_empty(
                                status.get("outcome_error_type")
                            ),
                            message=_normalize_optional_non_empty(
                                status.get("outcome_error_message")
                            ),
                            error_stage=_normalize_optional_non_empty(
                                status.get("outcome_error_stage")
                            ),
                            outcome_metadata=(
                                dict(status.get("outcome_metadata") or {})
                                if isinstance(status.get("outcome_metadata"), dict)
                                else None
                            ),
                            outputs=outputs,
                        )
                    return outputs
                outputs.append(tail)

    def release(self) -> bool:
        return self._endpoint._release(self.request_id)


class FlowEndpoint:
    def __init__(
        self,
        *,
        client: V1RuntimeClient,
        topic_api: Any,
        flow_instance: InstanceHandle,
        in_topic: str,
        out_topic: str,
        id_factory: Callable[[], str],
    ) -> None:
        self.client = client
        self.flow_instance = flow_instance
        self._topic_api = topic_api
        self._id_factory = id_factory
        self._requests_lock = Lock()
        self._requests: dict[str, _EndpointRequestState] = {}
        self._closed = False

        in_route = topic_api.require_topic_route(
            _normalize_non_empty(in_topic, field_name="in_topic")
        )
        out_route = topic_api.require_topic_route(
            _normalize_non_empty(out_topic, field_name="out_topic")
        )
        self.in_topic = in_route.topic_uri
        self.out_topic = out_route.topic_uri
        self._listener_id = f"v1-flow-endpoint-listener-{uuid.uuid4().hex}"
        self._topic_api.add_topic_event_listener(
            listener_id=self._listener_id,
            listener=self._on_topic_event,
        )

    def open_request(
        self,
        *,
        request_id: str | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> FlowRequestRef:
        if self._closed:
            raise RuntimeError("flow_endpoint_closed")
        if request_id is None:
            resolved_request_id = _normalize_non_empty(
                self._id_factory(),
                field_name="request_id",
            )
        else:
            resolved_request_id = _normalize_non_empty(request_id, field_name="request_id")
        with self._requests_lock:
            state = self._requests.get(resolved_request_id)
            if state is None or state.released:
                self._requests[resolved_request_id] = _EndpointRequestState(
                    request_id=resolved_request_id
                )
        return FlowRequestRef(
            endpoint=self,
            request_id=resolved_request_id,
            default_tags=tags,
        )

    def submit(
        self,
        payload: Any,
        *,
        request_id: str | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> FlowRequestRef:
        request = self.open_request(request_id=request_id, tags=tags)
        request.write(payload)
        request.finish()
        return request

    def call(
        self,
        payload: Any,
        *,
        timeout: float = 5.0,
        request_id: str | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> list[Any]:
        request = self.submit(
            payload,
            request_id=request_id,
            tags=tags,
        )
        return request.collect(timeout=timeout)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._topic_api.remove_topic_event_listener(listener_id=self._listener_id)
        with self._requests_lock:
            self._requests.clear()

    def _on_topic_event(self, event_record: dict[str, Any]) -> None:
        if not isinstance(event_record, dict):
            return
        if str(event_record.get("topic_uri") or "") != self.out_topic:
            return
        request_id = _normalize_optional_non_empty(event_record.get("event_group_id"))
        if request_id is None:
            return
        payload = event_record.get("payload")
        with self._requests_lock:
            state = self._requests.get(request_id)
            if state is None or state.released:
                return
            state.outputs.put(payload)

    def _require_request_state(self, request_id: str) -> _EndpointRequestState:
        normalized_request_id = _normalize_non_empty(request_id, field_name="request_id")
        with self._requests_lock:
            state = self._requests.get(normalized_request_id)
            if state is None or state.released:
                raise RuntimeError(f"flow_request_not_open:{normalized_request_id}")
            return state

    def _write(
        self,
        request_id: str,
        *,
        payload: Any,
        tags: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        state = self._require_request_state(request_id)
        if state.finished:
            raise RuntimeError(f"flow_request_already_finished:{request_id}")
        normalized_tags = None
        if tags is not None:
            normalized_tags = {str(key): str(value) for key, value in dict(tags).items()}
        return self._topic_api.publish_event(
            topic_uri=self.in_topic,
            event_group_id=request_id,
            payload=payload,
            tags=normalized_tags,
        )

    def _read(self, request_id: str, *, timeout: float) -> Any | None:
        state = self._require_request_state(request_id)
        timeout_value = float(timeout)
        if timeout_value <= 0:
            try:
                return state.outputs.get_nowait()
            except Empty:
                return None
        try:
            return state.outputs.get(timeout=timeout_value)
        except Empty:
            return None

    def _finish(self, request_id: str) -> bool:
        state = self._require_request_state(request_id)
        if state.finished:
            return False
        self._topic_api.producer_done(
            topic_uri=self.out_topic,
            event_group_id=request_id,
        )
        state.finished = True
        return True

    def _status(self, request_id: str) -> dict[str, Any]:
        state = self._require_request_state(request_id)
        event_chain_pending = 0
        producer_done = False
        request_done = False
        expected_total_events = None
        final_seq = None
        outcome_status = "pending"
        outcome_error_type = None
        outcome_error_message = None
        outcome_error_stage = None
        outcome_metadata: dict[str, Any] = {}
        observed_versions: list[str] = []
        version_count = 0
        mixed_version_violation = False
        ledger = None
        try:
            ledger = self._topic_api.event_group_ledger(
                topic_uri=self.out_topic,
                event_group_id=request_id,
            )
        except Exception:
            ledger = None
        if isinstance(ledger, dict):
            event_chain_pending = int(ledger.get("event_chain_pending") or 0)
            producer_done = bool(ledger.get("producer_done"))
            request_done = bool(ledger.get("request_done_emitted"))
            expected_total_events = ledger.get("expected_total_events_hint")
            final_seq = ledger.get("final_seq")
            outcome_status = (
                str(ledger.get("outcome_status") or "pending").strip().lower() or "pending"
            )
            outcome_error_type = _normalize_optional_non_empty(ledger.get("outcome_error_type"))
            outcome_error_message = _normalize_optional_non_empty(
                ledger.get("outcome_error_message")
            )
            outcome_error_stage = _normalize_optional_non_empty(ledger.get("outcome_error_stage"))
            if isinstance(ledger.get("outcome_metadata"), dict):
                outcome_metadata = dict(ledger["outcome_metadata"])
            raw_observed_versions = ledger.get("observed_versions")
            if isinstance(raw_observed_versions, (list, tuple)):
                observed_versions = [
                    str(item).strip() for item in raw_observed_versions if str(item).strip()
                ]
            version_count = int(ledger.get("version_count") or len(observed_versions))
            mixed_version_violation = bool(ledger.get("mixed_version_violation", version_count > 1))
        elif state.finished:
            producer_done = True
        return {
            "request_id": request_id,
            "request_ref_id": request_id,
            "in_topic": self.in_topic,
            "out_topic": self.out_topic,
            "producer_done": producer_done,
            "event_chain_pending": event_chain_pending,
            "event_chain_done": event_chain_pending == 0,
            "request_done": request_done,
            "expected_total_events": expected_total_events,
            "final_seq": final_seq,
            "outcome_status": outcome_status,
            "outcome_error_type": outcome_error_type,
            "outcome_error_message": outcome_error_message,
            "outcome_error_stage": outcome_error_stage,
            "outcome_metadata": outcome_metadata,
            "observed_versions": observed_versions,
            "version_count": version_count,
            "mixed_version_violation": mixed_version_violation,
            "released": bool(state.released),
        }

    def _release(self, request_id: str) -> bool:
        normalized_request_id = _normalize_non_empty(request_id, field_name="request_id")
        with self._requests_lock:
            state = self._requests.get(normalized_request_id)
            if state is None or state.released:
                return False
            state.released = True
            self._requests.pop(normalized_request_id, None)
        return True


class _ClientSurface:
    def __init__(
        self,
        *,
        kind: ResourceKind,
        registry: SurfaceRegistry,
        id_factory: Callable[[], str],
        runtime_host: object | None = None,
        client: Any | None = None,
        io_contract_mode: str = "compat",
    ) -> None:
        self._kind = kind
        self._registry = registry
        self._id_factory = id_factory
        self._runtime_host = runtime_host
        self._client = client
        self._io_contract_mode = _normalize_io_contract_mode(io_contract_mode)
        self._flow_endpoint_instance_by_key: dict[tuple[str, str, str], InstanceHandle] = {}
        self._flow_endpoint_lock = Lock()

    def register(
        self,
        declaration: Any,
        *,
        uri: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        materialization_policy_override: Mapping[str, Any] | None = None,
    ) -> RegistrationHandle:
        resolved_declaration = declaration
        if self._kind == "flow":
            resolved_declaration = _resolve_flow_registration_declaration(declaration)
        resolved_metadata = dict(metadata or {})
        if materialization_policy_override is not None:
            if self._kind != "actor":
                raise TypeError(
                    "materialization_policy_override is only supported on actors surface."
                )
            resolved_metadata["materialization_policy_override"] = _normalize_mapping(
                materialization_policy_override,
                field_name="materialization_policy_override",
            )
        return self._registry.register(
            resolved_declaration,
            uri=uri,
            metadata=resolved_metadata,
        )

    def instantiate(
        self,
        declaration_or_registration: Any,
        *,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> InstanceHandle:
        resolved_declaration_or_registration = declaration_or_registration
        instantiate_options = dict(kwargs)
        bind_hint: dict[str, Any] = {}
        if self._kind == "flow":
            resolved_declaration_or_registration, instantiate_options = (
                _resolve_flow_instantiation_inputs(
                    declaration_or_registration=declaration_or_registration,
                    raw_options=instantiate_options,
                )
            )
        elif self._kind in {"source", "service"}:
            resolved_declaration_or_registration, instantiate_options = (
                _resolve_source_service_instantiation_inputs(
                    kind=self._kind,
                    declaration_or_registration=declaration_or_registration,
                    raw_options=instantiate_options,
                )
            )
        bind_hint = _pop_internal_bind_hint(instantiate_options)
        registration, implicit_registration = self._registry.ensure_registration(
            resolved_declaration_or_registration,
        )
        bindings = _pick_bindings(instantiate_options)
        _validate_instance_binding_contract(
            kind=self._kind,
            bindings=bindings,
            io_contract_mode=self._io_contract_mode,
            bind_hint=bind_hint,
        )
        bind_hash = _compute_instance_bind_hash(
            kind=self._kind,
            registration=registration,
            bindings=bindings,
            bind_hint=bind_hint,
        )
        if bind_hash is not None:
            bindings.setdefault("bind_hash", bind_hash)
        options = dict(instantiate_options)
        instance = InstanceHandle(
            kind=self._kind,
            instance_id=_normalize_non_empty(self._id_factory(), field_name="instance_id"),
            registration=registration,
            implicit_registration=implicit_registration,
            config=_normalize_mapping(config, field_name="config"),
            policies=_normalize_mapping(policies, field_name="policies"),
            bindings=bindings,
            options=options,
        )
        self._bind_runtime_flow_process(instance=instance)
        return instance

    def endpoint(
        self,
        declaration_or_registration_or_instance_or_uri: Any,
        *,
        in_topic: str | None = None,
        out_topic: str | None = None,
        uri: str | None = None,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        reuse_existing: bool = True,
    ) -> FlowEndpoint:
        if self._kind != "flow":
            raise TypeError("endpoint is only available on flows surface.")
        if self._runtime_host is None:
            raise RuntimeError("flow_endpoint_requires_runtime_host")
        topic_api = getattr(self._runtime_host, "topic_api", None)
        if topic_api is None:
            raise RuntimeError("flow_endpoint_requires_topic_api")

        resolved_in_topic = _normalize_optional_non_empty(in_topic)
        resolved_out_topic = _normalize_optional_non_empty(out_topic)
        resolved_instance: InstanceHandle | None = None

        if isinstance(declaration_or_registration_or_instance_or_uri, InstanceHandle):
            resolved_instance = declaration_or_registration_or_instance_or_uri
            if resolved_instance.kind != "flow":
                raise TypeError("flow_endpoint_instance_kind_invalid")
            if resolved_in_topic is None:
                resolved_in_topic = _normalize_optional_non_empty(
                    resolved_instance.bindings.get("in_topic"),
                )
            if resolved_out_topic is None:
                resolved_out_topic = _normalize_optional_non_empty(
                    resolved_instance.bindings.get("out_topic"),
                )
        else:
            resolved_registration: RegistrationHandle | None = None
            declaration_for_implicit_registration: Any | None = None

            if isinstance(declaration_or_registration_or_instance_or_uri, RegistrationHandle):
                resolved_registration = declaration_or_registration_or_instance_or_uri
            elif isinstance(declaration_or_registration_or_instance_or_uri, str):
                flow_uri = _normalize_non_empty(
                    declaration_or_registration_or_instance_or_uri,
                    field_name="flow_uri",
                )
                resolved_registration = self.get_discoverable(flow_uri)
                if resolved_registration is None:
                    raise ValueError(f"flow_endpoint_flow_uri_not_registered:{flow_uri}")
            elif isinstance(
                declaration_or_registration_or_instance_or_uri, NamedFlowDeclarationRef
            ):
                named_ref = declaration_or_registration_or_instance_or_uri
                resolved_instance = self._resolve_named_flow_instance(named_ref)
                if resolved_instance is None:
                    flow_uri = _normalize_optional_non_empty(
                        getattr(named_ref.declaration, "flow_uri", None)
                    )
                    if flow_uri is None:
                        raise ValueError(
                            "flow_endpoint_named_ref_requires_flow_uri_or_running_instance:"
                            f" name={named_ref.name}",
                        )
                    resolved_registration = self.get_discoverable(flow_uri)
                    if resolved_registration is None:
                        declaration_for_implicit_registration = named_ref.declaration.compile()
                        declaration_metadata = getattr(
                            declaration_for_implicit_registration, "metadata", None
                        )
                        normalized_metadata = (
                            dict(declaration_metadata)
                            if isinstance(declaration_metadata, Mapping)
                            else None
                        )
                        resolved_registration = self.register(
                            declaration_for_implicit_registration,
                            uri=flow_uri,
                            metadata=normalized_metadata,
                        )
            elif _is_flow_program_like(declaration_or_registration_or_instance_or_uri):
                declaration_for_implicit_registration = _resolve_flow_registration_declaration(
                    declaration_or_registration_or_instance_or_uri,
                )
                resolved_uri = _normalize_optional_non_empty(uri)
                if resolved_uri is None:
                    resolved_uri = _normalize_optional_non_empty(
                        getattr(
                            declaration_or_registration_or_instance_or_uri,
                            "flow_uri",
                            None,
                        ),
                    )
                if resolved_uri is not None:
                    resolved_registration = self.get_discoverable(resolved_uri)
                    if resolved_registration is None:
                        declaration_metadata = getattr(
                            declaration_or_registration_or_instance_or_uri,
                            "metadata",
                            None,
                        )
                        normalized_metadata = (
                            dict(declaration_metadata)
                            if isinstance(declaration_metadata, Mapping)
                            else None
                        )
                        resolved_registration = self.register(
                            declaration_or_registration_or_instance_or_uri,
                            uri=resolved_uri,
                            metadata=normalized_metadata,
                        )
            else:
                raise TypeError(
                    "flow endpoint expects flow instance, registration, flow_uri, or flow declaration/program.",
                )

            if resolved_registration is not None:
                cache_key: tuple[str, str, str] | None = None
                if (
                    reuse_existing
                    and resolved_in_topic is not None
                    and resolved_out_topic is not None
                ):
                    cache_key = (
                        resolved_registration.uri,
                        resolved_in_topic,
                        resolved_out_topic,
                    )
                    with self._flow_endpoint_lock:
                        cached_instance = self._flow_endpoint_instance_by_key.get(cache_key)
                    if cached_instance is not None:
                        resolved_instance = cached_instance
                    if resolved_instance is None:
                        runtime_instance = self._resolve_existing_runtime_flow_instance(
                            registration=resolved_registration,
                            in_topic=resolved_in_topic,
                            out_topic=resolved_out_topic,
                        )
                        if runtime_instance is not None:
                            resolved_instance = runtime_instance
                            with self._flow_endpoint_lock:
                                self._flow_endpoint_instance_by_key[cache_key] = runtime_instance
                if resolved_instance is None:
                    instantiate_kwargs: dict[str, Any] = {}
                    if resolved_in_topic is not None:
                        instantiate_kwargs["in_topic"] = resolved_in_topic
                    if resolved_out_topic is not None:
                        instantiate_kwargs["out_topic"] = resolved_out_topic
                    resolved_instance = self.instantiate(
                        resolved_registration,
                        config=config,
                        policies=policies,
                        **instantiate_kwargs,
                    )
                    if cache_key is not None:
                        with self._flow_endpoint_lock:
                            self._flow_endpoint_instance_by_key[cache_key] = resolved_instance
            elif declaration_for_implicit_registration is not None:
                instantiate_kwargs = {}
                if resolved_in_topic is not None:
                    instantiate_kwargs["in_topic"] = resolved_in_topic
                if resolved_out_topic is not None:
                    instantiate_kwargs["out_topic"] = resolved_out_topic
                resolved_instance = self.instantiate(
                    declaration_for_implicit_registration,
                    config=config,
                    policies=policies,
                    **instantiate_kwargs,
                )

        if resolved_instance is None:
            raise RuntimeError("flow_endpoint_instance_resolution_failed")
        if resolved_in_topic is None:
            resolved_in_topic = _normalize_optional_non_empty(
                resolved_instance.bindings.get("in_topic"),
            )
        if resolved_out_topic is None:
            resolved_out_topic = _normalize_optional_non_empty(
                resolved_instance.bindings.get("out_topic"),
            )
        if resolved_in_topic is None or resolved_out_topic is None:
            raise ValueError("flow_endpoint_requires_in_out_topic")

        return FlowEndpoint(
            client=self._client,
            topic_api=topic_api,
            flow_instance=resolved_instance,
            in_topic=resolved_in_topic,
            out_topic=resolved_out_topic,
            id_factory=self._id_factory,
        )

    def _resolve_named_flow_instance(
        self, named_ref: NamedFlowDeclarationRef
    ) -> InstanceHandle | None:
        state_store = getattr(self, "_state_store", None)
        find_by_name = getattr(state_store, "resolve_active_by_name", None)
        if not callable(find_by_name):
            return None
        return find_by_name(
            name=named_ref.name,
            namespace=named_ref.namespace,
        )

    def _resolve_existing_runtime_flow_instance(
        self,
        *,
        registration: RegistrationHandle,
        in_topic: str,
        out_topic: str,
    ) -> InstanceHandle | None:
        if self._runtime_host is None:
            return None
        topic_api = getattr(self._runtime_host, "topic_api", None)
        if topic_api is None:
            return None
        flow_process_catalog = getattr(topic_api, "flow_process_catalog", None)
        list_flow_processes = getattr(flow_process_catalog, "list", None)
        if not callable(list_flow_processes):
            return None

        try:
            normalized_in_topic = topic_api.require_topic_route(in_topic).topic_uri
            normalized_out_topic = topic_api.require_topic_route(out_topic).topic_uri
        except Exception:
            return None

        for record in list_flow_processes():
            if str(getattr(record, "flow_program_uri", "") or "") != registration.uri:
                continue
            if str(getattr(record, "in_topic_uri", "") or "") != normalized_in_topic:
                continue
            if str(getattr(record, "out_topic_uri", "") or "") != normalized_out_topic:
                continue
            instance_id = _resolve_flow_instance_id_from_process_record(record)
            if instance_id is None:
                continue
            return InstanceHandle(
                kind="flow",
                instance_id=instance_id,
                registration=registration,
                implicit_registration=False,
                config={},
                policies={},
                bindings={
                    "in_topic": normalized_in_topic,
                    "out_topic": normalized_out_topic,
                },
                options={},
            )
        return None

    def _bind_runtime_flow_process(self, *, instance: InstanceHandle) -> None:
        if self._kind != "flow":
            return
        if self._runtime_host is None:
            return
        in_topic = _normalize_optional_non_empty(instance.bindings.get("in_topic"))
        out_topic = _normalize_optional_non_empty(instance.bindings.get("out_topic"))
        if in_topic is None or out_topic is None:
            return

        topic_api = getattr(self._runtime_host, "topic_api", None)
        if topic_api is None:
            return
        register_flow_program = getattr(topic_api, "register_flow_program", None)
        register_flow_process = getattr(topic_api, "register_flow_process", None)
        if not callable(register_flow_program) or not callable(register_flow_process):
            return

        local_address = _resolve_runtime_local_address(
            runtime_host=self._runtime_host,
            topic_api=topic_api,
        )
        if local_address is not None:
            _ensure_topic_route(
                topic_api=topic_api,
                topic_uri=in_topic,
                coordinator_address=local_address,
            )
            _ensure_topic_route(
                topic_api=topic_api,
                topic_uri=out_topic,
                coordinator_address=local_address,
            )

        flow_program_uri = _normalize_non_empty(instance.uri, field_name="flow_program_uri")
        flow_program_rev = _resolve_flow_program_rev(instance.registration)
        flow_process_uri = _build_flow_process_uri(instance.instance_id)
        materialized_flow_program = _materialize_flow_program_symbols(
            flow_program=instance.registration.declaration,
            instance=instance,
            runtime_host=self._runtime_host,
            topic_api=topic_api,
            client=self._client,
        )

        register_flow_program(
            flow_program_uri=flow_program_uri,
            flow_program_rev=flow_program_rev,
            flow_program=materialized_flow_program,
        )
        register_flow_process(
            flow_process_uri=flow_process_uri,
            flow_program_uri=flow_program_uri,
            flow_program_rev=flow_program_rev,
            in_topic_uri=in_topic,
            out_topic_uri=out_topic,
            metadata=_build_flow_process_metadata(
                instance=instance,
            ),
        )

    def get_discoverable(self, uri: str) -> RegistrationHandle | None:
        return self._registry.get_discoverable(uri)

    def list_discoverable(self) -> list[RegistrationHandle]:
        return self._registry.list_discoverable()

    def list_registrations(self) -> list[RegistrationHandle]:
        return self._registry.list_registrations()


def _build_flow_process_metadata(
    *,
    instance: InstanceHandle,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "flow_instance_id": instance.instance_id,
        "flow_uri": instance.uri,
        "owner": instance.registration.owner,
    }
    registration_metadata = getattr(instance.registration, "metadata", None)
    if isinstance(registration_metadata, Mapping):
        for key in ("namespace", "declaration_id", "definition_hash"):
            value = _normalize_optional_non_empty(registration_metadata.get(key))
            if value is not None:
                metadata[key] = value
    bind_hash = _normalize_optional_non_empty(instance.bindings.get("bind_hash"))
    if bind_hash is not None:
        metadata["bind_hash"] = bind_hash
    return metadata


@dataclass
class _LifecycleRecord:
    instance: InstanceHandle
    status: str
    started_at_epoch_ms: int
    stopped_at_epoch_ms: int | None = None


class _LifecycleStateStore:
    def __init__(self, *, kind: ResourceKind, enforce_unique_uri: bool = True) -> None:
        self._kind = kind
        self._enforce_unique_uri = bool(enforce_unique_uri)
        self._active: dict[str, _LifecycleRecord] = {}
        self._history: dict[str, _LifecycleRecord] = {}
        self._active_instance_by_uri: dict[str, str] = {}
        self._active_instance_by_name: dict[tuple[str, str], str] = {}
        self._lock = Lock()

    def start(self, *, instance: InstanceHandle) -> None:
        started_at_epoch_ms = _now_epoch_ms()
        with self._lock:
            if self._enforce_unique_uri:
                running_instance_id = self._active_instance_by_uri.get(instance.uri)
                if running_instance_id is not None:
                    raise ValueError(f"{self._kind}_uri_already_started:{instance.uri}")
            scoped_name = _resolve_scoped_instance_name(instance.bindings)
            if scoped_name is not None:
                existing_name_instance = self._active_instance_by_name.get(scoped_name)
                if existing_name_instance is not None:
                    raise ValueError(
                        f"{self._kind}_name_already_started:namespace={scoped_name[0]} name={scoped_name[1]}",
                    )
            record = _LifecycleRecord(
                instance=instance,
                status="running",
                started_at_epoch_ms=started_at_epoch_ms,
            )
            self._active[instance.instance_id] = record
            self._history[instance.instance_id] = record
            self._active_instance_by_uri[instance.uri] = instance.instance_id
            if scoped_name is not None:
                self._active_instance_by_name[scoped_name] = instance.instance_id

    def stop(self, instance_or_id: InstanceHandle | str) -> bool:
        instance_id = _normalize_instance_id(instance_or_id)
        with self._lock:
            record = self._active.pop(instance_id, None)
            if record is None:
                return False
            if self._active_instance_by_uri.get(record.instance.uri) == instance_id:
                self._active_instance_by_uri.pop(record.instance.uri, None)
            scoped_name = _resolve_scoped_instance_name(record.instance.bindings)
            if (
                scoped_name is not None
                and self._active_instance_by_name.get(scoped_name) == instance_id
            ):
                self._active_instance_by_name.pop(scoped_name, None)
            record.status = "stopped"
            record.stopped_at_epoch_ms = _now_epoch_ms()
        return True

    def query(
        self,
        *,
        instance_id: str | None = None,
        uri: str | None = None,
        include_stopped: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        if instance_id is not None and uri is not None:
            raise ValueError("query expects at most one selector: `instance_id` or `uri`.")

        if instance_id is not None:
            normalized_instance_id = _normalize_non_empty(
                instance_id,
                field_name="instance_id",
            )
            with self._lock:
                record = self._active.get(normalized_instance_id)
                if record is None and include_stopped:
                    record = self._history.get(normalized_instance_id)
            if record is None:
                return None
            return _lifecycle_snapshot(record)

        if uri is not None:
            normalized_uri = _normalize_non_empty(uri, field_name="uri")
            with self._lock:
                records = [
                    record
                    for record in self._history.values()
                    if record.instance.uri == normalized_uri
                ]
            if not include_stopped:
                records = [record for record in records if record.status == "running"]
            records.sort(key=lambda item: item.started_at_epoch_ms)
            return [_lifecycle_snapshot(record) for record in records]

        with self._lock:
            records = (
                list(self._history.values()) if include_stopped else list(self._active.values())
            )
        records.sort(key=lambda item: item.started_at_epoch_ms)
        return [_lifecycle_snapshot(record) for record in records]

    def resolve_active_by_name(
        self,
        *,
        name: str,
        namespace: str | None = None,
    ) -> InstanceHandle | None:
        normalized_name = _normalize_non_empty(name, field_name="name")
        normalized_namespace = _normalize_optional_non_empty(namespace) or "default"
        key = (normalized_namespace, normalized_name)
        with self._lock:
            instance_id = self._active_instance_by_name.get(key)
            if instance_id is None:
                return None
            record = self._active.get(instance_id)
            if record is None:
                return None
            return record.instance

    def resolve_active_by_tag(
        self,
        *,
        tag: str,
        namespace: str | None = None,
    ) -> list[InstanceHandle]:
        normalized_tag = _normalize_non_empty(tag, field_name="tag")
        normalized_namespace = _normalize_optional_non_empty(namespace) or "default"
        with self._lock:
            active_records = list(self._active.values())
        active_records.sort(key=lambda item: item.started_at_epoch_ms)
        matched: list[InstanceHandle] = []
        for record in active_records:
            if _resolve_instance_namespace(record.instance.bindings) != normalized_namespace:
                continue
            if _instance_matches_locate_tag(record.instance, normalized_tag):
                matched.append(record.instance)
        return matched


class _LifecycleClientSurface(_ClientSurface):
    """
    Source/service lifecycle surface draft.

    `start` keeps three-stage semantics by delegating to instantiate first.
    """

    def __init__(
        self,
        *,
        kind: ResourceKind,
        registry: SurfaceRegistry,
        id_factory: Callable[[], str],
        runtime_host: object | None,
        client: Any | None,
        io_contract_mode: str,
        state_store: _LifecycleStateStore,
    ) -> None:
        super().__init__(
            kind=kind,
            registry=registry,
            id_factory=id_factory,
            runtime_host=runtime_host,
            client=client,
            io_contract_mode=io_contract_mode,
        )
        self._state_store = state_store

    def start(
        self,
        declaration_or_registration: Any,
        *,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> InstanceHandle:
        instance = self.instantiate(
            declaration_or_registration,
            config=config,
            policies=policies,
            **kwargs,
        )
        self._state_store.start(instance=instance)
        return instance

    def stop(self, instance_or_id: InstanceHandle | str) -> bool:
        stopped = self._state_store.stop(instance_or_id)
        if not stopped:
            return False
        if self._kind == "flow" and self._client is not None:
            unbind = getattr(self._client, "unbind_flow_process", None)
            if callable(unbind):
                try:
                    unbind(instance_or_id)
                except Exception:
                    pass
        return True

    def query(
        self,
        *,
        instance_id: str | None = None,
        uri: str | None = None,
        include_stopped: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        return self._state_store.query(
            instance_id=instance_id,
            uri=uri,
            include_stopped=include_stopped,
        )

    def find(
        self,
        *,
        name: str,
        namespace: str | None = None,
        selector: str | None = None,
    ) -> InstanceHandle | None:
        normalized_selector = _normalize_optional_non_empty(selector) or "find"
        if normalized_selector == "locate":
            candidates = self._state_store.resolve_active_by_tag(
                tag=name,
                namespace=namespace,
            )
            if not candidates:
                return None
            if len(candidates) > 1:
                resolved_namespace = _normalize_optional_non_empty(namespace) or "default"
                raise ValueError(
                    f"{self._kind}_locate_requires_single_target_resolution:"
                    f" namespace={resolved_namespace} tag={name} matches={len(candidates)}",
                )
            return candidates[0]
        return self._state_store.resolve_active_by_name(
            name=name,
            namespace=namespace,
        )

    def locate(
        self,
        *,
        tag: str,
        namespace: str | None = None,
    ) -> list[InstanceHandle]:
        return self._state_store.resolve_active_by_tag(
            tag=tag,
            namespace=namespace,
        )


def _resolve_flow_registration_declaration(declaration: Any) -> Any:
    if isinstance(declaration, BoundFlowTemplate):
        declaration = declaration.bind()
    if isinstance(declaration, BoundFlowDeclaration):
        return declaration.flow_program
    if isinstance(declaration, FlowDeclaration):
        return declaration.compile()
    if isinstance(declaration, NamedFlowDeclarationRef):
        return declaration.declaration.compile()
    return declaration


def _resolve_flow_instantiation_inputs(
    *,
    declaration_or_registration: Any,
    raw_options: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    options = dict(raw_options)
    if isinstance(declaration_or_registration, BoundFlowTemplate):
        declaration_or_registration = declaration_or_registration.bind()
    if isinstance(declaration_or_registration, BoundFlowDeclaration):
        resolved_in = _resolve_topic_binding_option(options.get("in_topic"))
        resolved_out = _resolve_topic_binding_option(options.get("out_topic"))
        if resolved_in is None:
            resolved_in = _resolve_topic_binding_option(declaration_or_registration.in_binding)
        if resolved_out is None:
            resolved_out = _resolve_topic_binding_option(declaration_or_registration.out_binding)
        if resolved_in is not None:
            options["in_topic"] = resolved_in
        if resolved_out is not None:
            options["out_topic"] = resolved_out
        options[_INTERNAL_BIND_HINT_KEY] = {
            "kind": "bound_flow",
            "flow_args": list(declaration_or_registration.flow_args),
            "flow_kwargs": dict(declaration_or_registration.flow_kwargs),
            "io_declared": (
                declaration_or_registration.in_binding is not None
                or declaration_or_registration.out_binding is not None
            ),
        }
        return declaration_or_registration.flow_program, options
    if isinstance(declaration_or_registration, NamedFlowDeclarationRef):
        options.setdefault("name", declaration_or_registration.name)
        if declaration_or_registration.namespace is not None:
            options.setdefault("namespace", declaration_or_registration.namespace)
        options.setdefault("selector", declaration_or_registration.selector)
        return declaration_or_registration.declaration.compile(), options
    if isinstance(declaration_or_registration, FlowDeclaration):
        return declaration_or_registration.compile(), options
    return declaration_or_registration, options


def _resolve_source_service_instantiation_inputs(
    *,
    kind: ResourceKind,
    declaration_or_registration: Any,
    raw_options: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    options = dict(raw_options)
    if kind == "source" and isinstance(declaration_or_registration, BoundSourceDeclaration):
        resolved_out = _resolve_topic_binding_option(options.get("out_topic"))
        if resolved_out is None:
            resolved_out = _resolve_topic_binding_option(declaration_or_registration.out_binding)
        if resolved_out is not None:
            options["out_topic"] = resolved_out
        options[_INTERNAL_BIND_HINT_KEY] = {
            "kind": "bound_source",
            "io_declared": declaration_or_registration.out_binding is not None,
        }
        return declaration_or_registration.declaration, options

    if kind == "service" and isinstance(declaration_or_registration, BoundServiceDeclaration):
        resolved_in = _resolve_topic_binding_option(options.get("in_topic"))
        resolved_out = _resolve_topic_binding_option(options.get("out_topic"))
        if resolved_in is None:
            resolved_in = _resolve_topic_binding_option(declaration_or_registration.in_binding)
        if resolved_out is None:
            resolved_out = _resolve_topic_binding_option(declaration_or_registration.out_binding)
        if resolved_in is not None:
            options["in_topic"] = resolved_in
        if resolved_out is not None:
            options["out_topic"] = resolved_out
        options[_INTERNAL_BIND_HINT_KEY] = {
            "kind": "bound_service",
            "io_declared": (
                declaration_or_registration.in_binding is not None
                or declaration_or_registration.out_binding is not None
            ),
        }
        return declaration_or_registration.declaration, options

    return declaration_or_registration, options


def _resolve_topic_binding_option(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        return _normalize_optional_non_empty(raw_value)
    if isinstance(raw_value, Mapping):
        for key in ("topic", "topic_uri", "uri"):
            candidate = _normalize_optional_non_empty(raw_value.get(key))
            if candidate is not None:
                return candidate
    candidate = _normalize_optional_non_empty(getattr(raw_value, "topic_uri", None))
    if candidate is not None:
        return candidate
    return _normalize_optional_non_empty(getattr(raw_value, "uri", None))


def _pick_bindings(raw_options: dict[str, Any]) -> dict[str, Any]:
    bindings: dict[str, Any] = {}
    for key in _BINDING_KEYS:
        if key in raw_options:
            bindings[key] = raw_options.pop(key)
    return bindings


def _pop_internal_bind_hint(raw_options: dict[str, Any]) -> dict[str, Any]:
    raw_hint = raw_options.pop(_INTERNAL_BIND_HINT_KEY, None)
    if not isinstance(raw_hint, Mapping):
        return {}
    return dict(raw_hint)


def _normalize_io_contract_mode(raw_mode: Any) -> str:
    normalized = str(raw_mode or "compat").strip().lower() or "compat"
    if normalized not in _IO_CONTRACT_MODES:
        raise ValueError(
            "io_contract_mode must be one of: compat, strict.",
        )
    return normalized


def _validate_instance_binding_contract(
    *,
    kind: ResourceKind,
    bindings: Mapping[str, Any],
    io_contract_mode: str,
    bind_hint: Mapping[str, Any],
) -> None:
    normalized_mode = _normalize_io_contract_mode(io_contract_mode)

    in_topic = _normalize_optional_non_empty(bindings.get("in_topic"))
    out_topic = _normalize_optional_non_empty(bindings.get("out_topic"))
    has_ingress = in_topic is not None or _has_binding_collection(bindings.get("subscriptions"))
    has_egress = out_topic is not None or _has_binding_collection(bindings.get("publish_targets"))

    if kind == "flow":
        if (in_topic is None) != (out_topic is None):
            raise ValueError("flow_io_contract_requires_in_out_topic_pair")
        if (
            _normalize_optional_non_empty(bind_hint.get("kind")) == "bound_flow"
            and bool(bind_hint.get("io_declared"))
            and (in_topic is None or out_topic is None)
        ):
            raise ValueError("flow_bound_io_contract_requires_resolvable_in_out_topic_pair")
        return

    if kind == "source":
        if has_egress:
            return
        _handle_io_contract_violation(
            mode=normalized_mode,
            error_code="source_io_contract_requires_egress_binding",
            warning_message=(
                "source_start_without_egress_binding_deprecated:"
                " provide out_topic or publish_targets."
            ),
        )
        return

    if kind == "service":
        if has_ingress or has_egress:
            return
        _handle_io_contract_violation(
            mode=normalized_mode,
            error_code="service_io_contract_requires_ingress_or_egress_binding",
            warning_message=(
                "service_start_without_io_binding_deprecated:"
                " provide in_topic/subscriptions and/or out_topic/publish_targets."
            ),
        )
        return


def _handle_io_contract_violation(
    *,
    mode: str,
    error_code: str,
    warning_message: str,
) -> None:
    if mode == "strict":
        raise ValueError(error_code)
    warnings.warn(
        warning_message,
        category=DeprecationWarning,
        stacklevel=4,
    )


def _has_binding_collection(raw_value: Any) -> bool:
    if raw_value is None:
        return False
    if isinstance(raw_value, str):
        return _normalize_optional_non_empty(raw_value) is not None
    if isinstance(raw_value, Mapping):
        return bool(raw_value)
    if isinstance(raw_value, (list, tuple, set, frozenset)):
        return any(_normalize_optional_non_empty(item) is not None for item in raw_value)
    return True


def _compute_instance_bind_hash(
    *,
    kind: ResourceKind,
    registration: RegistrationHandle,
    bindings: Mapping[str, Any],
    bind_hint: Mapping[str, Any],
) -> str | None:
    normalized_bindings = {
        str(key): value for key, value in bindings.items() if str(key) != "bind_hash"
    }
    normalized_hint = {
        str(key): value
        for key, value in dict(bind_hint).items()
        if str(key) in {"kind", "flow_args", "flow_kwargs", "io_declared"}
    }
    if not normalized_bindings and not _bind_hint_has_payload(normalized_hint):
        return None

    payload = {
        "kind": kind,
        "uri": registration.uri,
        "declaration_id": _normalize_optional_non_empty(
            registration.metadata.get("declaration_id")
        ),
        "definition_hash": _normalize_optional_non_empty(
            registration.metadata.get("definition_hash")
        ),
        "bindings": _canonicalize_flow_value_for_digest(
            normalized_bindings,
            transformation_index={},
        ),
        "bind_hint": _canonicalize_flow_value_for_digest(
            normalized_hint,
            transformation_index={},
        ),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def _bind_hint_has_payload(bind_hint: Mapping[str, Any]) -> bool:
    if not bind_hint:
        return False
    flow_args = bind_hint.get("flow_args")
    flow_kwargs = bind_hint.get("flow_kwargs")
    if isinstance(flow_args, (list, tuple)) and flow_args:
        return True
    if isinstance(flow_kwargs, Mapping) and flow_kwargs:
        return True
    return bool(bind_hint.get("io_declared"))


def _normalize_mapping(
    raw_value: Mapping[str, Any] | None,
    *,
    field_name: str,
) -> dict[str, Any]:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, Mapping):
        raise TypeError(f"{field_name} must be a mapping when provided.")
    return dict(raw_value)


def _normalize_string_mapping(
    raw_value: Any,
    *,
    field_name: str,
) -> dict[str, str]:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, Mapping):
        raise TypeError(f"{field_name} must be a mapping when provided.")
    normalized: dict[str, str] = {}
    for raw_key, raw_item in raw_value.items():
        key = _normalize_optional_non_empty(raw_key)
        value = _normalize_optional_non_empty(raw_item)
        if key is None or value is None:
            continue
        normalized[key] = value
    return normalized


def _resolve_flow_program_rev(registration: RegistrationHandle) -> str:
    return _resolve_program_rev_from_metadata(
        registration_metadata=registration.metadata,
        declaration=getattr(registration, "declaration", None),
    )


def _resolve_program_rev_from_metadata(
    *,
    registration_metadata: Mapping[str, Any] | None,
    declaration: Any | None,
) -> str:
    metadata_candidates = (
        registration_metadata,
        getattr(declaration, "metadata", None),
    )
    for metadata in metadata_candidates:
        if not isinstance(metadata, Mapping):
            continue
        for key in ("flow_program_rev", "program_rev", "version"):
            candidate = _normalize_optional_non_empty(metadata.get(key))
            if candidate is not None:
                return candidate
    return "v1"


def _build_flow_process_uri(instance_id: str) -> str:
    return f"flowprocess://{_normalize_non_empty(instance_id, field_name='instance_id')}"


def _resolve_flow_instance_id_from_process_record(record: Any) -> str | None:
    metadata = getattr(record, "metadata", None)
    if isinstance(metadata, Mapping):
        instance_id = _normalize_optional_non_empty(metadata.get("flow_instance_id"))
        if instance_id is not None:
            return instance_id

    flow_process_uri = _normalize_optional_non_empty(getattr(record, "flow_process_uri", None))
    if flow_process_uri is None:
        return None
    prefix = "flowprocess://"
    if not flow_process_uri.startswith(prefix):
        return None
    return _normalize_optional_non_empty(flow_process_uri[len(prefix) :])


def _resolve_runtime_local_address(*, runtime_host: object, topic_api: object) -> str | None:
    comm_hub = getattr(runtime_host, "comm_hub", None)
    if comm_hub is not None:
        local_address = _normalize_optional_non_empty(getattr(comm_hub, "local_address", None))
        if local_address is not None:
            return local_address

    local_address_resolver = getattr(topic_api, "_local_address", None)
    if callable(local_address_resolver):
        try:
            return _normalize_optional_non_empty(local_address_resolver())
        except Exception:
            return None
    return None


def _ensure_topic_route(
    *,
    topic_api: object,
    topic_uri: str,
    coordinator_address: str,
) -> None:
    routing_directory = getattr(topic_api, "routing_directory", None)
    if routing_directory is None:
        return
    resolve = getattr(routing_directory, "resolve", None)
    upsert_route = getattr(routing_directory, "upsert_route", None)
    if not callable(resolve) or not callable(upsert_route):
        return
    existing = resolve(topic_uri)
    if existing is not None:
        return
    upsert_route(
        topic_uri=topic_uri,
        coordinator_address=coordinator_address,
        epoch=1,
    )


def _materialize_flow_program_symbols(
    *,
    flow_program: Any,
    instance: InstanceHandle,
    runtime_host: object,
    topic_api: object,
    client: Any | None,
    materialized_flow_program_keys: set[tuple[str, str]] | None = None,
) -> Any:
    transformations = _resolve_flow_transformations(flow_program)
    if not transformations:
        return flow_program
    if materialized_flow_program_keys is None:
        materialized_flow_program_keys = set()

    contains_any_symbolic_target = False
    contains_actor_symbolic_target = False
    for transformation in transformations:
        targets_to_scan: list[Any] = [getattr(transformation, "target", None)]
        operator_config = getattr(transformation, "operator_config", None)
        if isinstance(operator_config, dict):
            loop_meta = operator_config.get("loop")
            if isinstance(loop_meta, dict):
                targets_to_scan.append(loop_meta.get("condition"))
                targets_to_scan.append(loop_meta.get("body"))
        handler_stack = getattr(transformation, "exception_handler_stack", None)
        if isinstance(handler_stack, list):
            targets_to_scan.extend(list(handler_stack))

        for raw_target in targets_to_scan:
            if _is_symbolic_target(raw_target):
                contains_any_symbolic_target = True
            if _coerce_symbolic_actor_ref(raw_target) is not None:
                contains_actor_symbolic_target = True
        if contains_any_symbolic_target and contains_actor_symbolic_target:
            break

    if not contains_any_symbolic_target:
        return flow_program

    actor_api: Any | None = None
    local_address: str | None = None
    if contains_actor_symbolic_target:
        actor_api = getattr(runtime_host, "actor_api", None)
        if actor_api is None:
            raise RuntimeError("flow_symbolic_actor_materialization_requires_actor_api")
        local_address = _resolve_runtime_local_address(
            runtime_host=runtime_host, topic_api=topic_api
        )
        if local_address is None:
            raise RuntimeError("flow_symbolic_actor_materialization_requires_local_address")

    materialized_program = copy.deepcopy(flow_program)
    materialized_transformations = _resolve_flow_transformations(materialized_program)
    actor_ids_by_symbol_key: dict[str, tuple[str, ...]] = {}
    policy_fingerprint_by_symbol_key: dict[str, str] = {}
    stateless_callable_by_uri: dict[str, Any] = {}
    flow_program_ref_by_key: dict[str, dict[str, str]] = {}
    for transformation in materialized_transformations:
        transformation.target = _materialize_symbolic_target(
            target=transformation.target,
            instance=instance,
            client=client,
            runtime_host=runtime_host,
            topic_api=topic_api,
            actor_api=actor_api,
            local_address=local_address,
            actor_ids_by_symbol_key=actor_ids_by_symbol_key,
            policy_fingerprint_by_symbol_key=policy_fingerprint_by_symbol_key,
            stateless_callable_by_uri=stateless_callable_by_uri,
            flow_program_ref_by_key=flow_program_ref_by_key,
            materialized_flow_program_keys=materialized_flow_program_keys,
        )

        operator_config = getattr(transformation, "operator_config", None)
        if isinstance(operator_config, dict):
            loop_meta = operator_config.get("loop")
            if isinstance(loop_meta, dict):
                loop_meta["condition"] = _materialize_symbolic_target(
                    target=loop_meta.get("condition"),
                    instance=instance,
                    client=client,
                    runtime_host=runtime_host,
                    topic_api=topic_api,
                    actor_api=actor_api,
                    local_address=local_address,
                    actor_ids_by_symbol_key=actor_ids_by_symbol_key,
                    policy_fingerprint_by_symbol_key=policy_fingerprint_by_symbol_key,
                    stateless_callable_by_uri=stateless_callable_by_uri,
                    flow_program_ref_by_key=flow_program_ref_by_key,
                    materialized_flow_program_keys=materialized_flow_program_keys,
                )
                loop_meta["body"] = _materialize_symbolic_target(
                    target=loop_meta.get("body"),
                    instance=instance,
                    client=client,
                    runtime_host=runtime_host,
                    topic_api=topic_api,
                    actor_api=actor_api,
                    local_address=local_address,
                    actor_ids_by_symbol_key=actor_ids_by_symbol_key,
                    policy_fingerprint_by_symbol_key=policy_fingerprint_by_symbol_key,
                    stateless_callable_by_uri=stateless_callable_by_uri,
                    flow_program_ref_by_key=flow_program_ref_by_key,
                    materialized_flow_program_keys=materialized_flow_program_keys,
                )
        handler_stack = getattr(transformation, "exception_handler_stack", None)
        if isinstance(handler_stack, list):
            for index, handler in enumerate(list(handler_stack)):
                handler_stack[index] = _materialize_symbolic_target(
                    target=handler,
                    instance=instance,
                    client=client,
                    runtime_host=runtime_host,
                    topic_api=topic_api,
                    actor_api=actor_api,
                    local_address=local_address,
                    actor_ids_by_symbol_key=actor_ids_by_symbol_key,
                    policy_fingerprint_by_symbol_key=policy_fingerprint_by_symbol_key,
                    stateless_callable_by_uri=stateless_callable_by_uri,
                    flow_program_ref_by_key=flow_program_ref_by_key,
                    materialized_flow_program_keys=materialized_flow_program_keys,
                )
    return materialized_program


def _is_symbolic_target(target: Any) -> bool:
    if _coerce_symbolic_actor_ref(target) is not None:
        return True
    if _coerce_symbolic_stateless_ref(target) is not None:
        return True
    if _coerce_symbolic_flow_ref(target) is not None:
        return True
    return False


def _materialize_symbolic_target(
    *,
    target: Any,
    instance: InstanceHandle,
    client: Any | None,
    runtime_host: object,
    topic_api: object,
    actor_api: Any | None,
    local_address: str | None,
    actor_ids_by_symbol_key: dict[str, tuple[str, ...]],
    policy_fingerprint_by_symbol_key: dict[str, str],
    stateless_callable_by_uri: dict[str, Any],
    flow_program_ref_by_key: dict[str, dict[str, str]],
    materialized_flow_program_keys: set[tuple[str, str]],
) -> Any:
    actor_symbolic_ref = _coerce_symbolic_actor_ref(target)
    if actor_symbolic_ref is not None:
        if actor_api is None:
            raise RuntimeError("flow_symbolic_actor_materialization_requires_actor_api")
        if local_address is None:
            raise RuntimeError("flow_symbolic_actor_materialization_requires_local_address")
        return _materialize_symbolic_actor_target(
            symbolic_ref=actor_symbolic_ref,
            instance=instance,
            client=client,
            actor_api=actor_api,
            local_address=local_address,
            actor_ids_by_symbol_key=actor_ids_by_symbol_key,
            policy_fingerprint_by_symbol_key=policy_fingerprint_by_symbol_key,
        )

    stateless_symbolic_ref = _coerce_symbolic_stateless_ref(target)
    if stateless_symbolic_ref is not None:
        return _materialize_symbolic_stateless_target(
            symbolic_ref=stateless_symbolic_ref,
            client=client,
            stateless_callable_by_uri=stateless_callable_by_uri,
        )

    flow_symbolic_ref = _coerce_symbolic_flow_ref(target)
    if flow_symbolic_ref is not None:
        return _materialize_symbolic_flow_target(
            symbolic_ref=flow_symbolic_ref,
            instance=instance,
            client=client,
            runtime_host=runtime_host,
            topic_api=topic_api,
            flow_program_ref_by_key=flow_program_ref_by_key,
            materialized_flow_program_keys=materialized_flow_program_keys,
        )

    return target


def _materialize_symbolic_actor_target(
    *,
    symbolic_ref: dict[str, Any],
    instance: InstanceHandle,
    client: Any | None,
    actor_api: Any,
    local_address: str,
    actor_ids_by_symbol_key: dict[str, tuple[str, ...]],
    policy_fingerprint_by_symbol_key: dict[str, str],
) -> Any:
    actor_uri = _normalize_non_empty(symbolic_ref["actor_uri"], field_name="actor_uri")
    method = _normalize_non_empty(symbolic_ref["method"], field_name="method")
    bind_args, bind_kwargs = _normalize_symbolic_bind_payload(symbolic_ref.get("bind"))
    named_ref = _normalize_optional_non_empty(symbolic_ref.get("name"))
    namespace = _normalize_optional_non_empty(symbolic_ref.get("namespace"))
    selector = _normalize_optional_non_empty(symbolic_ref.get("selector"))
    declaration = _resolve_actor_declaration_for_symbol(
        actor_uri=actor_uri,
        symbolic_ref=symbolic_ref,
        client=client,
    )
    registration_metadata = _resolve_actor_registration_metadata(
        actor_uri=actor_uri,
        declaration=declaration,
        client=client,
    )
    policy = _resolve_materialization_policy(
        declaration=declaration,
        registration_metadata=registration_metadata,
        symbolic_ref=symbolic_ref,
    )
    symbol_key = _build_symbolic_actor_key(
        actor_uri=actor_uri,
        bind_args=bind_args,
        bind_kwargs=bind_kwargs,
        name=named_ref,
        namespace=namespace,
        selector=selector,
    )
    policy_fingerprint = _materialization_policy_fingerprint(policy)
    cached_fingerprint = policy_fingerprint_by_symbol_key.get(symbol_key)
    if cached_fingerprint is None:
        policy_fingerprint_by_symbol_key[symbol_key] = policy_fingerprint
    elif cached_fingerprint != policy_fingerprint:
        raise ValueError(
            f"actor_materialization_policy_conflict: actor_uri={actor_uri} symbol_key={symbol_key}",
        )

    actor_ids = actor_ids_by_symbol_key.get(symbol_key)
    if actor_ids is None:
        actor_ids = _register_materialized_local_actor_replicas(
            actor_api=actor_api,
            declaration=declaration,
            policy=policy,
            instance_id=instance.instance_id,
            actor_uri=actor_uri,
            bind_args=bind_args,
            bind_kwargs=bind_kwargs,
            name=named_ref,
            namespace=namespace,
            selector=selector,
        )
        actor_ids_by_symbol_key[symbol_key] = actor_ids
    return _build_materialized_actor_target(
        local_address=local_address,
        actor_uri=actor_uri,
        symbol_key=symbol_key,
        actor_ids=actor_ids,
        method=method,
    )


def _normalize_symbolic_bind_payload(raw_bind: Any) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if not isinstance(raw_bind, Mapping):
        return (), {}
    raw_args = raw_bind.get("args")
    raw_kwargs = raw_bind.get("kwargs")

    normalized_args: tuple[Any, ...]
    if isinstance(raw_args, (list, tuple)):
        normalized_args = tuple(raw_args)
    else:
        normalized_args = ()

    normalized_kwargs: dict[str, Any]
    if isinstance(raw_kwargs, Mapping):
        normalized_kwargs = dict(raw_kwargs)
    else:
        normalized_kwargs = {}
    return normalized_args, normalized_kwargs


def _build_symbolic_actor_key(
    *,
    actor_uri: str,
    bind_args: tuple[Any, ...],
    bind_kwargs: Mapping[str, Any],
    name: str | None,
    namespace: str | None,
    selector: str | None,
) -> str:
    payload = {
        "actor_uri": actor_uri,
        "bind": {
            "args": _canonicalize_flow_value_for_digest(bind_args, transformation_index={}),
            "kwargs": _canonicalize_flow_value_for_digest(bind_kwargs, transformation_index={}),
        },
        "name": name,
        "namespace": namespace,
        "selector": selector,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def _compute_symbolic_bind_hash(bind_args: tuple[Any, ...], bind_kwargs: Mapping[str, Any]) -> str:
    payload = {
        "args": _canonicalize_flow_value_for_digest(bind_args, transformation_index={}),
        "kwargs": _canonicalize_flow_value_for_digest(bind_kwargs, transformation_index={}),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def _materialization_policy_fingerprint(policy: Mapping[str, Any]) -> str:
    canonical_payload = _canonicalize_flow_value_for_digest(
        dict(policy),
        transformation_index={},
    )
    encoded = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def _build_materialized_actor_target(
    *,
    local_address: str,
    actor_uri: str,
    symbol_key: str,
    actor_ids: tuple[str, ...],
    method: str,
) -> dict[str, Any]:
    if len(actor_ids) == 1:
        return {
            "address": local_address,
            "actor_id": actor_ids[0],
            "method": method,
        }
    replicas = [
        {
            "address": local_address,
            "actor_id": actor_id,
        }
        for actor_id in actor_ids
    ]
    return {
        "kind": "actor_replica_pool_ref",
        "actor_uri": actor_uri,
        "symbol_key": symbol_key,
        "method": method,
        "replicas": replicas,
    }


def _build_named_actor_id(
    *,
    prefix: str,
    name: str | None,
    namespace: str | None,
    selector: str | None,
) -> str | None:
    normalized_name = _normalize_optional_non_empty(name)
    if normalized_name is None:
        return None
    normalized_namespace = _normalize_optional_non_empty(namespace) or "default"
    normalized_selector = _normalize_optional_non_empty(selector) or "find"
    token = f"{normalized_namespace}:{normalized_selector}:{normalized_name}"
    suffix = hashlib.sha1(token.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{suffix}"


def _materialize_symbolic_stateless_target(
    *,
    symbolic_ref: dict[str, Any],
    client: Any | None,
    stateless_callable_by_uri: dict[str, Any],
) -> Any:
    op_uri = _normalize_non_empty(symbolic_ref["op_uri"], field_name="op_uri")
    cached = stateless_callable_by_uri.get(op_uri)
    if cached is not None:
        return cached

    declaration = _resolve_stateless_declaration_for_symbol(
        op_uri=op_uri,
        symbolic_ref=symbolic_ref,
        client=client,
    )
    target = getattr(declaration, "target", None)
    if not callable(target):
        raise RuntimeError(
            f"flow_symbolic_stateless_target_not_callable: op_uri={op_uri}",
        )
    _ensure_stateless_registration(
        op_uri=op_uri,
        declaration=declaration,
        client=client,
    )
    stateless_callable_by_uri[op_uri] = target
    return target


def _materialize_symbolic_flow_target(
    *,
    symbolic_ref: dict[str, Any],
    instance: InstanceHandle,
    client: Any | None,
    runtime_host: object,
    topic_api: object,
    flow_program_ref_by_key: dict[str, dict[str, str]],
    materialized_flow_program_keys: set[tuple[str, str]],
) -> dict[str, str]:
    resolved_flow_uri = _normalize_optional_non_empty(symbolic_ref.get("flow_uri"))
    declaration = _resolve_flow_declaration_for_symbol(
        flow_uri=resolved_flow_uri,
        symbolic_ref=symbolic_ref,
        client=client,
    )
    materialization_policy = _resolve_flow_symbol_materialization_policy(
        symbolic_ref=symbolic_ref,
        declaration=declaration,
    )
    cache_key = _build_flow_symbol_cache_key(
        symbolic_ref=symbolic_ref,
        declaration=declaration,
        policy=materialization_policy,
    )
    cached = flow_program_ref_by_key.get(cache_key)
    if cached is not None:
        return dict(cached)

    flow_uri, registration = _resolve_symbolic_flow_uri_and_registration(
        symbolic_ref=symbolic_ref,
        declaration=declaration,
        policy=materialization_policy,
        client=client,
        instance=instance,
    )
    program_rev = _normalize_optional_non_empty(symbolic_ref.get("program_rev"))
    if program_rev is None:
        if registration is not None:
            program_rev = _resolve_flow_program_rev(registration)
        else:
            program_rev = _resolve_program_rev_from_metadata(
                registration_metadata=None,
                declaration=declaration,
            )
    resolved_ref = {
        "program_uri": flow_uri,
        "program_rev": _normalize_non_empty(program_rev, field_name="program_rev"),
    }
    _ensure_runtime_flow_program_registered_for_symbolic_ref(
        flow_uri=resolved_ref["program_uri"],
        program_rev=resolved_ref["program_rev"],
        registration=registration,
        declaration=declaration,
        instance=instance,
        client=client,
        runtime_host=runtime_host,
        topic_api=topic_api,
        materialized_flow_program_keys=materialized_flow_program_keys,
    )
    flow_program_ref_by_key[cache_key] = dict(resolved_ref)
    return resolved_ref


def _ensure_runtime_flow_program_registered_for_symbolic_ref(
    *,
    flow_uri: str,
    program_rev: str,
    registration: RegistrationHandle | None,
    declaration: Any | None,
    instance: InstanceHandle,
    client: Any | None,
    runtime_host: object,
    topic_api: object,
    materialized_flow_program_keys: set[tuple[str, str]],
) -> None:
    register_flow_program = getattr(topic_api, "register_flow_program", None)
    if not callable(register_flow_program):
        return
    key = (flow_uri, program_rev)
    if key in materialized_flow_program_keys:
        return
    source_declaration = (
        getattr(registration, "declaration", None) if registration is not None else None
    )
    if source_declaration is None:
        source_declaration = declaration
    if source_declaration is None:
        return
    resolved_declaration = _resolve_flow_registration_declaration(source_declaration)
    if not _is_flow_program_like(resolved_declaration):
        return

    materialized_flow_program_keys.add(key)
    materialized_program = _materialize_flow_program_symbols(
        flow_program=resolved_declaration,
        instance=instance,
        runtime_host=runtime_host,
        topic_api=topic_api,
        client=client,
        materialized_flow_program_keys=materialized_flow_program_keys,
    )
    register_flow_program(
        flow_program_uri=flow_uri,
        flow_program_rev=program_rev,
        flow_program=materialized_program,
    )


def _resolve_flow_symbol_materialization_policy(
    *,
    symbolic_ref: Mapping[str, Any],
    declaration: Any | None,
) -> dict[str, str]:
    raw_policy = symbolic_ref.get("materialization_policy")
    if raw_policy is None:
        raw_policy = _resolve_flow_symbol_materialization_policy_from_declaration(declaration)
    return _normalize_flow_symbol_materialization_policy(raw_policy)


def _resolve_flow_symbol_materialization_policy_from_declaration(declaration: Any | None) -> Any:
    if not _is_flow_program_like(declaration):
        return None
    policies = getattr(declaration, "policies", None)
    if not isinstance(policies, Mapping):
        return None
    return policies.get("subflow_materialization")


def _normalize_flow_symbol_materialization_policy(raw_policy: Any) -> dict[str, str]:
    if raw_policy is None:
        return {"mode": "caller_owned"}
    if isinstance(raw_policy, str):
        policy = {"mode": raw_policy}
    elif isinstance(raw_policy, Mapping):
        policy = dict(raw_policy)
    else:
        raise TypeError(
            "flow symbol materialization policy must be mapping/string when provided.",
        )

    _raise_on_unknown_fields(
        policy,
        {"mode", "namespace"},
        field_name="flow_symbol_materialization_policy",
    )
    mode = _normalize_optional_non_empty(policy.get("mode")) or "caller_owned"
    if mode not in _FLOW_SYMBOL_MATERIALIZATION_MODES:
        raise ValueError(f"flow symbol materialization policy mode unsupported: {mode}")
    normalized: dict[str, str] = {"mode": mode}
    if mode == "global_unique":
        normalized["namespace"] = _normalize_global_unique_namespace(policy.get("namespace"))
    return normalized


def _build_flow_symbol_cache_key(
    *,
    symbolic_ref: Mapping[str, Any],
    declaration: Any | None,
    policy: Mapping[str, str],
) -> str:
    named_scope = ""
    named_name = _normalize_optional_non_empty(symbolic_ref.get("name"))
    if named_name is not None:
        named_namespace = _normalize_optional_non_empty(symbolic_ref.get("namespace")) or "default"
        named_selector = _normalize_optional_non_empty(symbolic_ref.get("selector")) or "find"
        named_scope = f":{named_namespace}:{named_selector}:{named_name}"
    flow_uri = _normalize_optional_non_empty(symbolic_ref.get("flow_uri"))
    program_rev = _normalize_optional_non_empty(symbolic_ref.get("program_rev")) or ""
    if flow_uri is not None:
        return f"flow-uri:{flow_uri}:{program_rev}{named_scope}"

    declared_flow_uri = _resolve_declared_flow_uri(declaration)
    if declared_flow_uri is not None:
        return f"declared-flow-uri:{declared_flow_uri}:{program_rev}{named_scope}"

    mode = str(policy.get("mode") or "caller_owned")
    if mode == "global_unique" and declaration is not None:
        namespace = str(policy.get("namespace") or "default")
        digest = _compute_flow_program_global_unique_digest(declaration)
        return f"global-unique:{namespace}:{digest}:{program_rev}{named_scope}"
    if declaration is not None:
        return f"{mode}:decl:{id(declaration)}:{program_rev}{named_scope}"
    return f"{mode}:symbol:{id(symbolic_ref)}:{program_rev}{named_scope}"


def _resolve_symbolic_flow_uri_and_registration(
    *,
    symbolic_ref: Mapping[str, Any],
    declaration: Any | None,
    policy: Mapping[str, str],
    client: Any | None,
    instance: InstanceHandle,
) -> tuple[str, RegistrationHandle | None]:
    named_name = _normalize_optional_non_empty(symbolic_ref.get("name"))
    if named_name is not None and client is not None and hasattr(client, "flows"):
        find = getattr(client.flows, "find", None)
        if callable(find):
            named_namespace = _normalize_optional_non_empty(symbolic_ref.get("namespace"))
            named_selector = _normalize_optional_non_empty(symbolic_ref.get("selector"))
            found_instance = find(
                name=named_name,
                namespace=named_namespace,
                selector=named_selector,
            )
            if isinstance(found_instance, InstanceHandle):
                return (
                    _normalize_non_empty(found_instance.uri, field_name="flow_uri"),
                    found_instance.registration,
                )
    flow_uri = _normalize_optional_non_empty(symbolic_ref.get("flow_uri"))
    if flow_uri is None:
        flow_uri = _resolve_declared_flow_uri(declaration)

    if flow_uri is not None:
        return (
            flow_uri,
            _ensure_flow_registration(
                flow_uri=flow_uri,
                declaration=declaration,
                client=client,
            ),
        )

    mode = str(policy.get("mode") or "caller_owned")
    if mode == "caller_owned":
        if declaration is None:
            raise RuntimeError(
                "flow_symbolic_flow_materialization_requires_declaration: mode=caller_owned",
            )
        flows_surface = getattr(client, "flows", None) if client is not None else None
        register = getattr(flows_surface, "register", None)
        if not callable(register):
            raise RuntimeError(
                "flow_symbolic_flow_materialization_requires_flow_client_surface:"
                f" mode=caller_owned instance_id={instance.instance_id}",
            )
        registration = register(declaration)
        return (
            _normalize_non_empty(registration.uri, field_name="flow_uri"),
            registration,
        )

    if mode == "global_unique":
        if declaration is None:
            raise RuntimeError(
                "flow_symbolic_flow_materialization_requires_declaration: mode=global_unique",
            )
        flow_uri = _build_global_unique_flow_uri(
            declaration=declaration,
            namespace=policy.get("namespace"),
        )
        return (
            flow_uri,
            _ensure_flow_registration(
                flow_uri=flow_uri,
                declaration=declaration,
                client=client,
            ),
        )

    raise RuntimeError(
        f"flow_symbolic_flow_materialization_policy_mode_unsupported:{mode}",
    )


def _resolve_declared_flow_uri(declaration: Any | None) -> str | None:
    if declaration is None:
        return None
    return _normalize_optional_non_empty(getattr(declaration, "flow_uri", None))


def _build_global_unique_flow_uri(*, declaration: Any, namespace: Any | None) -> str:
    normalized_namespace = _normalize_global_unique_namespace(namespace)
    digest = _compute_flow_program_global_unique_digest(declaration)
    return f"flow://auto/global-unique/{normalized_namespace}/{digest}"


def _normalize_global_unique_namespace(raw_namespace: Any | None) -> str:
    namespace = _normalize_optional_non_empty(raw_namespace) or "default"
    normalized = "".join(
        char if (char.isalnum() or char in "._-") else "-" for char in namespace
    ).strip("-.")
    return normalized or "default"


def _compute_flow_program_global_unique_digest(flow_program: Any) -> str:
    canonical_payload = _canonicalize_flow_program_for_digest(flow_program)
    encoded = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def _canonicalize_flow_program_for_digest(flow_program: Any) -> dict[str, Any]:
    transformations = _resolve_flow_transformations(flow_program)
    transformation_index: dict[int, int] = {
        id(transformation): index for index, transformation in enumerate(transformations)
    }
    canonical_pipeline = [
        {
            "type": str(getattr(transformation, "type", "")),
            "operator_key": _normalize_optional_non_empty(
                getattr(transformation, "operator_key", None),
            ),
            "target": _canonicalize_flow_value_for_digest(
                getattr(transformation, "target", None),
                transformation_index=transformation_index,
            ),
            "operator_config": _canonicalize_flow_value_for_digest(
                getattr(transformation, "operator_config", None),
                transformation_index=transformation_index,
            ),
            "exception_handler_stack": _canonicalize_flow_value_for_digest(
                getattr(transformation, "exception_handler_stack", None),
                transformation_index=transformation_index,
            ),
            "is_sink": bool(getattr(transformation, "is_sink", False)),
            "is_return": bool(getattr(transformation, "is_return", False)),
            "upstreams": _resolve_transformation_neighbor_indexes(
                getattr(transformation, "upstreams", None),
                transformation_index=transformation_index,
            ),
            "downstreams": _resolve_transformation_neighbor_indexes(
                getattr(transformation, "downstreams", None),
                transformation_index=transformation_index,
            ),
        }
        for transformation in transformations
    ]
    return {
        "flow_uri": _normalize_optional_non_empty(getattr(flow_program, "flow_uri", None)),
        "dsl_name": _normalize_optional_non_empty(getattr(flow_program, "dsl_name", None)),
        "no_return": bool(getattr(flow_program, "no_return", False)),
        "scheduler": _canonicalize_flow_value_for_digest(
            getattr(flow_program, "scheduler", None),
            transformation_index=transformation_index,
        ),
        "resources": _canonicalize_flow_value_for_digest(
            getattr(flow_program, "resources", None),
            transformation_index=transformation_index,
        ),
        "policies": _canonicalize_flow_value_for_digest(
            getattr(flow_program, "policies", None),
            transformation_index=transformation_index,
        ),
        "pipeline": canonical_pipeline,
    }


def _resolve_transformation_neighbor_indexes(
    raw_neighbors: Any,
    *,
    transformation_index: Mapping[int, int],
) -> list[int]:
    if not isinstance(raw_neighbors, list):
        return []
    indexes: list[int] = []
    for raw_neighbor in raw_neighbors:
        index = transformation_index.get(id(raw_neighbor))
        if index is not None:
            indexes.append(index)
    indexes.sort()
    return indexes


def _canonicalize_flow_value_for_digest(
    raw_value: Any,
    *,
    transformation_index: Mapping[int, int],
) -> Any:
    if raw_value is None or isinstance(raw_value, (bool, int, str)):
        return raw_value
    if isinstance(raw_value, float):
        return {"$float": repr(raw_value)}
    if isinstance(raw_value, Mapping):
        normalized: dict[str, Any] = {}
        for raw_key in sorted(raw_value.keys(), key=lambda item: str(item)):
            if raw_key == "declaration":
                continue
            normalized[str(raw_key)] = _canonicalize_flow_value_for_digest(
                raw_value[raw_key],
                transformation_index=transformation_index,
            )
        declaration_hint = _canonicalize_flow_declaration_hint(raw_value.get("declaration"))
        if declaration_hint is not None:
            normalized["$declaration"] = declaration_hint
        return normalized
    if isinstance(raw_value, (list, tuple)):
        return [
            _canonicalize_flow_value_for_digest(
                item,
                transformation_index=transformation_index,
            )
            for item in raw_value
        ]
    if isinstance(raw_value, set):
        normalized_items = [
            _canonicalize_flow_value_for_digest(
                item,
                transformation_index=transformation_index,
            )
            for item in raw_value
        ]
        try:
            return sorted(
                normalized_items,
                key=lambda item: json.dumps(
                    item,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ),
            )
        except Exception:
            return normalized_items
    trans_index = transformation_index.get(id(raw_value))
    if trans_index is not None:
        return {"$transformation_index": trans_index}
    declaration_hint = _canonicalize_flow_declaration_hint(raw_value)
    if declaration_hint is not None:
        return declaration_hint
    callable_hint = _resolve_callable_hint(raw_value)
    if callable_hint is not None:
        return {"$callable": callable_hint}
    return {"$type": type(raw_value).__name__}


def _canonicalize_flow_declaration_hint(raw_declaration: Any) -> dict[str, Any] | None:
    if raw_declaration is None:
        return None
    uri = _normalize_optional_non_empty(getattr(raw_declaration, "uri", None))
    flow_uri = _normalize_optional_non_empty(getattr(raw_declaration, "flow_uri", None))
    dsl_name = _normalize_optional_non_empty(getattr(raw_declaration, "dsl_name", None))
    pipeline = getattr(raw_declaration, "pipeline", None)
    pipeline_len = len(pipeline) if isinstance(pipeline, list) else None
    if uri is None and flow_uri is None and dsl_name is None and pipeline_len is None:
        return None
    hint: dict[str, Any] = {"$declaration_type": type(raw_declaration).__name__}
    if uri is not None:
        hint["uri"] = uri
    if flow_uri is not None:
        hint["flow_uri"] = flow_uri
    if dsl_name is not None:
        hint["dsl_name"] = dsl_name
    if pipeline_len is not None:
        hint["pipeline_len"] = pipeline_len
    return hint


def _resolve_callable_hint(raw_value: Any) -> str | None:
    if not callable(raw_value):
        return None
    module = _normalize_optional_non_empty(getattr(raw_value, "__module__", None))
    qualname = _normalize_optional_non_empty(getattr(raw_value, "__qualname__", None))
    if module is None or qualname is None:
        return None
    return f"{module}:{qualname}"


def _coerce_symbolic_actor_ref(target: Any) -> dict[str, Any] | None:
    try:
        return coerce_actor_symbol_target(target)
    except Exception:
        return None


def _coerce_symbolic_stateless_ref(target: Any) -> dict[str, Any] | None:
    try:
        return coerce_stateless_symbol_target(target)
    except Exception:
        return None


def _coerce_symbolic_flow_ref(target: Any) -> dict[str, Any] | None:
    try:
        return coerce_flow_symbol_target(target)
    except Exception:
        return None


def _resolve_actor_declaration_for_symbol(
    *,
    actor_uri: str,
    symbolic_ref: dict[str, Any],
    client: Any | None,
) -> ActorDeclaration:
    declaration = symbolic_ref.get("declaration")
    if isinstance(declaration, ActorDeclaration):
        return declaration
    if client is not None and hasattr(client, "actors"):
        registration = client.actors.get_discoverable(actor_uri)
        if registration is not None and isinstance(registration.declaration, ActorDeclaration):
            return registration.declaration
    raise RuntimeError(
        f"flow_symbolic_actor_declaration_missing: actor_uri={actor_uri}",
    )


def _resolve_actor_registration_metadata(
    *,
    actor_uri: str,
    declaration: ActorDeclaration,
    client: Any | None,
) -> dict[str, Any]:
    if client is None or not hasattr(client, "actors"):
        return {}
    registration = client.actors.get_discoverable(actor_uri)
    if registration is None:
        registration = client.actors.register(declaration, uri=actor_uri)
    metadata = getattr(registration, "metadata", None)
    if not isinstance(metadata, Mapping):
        return {}
    return dict(metadata)


def _resolve_stateless_declaration_for_symbol(
    *,
    op_uri: str,
    symbolic_ref: dict[str, Any],
    client: Any | None,
) -> StatelessDeclaration:
    declaration = symbolic_ref.get("declaration")
    if isinstance(declaration, StatelessDeclaration):
        return declaration
    if client is not None and hasattr(client, "stateless"):
        registration = client.stateless.get_discoverable(op_uri)
        if registration is not None and isinstance(registration.declaration, StatelessDeclaration):
            return registration.declaration
    raise RuntimeError(
        f"flow_symbolic_stateless_declaration_missing: op_uri={op_uri}",
    )


def _ensure_stateless_registration(
    *,
    op_uri: str,
    declaration: StatelessDeclaration,
    client: Any | None,
) -> None:
    if client is None or not hasattr(client, "stateless"):
        return
    registration = client.stateless.get_discoverable(op_uri)
    if registration is None:
        client.stateless.register(declaration, uri=op_uri)


def _is_flow_program_like(declaration: Any) -> bool:
    if isinstance(declaration, (FlowDeclaration, BoundFlowTemplate, BoundFlowDeclaration)):
        return True
    pipeline = getattr(declaration, "pipeline", None)
    return isinstance(pipeline, list)


def _resolve_flow_declaration_for_symbol(
    *,
    flow_uri: str | None,
    symbolic_ref: dict[str, Any],
    client: Any | None,
) -> Any | None:
    declaration = symbolic_ref.get("declaration")
    if _is_flow_program_like(declaration):
        return declaration
    if flow_uri is not None and client is not None and hasattr(client, "flows"):
        registration = client.flows.get_discoverable(flow_uri)
        if registration is not None and _is_flow_program_like(registration.declaration):
            return registration.declaration
    return None


def _ensure_flow_registration(
    *,
    flow_uri: str,
    declaration: Any | None,
    client: Any | None,
) -> RegistrationHandle | None:
    if client is None or not hasattr(client, "flows"):
        return None
    registration = client.flows.get_discoverable(flow_uri)
    if registration is not None:
        return registration
    if declaration is None:
        return None
    metadata = getattr(declaration, "metadata", None)
    if isinstance(metadata, Mapping):
        return client.flows.register(declaration, uri=flow_uri, metadata=dict(metadata))
    return client.flows.register(declaration, uri=flow_uri)


def _resolve_materialization_policy(
    *,
    declaration: ActorDeclaration,
    registration_metadata: Mapping[str, Any] | None,
    symbolic_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    declaration_policy = _extract_declaration_materialization_policy(declaration)
    override_policy: dict[str, Any] = {}
    if isinstance(registration_metadata, Mapping):
        raw_override = registration_metadata.get("materialization_policy_override")
        if raw_override is not None:
            override_policy = _normalize_mapping(
                raw_override,
                field_name="materialization_policy_override",
            )
    reference_override_policy: dict[str, Any] = {}
    if isinstance(symbolic_ref, Mapping):
        raw_reference_override = symbolic_ref.get("materialization_policy_override")
        if raw_reference_override is not None:
            reference_override_policy = _normalize_mapping(
                raw_reference_override,
                field_name="symbolic_ref.materialization_policy_override",
            )
    merged = _deep_merge_mapping(declaration_policy, override_policy)
    merged = _deep_merge_mapping(merged, reference_override_policy)
    return _normalize_materialization_policy(merged, declaration=declaration)


def _extract_declaration_materialization_policy(declaration: ActorDeclaration) -> dict[str, Any]:
    execution_policy = getattr(declaration, "execution_policy_default", None)
    if not isinstance(execution_policy, Mapping):
        return {}
    raw_materialization = execution_policy.get("materialization")
    if raw_materialization is None:
        return {}
    return _normalize_mapping(
        raw_materialization, field_name="execution_policy_default.materialization"
    )


def _normalize_materialization_policy(
    raw_policy: Mapping[str, Any], *, declaration: ActorDeclaration
) -> dict[str, Any]:
    policy = dict(raw_policy)
    allowed_top_keys = {
        "identity_scope",
        "replica_policy",
        "routing",
        "naming",
        "backend",
    }
    _raise_on_unknown_fields(policy, allowed_top_keys, field_name="materialization_policy")

    identity_scope = str(policy.get("identity_scope") or "flow_instance").strip()
    if identity_scope != "flow_instance":
        raise ValueError(
            f"actor_materialization_policy_unsupported_phase: identity_scope={identity_scope}",
        )

    replica_policy = _normalize_mapping(policy.get("replica_policy"), field_name="replica_policy")
    _raise_on_unknown_fields(
        replica_policy,
        {"mode", "count", "min", "max"},
        field_name="replica_policy",
    )
    replica_mode = str(replica_policy.get("mode") or "fixed").strip()
    if replica_mode != "fixed":
        raise ValueError(
            f"actor_materialization_policy_unsupported_phase: replica_policy.mode={replica_mode}",
        )
    replica_count = int(replica_policy.get("count", 1))
    if replica_count < 1:
        raise ValueError(
            f"actor_materialization_policy_invalid_value: replica_policy.count={replica_count}",
        )

    routing_policy = _normalize_mapping(policy.get("routing"), field_name="routing")
    _raise_on_unknown_fields(
        routing_policy,
        {"mode", "key", "key_source", "stateful_sticky", "rr_resume_on_restart"},
        field_name="routing",
    )
    routing_mode = str(routing_policy.get("mode") or "single").strip()
    if routing_mode != "single":
        raise ValueError(
            f"actor_materialization_policy_unsupported_phase: routing.mode={routing_mode}",
        )
    rr_resume_on_restart = bool(routing_policy.get("rr_resume_on_restart", False))
    if rr_resume_on_restart:
        raise ValueError(
            "actor_materialization_policy_invalid_value: routing.rr_resume_on_restart must be False."
        )

    naming_policy = _normalize_mapping(policy.get("naming"), field_name="naming")
    _raise_on_unknown_fields(
        naming_policy,
        {"prefix", "suffix"},
        field_name="naming",
    )
    default_prefix = getattr(declaration.target, "__name__", "actor")
    naming_prefix = str(naming_policy.get("prefix") or default_prefix).strip()
    if not naming_prefix:
        naming_prefix = default_prefix
    naming_suffix = str(naming_policy.get("suffix") or "short_uuid").strip()
    if naming_suffix != "short_uuid":
        raise ValueError(
            f"actor_materialization_policy_unsupported_phase: naming.suffix={naming_suffix}",
        )

    backend_policy = _normalize_mapping(policy.get("backend"), field_name="backend")
    _raise_on_unknown_fields(
        backend_policy,
        {"required_tags", "preferred_backend_id", "request_epoch_field"},
        field_name="backend",
    )
    backend_required_tags = _normalize_string_mapping(
        backend_policy.get("required_tags"),
        field_name="backend.required_tags",
    )
    backend_preferred_backend_id = _normalize_optional_non_empty(
        backend_policy.get("preferred_backend_id")
    )
    backend_request_epoch_field = (
        _normalize_optional_non_empty(backend_policy.get("request_epoch_field")) or "request_epoch"
    )

    return {
        "identity_scope": identity_scope,
        "replica_policy": {
            "mode": replica_mode,
            "count": replica_count,
        },
        "routing": {
            "mode": routing_mode,
            "stateful_sticky": bool(routing_policy.get("stateful_sticky", True)),
            "rr_resume_on_restart": False,
        },
        "naming": {
            "prefix": naming_prefix,
            "suffix": naming_suffix,
        },
        "backend": {
            "required_tags": backend_required_tags,
            "preferred_backend_id": backend_preferred_backend_id,
            "request_epoch_field": backend_request_epoch_field,
        },
    }


def _register_materialized_local_actor(
    *,
    actor_api: Any,
    declaration: ActorDeclaration,
    policy: Mapping[str, Any],
    instance_id: str,
    actor_uri: str,
    bind_args: tuple[Any, ...] = (),
    bind_kwargs: Mapping[str, Any] | None = None,
    name: str | None = None,
    namespace: str | None = None,
    selector: str | None = None,
    replica_index: int | None = None,
    replica_count: int = 1,
) -> str:
    actor_cls = declaration.target
    if not isinstance(actor_cls, type):
        raise TypeError("actor_materialization_target_must_be_class")
    naming_policy = policy.get("naming") if isinstance(policy, Mapping) else None
    prefix = ""
    if isinstance(naming_policy, Mapping):
        prefix = str(naming_policy.get("prefix") or "").strip()
    if not prefix:
        prefix = getattr(actor_cls, "__name__", "actor")

    bind_kwargs_dict = dict(bind_kwargs or {})
    named_actor_id = _build_named_actor_id(
        prefix=prefix,
        name=name,
        namespace=namespace,
        selector=selector,
    )
    if named_actor_id is not None and replica_count > 1 and replica_index is not None:
        named_actor_id = f"{named_actor_id}_r{int(replica_index)}"
    for _ in range(16):
        actor_id = named_actor_id or f"{prefix}_{uuid.uuid4().hex[:8]}"
        actor_object = actor_cls(*tuple(bind_args), **bind_kwargs_dict)
        backend_requirements: dict[str, Any] | None = None
        backend_policy = policy.get("backend") if isinstance(policy, Mapping) else None
        if isinstance(backend_policy, Mapping):
            normalized_required_tags = _normalize_string_mapping(
                backend_policy.get("required_tags"),
                field_name="materialization_policy.backend.required_tags",
            )
            normalized_preferred_backend_id = _normalize_optional_non_empty(
                backend_policy.get("preferred_backend_id")
            )
            normalized_request_epoch_field = (
                _normalize_optional_non_empty(backend_policy.get("request_epoch_field"))
                or "request_epoch"
            )
            if (
                normalized_required_tags
                or normalized_preferred_backend_id is not None
                or normalized_request_epoch_field != "request_epoch"
            ):
                backend_requirements = {
                    "required_tags": normalized_required_tags,
                    "preferred_backend_id": normalized_preferred_backend_id,
                    "request_epoch_field": normalized_request_epoch_field,
                }
        actor_config: dict[str, Any] = {
            "task_policy": {
                "max_pending": 256,
            },
            "materialized_from": {
                "instance_id": instance_id,
                "actor_uri": actor_uri,
                "name": name,
                "namespace": namespace,
                "selector": selector,
                "bind_hash": _compute_symbolic_bind_hash(bind_args, bind_kwargs_dict),
            },
        }
        if backend_requirements is not None:
            actor_config["backend_requirements"] = dict(backend_requirements)
            actor_config["materialized_from"]["backend_requirements"] = dict(backend_requirements)
        try:
            actor_api.register_local_actor(
                actor_object,
                actor_id=actor_id,
                config=actor_config,
            )
            return actor_id
        except ValueError as exc:
            if not str(exc).startswith("actor_already_exists:"):
                raise
            if named_actor_id is not None:
                return actor_id
            continue
    raise RuntimeError(f"actor_materialization_id_collision_exhausted:actor_uri={actor_uri}")


def _register_materialized_local_actor_replicas(
    *,
    actor_api: Any,
    declaration: ActorDeclaration,
    policy: Mapping[str, Any],
    instance_id: str,
    actor_uri: str,
    bind_args: tuple[Any, ...] = (),
    bind_kwargs: Mapping[str, Any] | None = None,
    name: str | None = None,
    namespace: str | None = None,
    selector: str | None = None,
) -> tuple[str, ...]:
    replica_policy = policy.get("replica_policy") if isinstance(policy, Mapping) else None
    replica_count = 1
    if isinstance(replica_policy, Mapping):
        replica_count = int(replica_policy.get("count", 1))
    replica_count = max(1, replica_count)

    actor_ids: list[str] = []
    for replica_index in range(replica_count):
        actor_ids.append(
            _register_materialized_local_actor(
                actor_api=actor_api,
                declaration=declaration,
                policy=policy,
                instance_id=instance_id,
                actor_uri=actor_uri,
                bind_args=bind_args,
                bind_kwargs=bind_kwargs,
                name=name,
                namespace=namespace,
                selector=selector,
                replica_index=replica_index,
                replica_count=replica_count,
            )
        )
    return tuple(actor_ids)


def _resolve_flow_transformations(flow_program: Any) -> list[Any]:
    pipeline = getattr(flow_program, "pipeline", None)
    if isinstance(pipeline, list):
        return list(pipeline)
    return []


def _deep_merge_mapping(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, override_value in override.items():
        if isinstance(override_value, Mapping):
            base_value = merged.get(key)
            if isinstance(base_value, Mapping):
                merged[key] = _deep_merge_mapping(dict(base_value), override_value)
            else:
                merged[key] = dict(override_value)
            continue
        merged[key] = override_value
    return merged


def _raise_on_unknown_fields(
    mapping: Mapping[str, Any], allowed: set[str], *, field_name: str
) -> None:
    for key in mapping:
        if str(key) not in allowed:
            raise ValueError(
                f"actor_materialization_policy_unknown_field: {field_name}.{key}",
            )


def build_runtime_client(
    *,
    owner: str = "local-owner",
    runtime_host: object | None = None,
    io_contract_mode: str = "compat",
) -> V1RuntimeClient:
    return V1RuntimeClient(
        owner=owner,
        runtime_host=runtime_host,
        io_contract_mode=io_contract_mode,
    )


@contextmanager
def client_scope(client: V1RuntimeClient):
    if not isinstance(client, V1RuntimeClient):
        raise TypeError("client_scope expects V1RuntimeClient.")
    token: Token[V1RuntimeClient | None] = _SCOPED_RUNTIME_CLIENT.set(client)
    try:
        yield client
    finally:
        _SCOPED_RUNTIME_CLIENT.reset(token)


def get_scoped_runtime_client() -> V1RuntimeClient | None:
    return _SCOPED_RUNTIME_CLIENT.get()


def _resolve_lifecycle_state_store(
    *,
    runtime_host: object | None,
    kind: ResourceKind,
) -> _LifecycleStateStore:
    enforce_unique_uri = kind != "flow"
    if runtime_host is None:
        return _LifecycleStateStore(kind=kind, enforce_unique_uri=enforce_unique_uri)

    with _HOST_LIFECYCLE_STATE_STORES_LOCK:
        try:
            stores_by_kind = _HOST_LIFECYCLE_STATE_STORES.get(runtime_host)
        except TypeError as exc:
            raise TypeError("runtime_host must support weak references.") from exc

        if stores_by_kind is None:
            stores_by_kind = {}
            _HOST_LIFECYCLE_STATE_STORES[runtime_host] = stores_by_kind

        state_store = stores_by_kind.get(kind)
        if state_store is None:
            state_store = _LifecycleStateStore(
                kind=kind,
                enforce_unique_uri=enforce_unique_uri,
            )
            stores_by_kind[kind] = state_store
        return state_store


def _normalize_non_empty(raw_value: Any, *, field_name: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _normalize_optional_non_empty(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    return normalized


def _status_has_error_outcome(status: Mapping[str, Any]) -> bool:
    raw = _normalize_optional_non_empty(status.get("outcome_status"))
    if raw is None:
        return False
    return raw.lower() in {"failed", "aborted", "dropped"}


def _resolve_scoped_instance_name(bindings: Mapping[str, Any] | None) -> tuple[str, str] | None:
    if not isinstance(bindings, Mapping):
        return None
    name = _normalize_optional_non_empty(bindings.get("name"))
    if name is None:
        return None
    namespace = _resolve_instance_namespace(bindings)
    return namespace, name


def _resolve_instance_namespace(bindings: Mapping[str, Any] | None) -> str:
    if not isinstance(bindings, Mapping):
        return "default"
    return _normalize_optional_non_empty(bindings.get("namespace")) or "default"


def _instance_matches_locate_tag(instance: InstanceHandle, normalized_tag: str) -> bool:
    scoped_name = _resolve_scoped_instance_name(instance.bindings)
    if scoped_name is not None and scoped_name[1] == normalized_tag:
        return True

    tags = _coerce_instance_tag_values(instance.bindings.get("tag"))
    return normalized_tag in tags


def _coerce_instance_tag_values(raw_value: Any) -> set[str]:
    if raw_value is None:
        return set()
    if isinstance(raw_value, str):
        normalized = _normalize_optional_non_empty(raw_value)
        return {normalized} if normalized is not None else set()
    if isinstance(raw_value, Mapping):
        values: set[str] = set()
        for key in ("tag", "name", "value"):
            normalized = _normalize_optional_non_empty(raw_value.get(key))
            if normalized is not None:
                values.add(normalized)
        return values
    if isinstance(raw_value, (list, tuple, set, frozenset)):
        values: set[str] = set()
        for item in raw_value:
            normalized = _normalize_optional_non_empty(item)
            if normalized is not None:
                values.add(normalized)
        return values
    normalized = _normalize_optional_non_empty(raw_value)
    return {normalized} if normalized is not None else set()


def _normalize_instance_id(instance_or_id: InstanceHandle | str) -> str:
    if isinstance(instance_or_id, InstanceHandle):
        return instance_or_id.instance_id
    return _normalize_non_empty(instance_or_id, field_name="instance_id")


def _now_epoch_ms() -> int:
    return int(time.time() * 1000)


def _lifecycle_snapshot(record: _LifecycleRecord) -> dict[str, Any]:
    instance = record.instance
    registration = instance.registration
    return {
        "kind": instance.kind,
        "instance_id": instance.instance_id,
        "registration_id": registration.registration_id,
        "uri": registration.uri,
        "owner": registration.owner,
        "status": record.status,
        "implicit_registration": instance.implicit_registration,
        "started_at_epoch_ms": record.started_at_epoch_ms,
        "stopped_at_epoch_ms": record.stopped_at_epoch_ms,
        "config": dict(instance.config),
        "policies": dict(instance.policies),
        "bindings": dict(instance.bindings),
        "options": dict(instance.options),
        "registration_metadata": dict(registration.metadata),
    }


__all__ = [
    "FlowEndpoint",
    "FlowRequestRef",
    "FlowRequestOutcomeError",
    "V1RuntimeClient",
    "build_runtime_client",
    "client_scope",
    "get_scoped_runtime_client",
]
