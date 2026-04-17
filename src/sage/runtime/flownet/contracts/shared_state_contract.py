from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from sage.runtime.flownet.contracts.recovery_contract import (
    RecoveryPolicy,
    normalize_recovery_policy,
)

SharedStateVisibility = Literal["private", "namespace", "public"]
SharedStateReusePolicy = Literal["flow", "cross_flow"]
SharedStateRecoveryPolicy = RecoveryPolicy

SHARED_STATE_BINDINGS_METADATA_KEY = "shared_state_bindings"

_VISIBILITIES = frozenset({"private", "namespace", "public"})
_REUSE_POLICIES = frozenset({"flow", "cross_flow"})


@dataclass(frozen=True)
class SharedStateServiceDescriptor:
    service_name: str
    namespace: str
    owner: str
    visibility: SharedStateVisibility = "private"
    reuse_policy: SharedStateReusePolicy = "flow"
    recovery_policy: SharedStateRecoveryPolicy = "best_effort"
    admission_policy: dict[str, Any] = field(default_factory=dict)
    binding_metadata: dict[str, Any] = field(default_factory=dict)
    contract_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "service_name", _normalize_non_empty(self.service_name, field_name="service_name"))
        object.__setattr__(self, "namespace", _normalize_non_empty(self.namespace, field_name="namespace"))
        object.__setattr__(self, "owner", _normalize_non_empty(self.owner, field_name="owner"))
        object.__setattr__(self, "visibility", _normalize_choice(self.visibility, field_name="visibility", allowed=_VISIBILITIES))
        object.__setattr__(self, "reuse_policy", _normalize_choice(self.reuse_policy, field_name="reuse_policy", allowed=_REUSE_POLICIES))
        object.__setattr__(self, "recovery_policy", normalize_recovery_policy(self.recovery_policy))
        object.__setattr__(self, "admission_policy", _normalize_mapping(self.admission_policy, field_name="admission_policy"))
        object.__setattr__(self, "binding_metadata", _normalize_mapping(self.binding_metadata, field_name="binding_metadata"))
        contract_id = _normalize_optional_non_empty(self.contract_id)
        if contract_id is None:
            contract_id = _build_contract_id(self)
        object.__setattr__(self, "contract_id", contract_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_name": self.service_name,
            "namespace": self.namespace,
            "owner": self.owner,
            "visibility": self.visibility,
            "reuse_policy": self.reuse_policy,
            "recovery_policy": self.recovery_policy,
            "admission_policy": dict(self.admission_policy),
            "binding_metadata": dict(self.binding_metadata),
            "contract_id": self.contract_id,
        }


@dataclass(frozen=True)
class SharedStateBindingSpec:
    alias: str
    descriptor: SharedStateServiceDescriptor
    required: bool = True
    binding_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "alias", _normalize_non_empty(self.alias, field_name="alias"))
        object.__setattr__(self, "descriptor", normalize_shared_state_service_descriptor(self.descriptor))
        object.__setattr__(self, "required", bool(self.required))
        object.__setattr__(self, "binding_metadata", _normalize_mapping(self.binding_metadata, field_name="binding_metadata"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "descriptor": self.descriptor.to_dict(),
            "required": self.required,
            "binding_metadata": dict(self.binding_metadata),
        }


def normalize_shared_state_service_descriptor(
    raw_value: SharedStateServiceDescriptor | Mapping[str, Any],
) -> SharedStateServiceDescriptor:
    if isinstance(raw_value, SharedStateServiceDescriptor):
        return raw_value
    if not isinstance(raw_value, Mapping):
        raise TypeError("shared state descriptor must be a SharedStateServiceDescriptor or mapping.")
    return SharedStateServiceDescriptor(
        service_name=raw_value.get("service_name"),
        namespace=raw_value.get("namespace"),
        owner=raw_value.get("owner"),
        visibility=raw_value.get("visibility", "private"),
        reuse_policy=raw_value.get("reuse_policy", "flow"),
        recovery_policy=raw_value.get("recovery_policy", "best_effort"),
        admission_policy=_normalize_mapping(raw_value.get("admission_policy"), field_name="admission_policy"),
        binding_metadata=_normalize_mapping(raw_value.get("binding_metadata"), field_name="binding_metadata"),
        contract_id=_normalize_optional_non_empty(raw_value.get("contract_id")) or "",
    )


def normalize_shared_state_binding_spec(
    raw_value: SharedStateBindingSpec | Mapping[str, Any],
) -> SharedStateBindingSpec:
    if isinstance(raw_value, SharedStateBindingSpec):
        return raw_value
    if not isinstance(raw_value, Mapping):
        raise TypeError("shared state binding must be a SharedStateBindingSpec or mapping.")
    return SharedStateBindingSpec(
        alias=raw_value.get("alias"),
        descriptor=normalize_shared_state_service_descriptor(raw_value.get("descriptor") or {}),
        required=bool(raw_value.get("required", True)),
        binding_metadata=_normalize_mapping(raw_value.get("binding_metadata"), field_name="binding_metadata"),
    )


def normalize_shared_state_binding_specs(raw_value: Any) -> tuple[SharedStateBindingSpec, ...]:
    payload = raw_value
    if isinstance(raw_value, Mapping):
        payload = raw_value.get(SHARED_STATE_BINDINGS_METADATA_KEY)
    if payload is None:
        return ()
    if isinstance(payload, SharedStateBindingSpec):
        return (payload,)
    if isinstance(payload, Mapping):
        return (normalize_shared_state_binding_spec(payload),)
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes, bytearray)):
        raise TypeError("shared state bindings payload must be a binding spec or sequence of binding specs.")

    normalized: list[SharedStateBindingSpec] = []
    aliases: dict[str, str] = {}
    for item in payload:
        binding = normalize_shared_state_binding_spec(item)
        existing_contract_id = aliases.get(binding.alias)
        if existing_contract_id is not None and existing_contract_id != binding.descriptor.contract_id:
            raise ValueError(
                "shared_state_binding_alias_conflict:"
                f" alias={binding.alias} existing_contract_id={existing_contract_id}"
                f" incoming_contract_id={binding.descriptor.contract_id}"
            )
        aliases[binding.alias] = binding.descriptor.contract_id
        if any(
            existing.alias == binding.alias and existing.descriptor.contract_id == binding.descriptor.contract_id
            for existing in normalized
        ):
            continue
        normalized.append(binding)
    return tuple(normalized)


def serialize_shared_state_binding_specs(
    bindings: Sequence[SharedStateBindingSpec | Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [normalize_shared_state_binding_spec(binding).to_dict() for binding in bindings]


def with_shared_state_binding_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    alias: str,
    descriptor: SharedStateServiceDescriptor | Mapping[str, Any],
    required: bool = True,
    binding_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_metadata = dict(metadata or {})
    bindings = list(normalize_shared_state_binding_specs(resolved_metadata))
    new_binding = SharedStateBindingSpec(
        alias=alias,
        descriptor=normalize_shared_state_service_descriptor(descriptor),
        required=required,
        binding_metadata=_normalize_mapping(binding_metadata, field_name="binding_metadata"),
    )
    replaced = False
    for index, existing in enumerate(bindings):
        if existing.alias != new_binding.alias:
            continue
        if existing.descriptor.contract_id != new_binding.descriptor.contract_id:
            raise ValueError(
                "shared_state_binding_alias_conflict:"
                f" alias={new_binding.alias} existing_contract_id={existing.descriptor.contract_id}"
                f" incoming_contract_id={new_binding.descriptor.contract_id}"
            )
        bindings[index] = new_binding
        replaced = True
        break
    if not replaced:
        bindings.append(new_binding)
    resolved_metadata[SHARED_STATE_BINDINGS_METADATA_KEY] = serialize_shared_state_binding_specs(bindings)
    return resolved_metadata


def _build_contract_id(descriptor: SharedStateServiceDescriptor) -> str:
    payload = {
        "service_name": descriptor.service_name,
        "namespace": descriptor.namespace,
        "owner": descriptor.owner,
        "visibility": descriptor.visibility,
        "reuse_policy": descriptor.reuse_policy,
        "recovery_policy": descriptor.recovery_policy,
        "admission_policy": _canonicalize_value(descriptor.admission_policy),
        "binding_metadata": _canonicalize_value(descriptor.binding_metadata),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def _canonicalize_value(raw_value: Any) -> Any:
    if raw_value is None or isinstance(raw_value, (bool, int, float, str)):
        return raw_value
    if isinstance(raw_value, Mapping):
        return {
            str(key): _canonicalize_value(raw_value[key])
            for key in sorted(raw_value.keys(), key=lambda item: str(item))
        }
    if isinstance(raw_value, (list, tuple)):
        return [_canonicalize_value(item) for item in raw_value]
    if isinstance(raw_value, set):
        return sorted(_canonicalize_value(item) for item in raw_value)
    return str(raw_value)


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


def _normalize_choice(raw_value: Any, *, field_name: str, allowed: set[str] | frozenset[str]) -> str:
    normalized = _normalize_non_empty(raw_value, field_name=field_name).lower()
    if normalized not in allowed:
        raise ValueError(
            f"{field_name} must be one of: {', '.join(sorted(allowed))}."
        )
    return normalized


def _normalize_mapping(raw_value: Any, *, field_name: str) -> dict[str, Any]:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, Mapping):
        raise TypeError(f"{field_name} must be a mapping when provided.")
    return dict(raw_value)


__all__ = [
    "SHARED_STATE_BINDINGS_METADATA_KEY",
    "SharedStateBindingSpec",
    "SharedStateRecoveryPolicy",
    "SharedStateReusePolicy",
    "SharedStateServiceDescriptor",
    "SharedStateVisibility",
    "normalize_shared_state_binding_spec",
    "normalize_shared_state_binding_specs",
    "normalize_shared_state_service_descriptor",
    "serialize_shared_state_binding_specs",
    "with_shared_state_binding_metadata",
]