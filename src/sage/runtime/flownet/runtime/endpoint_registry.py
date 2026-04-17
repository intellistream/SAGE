from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from threading import RLock
from typing import Any

from sage.runtime.flownet.client.handles import InstanceHandle
from sage.runtime.flownet.contracts.endpoint_plane_contract import (
    FLOW_ENDPOINT_PUBLISHED,
    FLOW_ENDPOINT_RELEASED,
    FlowEndpointDescriptor,
)


@dataclass(frozen=True)
class PublishedFlowEndpointRecord:
    descriptor: FlowEndpointDescriptor
    flow_instance: InstanceHandle

    def snapshot(self) -> dict[str, Any]:
        return self.descriptor.to_dict()


class FlowEndpointRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._records_by_id: dict[str, PublishedFlowEndpointRecord] = {}
        self._active_endpoint_by_name: dict[tuple[str, str], str] = {}

    def publish(
        self,
        *,
        descriptor: FlowEndpointDescriptor,
        flow_instance: InstanceHandle,
        reuse_existing: bool,
    ) -> PublishedFlowEndpointRecord:
        if not isinstance(reuse_existing, bool):
            raise TypeError("reuse_existing must be bool.")
        if flow_instance.kind != "flow":
            raise TypeError("published endpoint requires a flow instance.")
        scoped_name = (descriptor.namespace, descriptor.name)
        with self._lock:
            existing_record = self._resolve_active_record_locked(scoped_name)
            if existing_record is not None:
                if self._same_publication(existing_record, descriptor):
                    if reuse_existing:
                        return existing_record
                    raise ValueError(
                        "flow_endpoint_name_already_published:"
                        f"namespace={descriptor.namespace} name={descriptor.name}"
                    )
                raise ValueError(
                    "flow_endpoint_publish_conflict:"
                    f"namespace={descriptor.namespace} name={descriptor.name}"
                )
            record = PublishedFlowEndpointRecord(
                descriptor=descriptor,
                flow_instance=flow_instance,
            )
            self._records_by_id[descriptor.endpoint_id] = record
            self._active_endpoint_by_name[scoped_name] = descriptor.endpoint_id
            return record

    def find_active(
        self,
        *,
        name: str,
        namespace: str,
        flow_uri: str | None = None,
    ) -> PublishedFlowEndpointRecord | None:
        scoped_name = (_normalize_non_empty(namespace, field_name="namespace"), _normalize_non_empty(name, field_name="name"))
        with self._lock:
            record = self._resolve_active_record_locked(scoped_name)
            if record is None:
                return None
            if flow_uri is not None and record.descriptor.flow_uri != _normalize_non_empty(flow_uri, field_name="flow_uri"):
                return None
            return record

    def inspect(
        self,
        *,
        endpoint_id: str | None = None,
        name: str | None = None,
        namespace: str | None = None,
        flow_uri: str | None = None,
    ) -> dict[str, Any] | None:
        record = self.resolve(
            endpoint_id=endpoint_id,
            name=name,
            namespace=namespace,
            flow_uri=flow_uri,
        )
        if record is None:
            return None
        return record.snapshot()

    def resolve(
        self,
        *,
        endpoint_id: str | None = None,
        name: str | None = None,
        namespace: str | None = None,
        flow_uri: str | None = None,
    ) -> PublishedFlowEndpointRecord | None:
        normalized_flow_uri = _normalize_optional_non_empty(flow_uri)
        with self._lock:
            if endpoint_id is not None:
                record = self._records_by_id.get(_normalize_non_empty(endpoint_id, field_name="endpoint_id"))
                if record is None:
                    return None
                if normalized_flow_uri is not None and record.descriptor.flow_uri != normalized_flow_uri:
                    return None
                return record
            if name is None or namespace is None:
                raise ValueError("endpoint resolve requires endpoint_id or name+namespace.")
            scoped_name = (_normalize_non_empty(namespace, field_name="namespace"), _normalize_non_empty(name, field_name="name"))
            record = self._resolve_active_record_locked(scoped_name)
            if record is None:
                return None
            if normalized_flow_uri is not None and record.descriptor.flow_uri != normalized_flow_uri:
                return None
            return record

    def list_endpoints(
        self,
        *,
        namespace: str | None = None,
        flow_uri: str | None = None,
        include_released: bool = True,
    ) -> list[dict[str, Any]]:
        normalized_namespace = _normalize_optional_non_empty(namespace)
        normalized_flow_uri = _normalize_optional_non_empty(flow_uri)
        with self._lock:
            records = list(self._records_by_id.values())
        rows: list[dict[str, Any]] = []
        for record in records:
            descriptor = record.descriptor
            if not include_released and descriptor.status != FLOW_ENDPOINT_PUBLISHED:
                continue
            if normalized_namespace is not None and descriptor.namespace != normalized_namespace:
                continue
            if normalized_flow_uri is not None and descriptor.flow_uri != normalized_flow_uri:
                continue
            rows.append(record.snapshot())
        rows.sort(
            key=lambda item: (
                str(item.get("namespace") or ""),
                str(item.get("name") or ""),
                str(item.get("version") or ""),
            )
        )
        return rows

    def release_flow_instance_endpoints(self, flow_instance_id: str) -> int:
        normalized_flow_instance_id = _normalize_non_empty(
            flow_instance_id,
            field_name="flow_instance_id",
        )
        released = 0
        with self._lock:
            for endpoint_id, record in list(self._records_by_id.items()):
                descriptor = record.descriptor
                if descriptor.flow_instance_id != normalized_flow_instance_id:
                    continue
                if descriptor.status == FLOW_ENDPOINT_RELEASED:
                    continue
                updated_descriptor = replace(descriptor, status=FLOW_ENDPOINT_RELEASED)
                self._records_by_id[endpoint_id] = PublishedFlowEndpointRecord(
                    descriptor=updated_descriptor,
                    flow_instance=record.flow_instance,
                )
                scoped_name = (descriptor.namespace, descriptor.name)
                if self._active_endpoint_by_name.get(scoped_name) == endpoint_id:
                    self._active_endpoint_by_name.pop(scoped_name, None)
                released += 1
        return released

    def observability_snapshot(
        self,
        *,
        namespace: str | None = None,
        flow_uri: str | None = None,
        include_released: bool = True,
    ) -> list[dict[str, Any]]:
        return self.list_endpoints(
            namespace=namespace,
            flow_uri=flow_uri,
            include_released=include_released,
        )

    def _resolve_active_record_locked(
        self,
        scoped_name: tuple[str, str],
    ) -> PublishedFlowEndpointRecord | None:
        endpoint_id = self._active_endpoint_by_name.get(scoped_name)
        if endpoint_id is None:
            return None
        record = self._records_by_id.get(endpoint_id)
        if record is None:
            self._active_endpoint_by_name.pop(scoped_name, None)
            return None
        if record.descriptor.status != FLOW_ENDPOINT_PUBLISHED:
            self._active_endpoint_by_name.pop(scoped_name, None)
            return None
        return record

    def _same_publication(
        self,
        existing_record: PublishedFlowEndpointRecord,
        candidate_descriptor: FlowEndpointDescriptor,
    ) -> bool:
        existing = existing_record.descriptor
        if existing.status != FLOW_ENDPOINT_PUBLISHED:
            return False
        return (
            existing.namespace == candidate_descriptor.namespace
            and existing.name == candidate_descriptor.name
            and existing.flow_uri == candidate_descriptor.flow_uri
            and existing.in_topic == candidate_descriptor.in_topic
            and existing.out_topic == candidate_descriptor.out_topic
            and existing.version == candidate_descriptor.version
            and existing.owner == candidate_descriptor.owner
            and existing.bind_hash == candidate_descriptor.bind_hash
            and _shared_state_contract_ids(existing.shared_state_bindings)
            == _shared_state_contract_ids(candidate_descriptor.shared_state_bindings)
        )


def _shared_state_contract_ids(bindings: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    contract_ids: list[str] = []
    for binding in bindings:
        if not isinstance(binding, Mapping):
            continue
        contract_id = _normalize_optional_non_empty(binding.get("contract_id"))
        if contract_id is None:
            continue
        contract_ids.append(contract_id)
    return tuple(sorted(contract_ids))


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


__all__ = [
    "FlowEndpointRegistry",
    "PublishedFlowEndpointRecord",
]