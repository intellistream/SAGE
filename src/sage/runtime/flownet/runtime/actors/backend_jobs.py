from __future__ import annotations

import hashlib
from collections.abc import Mapping
from concurrent.futures import Future
from typing import Any

from sage.runtime.flownet.runtime.actors.execution_context import (
    require_actor_execution_context,
    require_actor_runtime_host,
)


def submit_backend_job(
    *,
    request: Mapping[str, Any],
    backend_id: str | None = None,
    required_tags: Mapping[str, str] | None = None,
    required_capabilities: Mapping[str, Any] | None = None,
    preferred_backend_id: str | None = None,
    request_epoch: int | None = None,
    timeout_seconds: float | None = None,
    poll_interval_seconds: float = 0.01,
    auto_ack: bool = True,
) -> Future:
    actor_context = require_actor_execution_context()
    runtime_host = require_actor_runtime_host()
    submit = getattr(runtime_host, "submit_backend_job", None)
    if not callable(submit):
        raise RuntimeError("actor_runtime_host_missing_submit_backend_job")

    requirements = resolve_actor_backend_requirements(actor_context.actor_config)
    merged_required_tags = dict(requirements.get("required_tags") or {})
    merged_required_capabilities = dict(requirements.get("required_capabilities") or {})
    if isinstance(required_tags, Mapping):
        for raw_key, raw_value in required_tags.items():
            key = _normalize_optional_non_empty(raw_key)
            value = _normalize_optional_non_empty(raw_value)
            if key is None or value is None:
                continue
            merged_required_tags[key] = value
    if isinstance(required_capabilities, Mapping):
        for raw_key, raw_value in required_capabilities.items():
            key = _normalize_optional_non_empty(raw_key)
            if key is None:
                continue
            merged_required_capabilities[key] = _normalize_capability_value(raw_value)

    _merge_serving_context_backend_requirements(
        request=request,
        required_tags=merged_required_tags,
        required_capabilities=merged_required_capabilities,
    )

    resolved_preferred_backend_id = _normalize_optional_non_empty(
        preferred_backend_id
    ) or _normalize_optional_non_empty(requirements.get("preferred_backend_id"))
    if resolved_preferred_backend_id is None:
        resolved_preferred_backend_id = _resolve_prefix_cache_key_backend_affinity(
            request=request,
            runtime_host=runtime_host,
            required_tags=merged_required_tags or None,
            required_capabilities=merged_required_capabilities or None,
        )
    resolved_request_epoch = (
        request_epoch
        if request_epoch is not None
        else _resolve_actor_request_epoch(
            request=request,
            requirements=requirements,
        )
    )
    return submit(
        request=dict(request),
        backend_id=backend_id,
        required_tags=merged_required_tags or None,
        required_capabilities=merged_required_capabilities or None,
        preferred_backend_id=resolved_preferred_backend_id,
        request_epoch=resolved_request_epoch,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        auto_ack=auto_ack,
    )


def resolve_actor_backend_requirements(actor_config: Any | None) -> dict[str, Any]:
    if not isinstance(actor_config, Mapping):
        return {}
    backend_requirements = actor_config.get("backend_requirements")
    if not isinstance(backend_requirements, Mapping):
        return {}
    required_tags = _normalize_tags(backend_requirements.get("required_tags"))
    required_capabilities = _normalize_capability_mapping(
        backend_requirements.get("required_capabilities")
    )
    preferred_backend_id = _normalize_optional_non_empty(
        backend_requirements.get("preferred_backend_id")
    )
    request_epoch_field = (
        _normalize_optional_non_empty(backend_requirements.get("request_epoch_field"))
        or "request_epoch"
    )
    return {
        "required_tags": required_tags,
        "required_capabilities": required_capabilities,
        "preferred_backend_id": preferred_backend_id,
        "request_epoch_field": request_epoch_field,
    }


def _resolve_actor_request_epoch(
    *,
    request: Mapping[str, Any],
    requirements: Mapping[str, Any],
) -> int | None:
    request_epoch_field = _normalize_optional_non_empty(requirements.get("request_epoch_field"))
    if request_epoch_field is None:
        return None
    candidates = (
        request.get(request_epoch_field),
        request.get("request_epoch"),
        request.get("epoch"),
    )
    for candidate in candidates:
        normalized = _normalize_optional_epoch(candidate)
        if normalized is not None:
            return normalized

    metadata = request.get("metadata")
    if isinstance(metadata, Mapping):
        metadata_candidates = (
            metadata.get(request_epoch_field),
            metadata.get("request_epoch"),
            metadata.get("epoch"),
        )
        for candidate in metadata_candidates:
            normalized = _normalize_optional_epoch(candidate)
            if normalized is not None:
                return normalized
    return None


def _merge_serving_context_backend_requirements(
    *,
    request: Mapping[str, Any],
    required_tags: dict[str, str],
    required_capabilities: dict[str, Any],
) -> None:
    serving_context = _resolve_request_serving_context(request)
    if serving_context is None:
        return

    if "accelerator" not in required_tags:
        accelerator_affinity = _normalize_optional_non_empty(
            serving_context.get("accelerator_affinity")
        )
        if accelerator_affinity is not None:
            required_tags["accelerator"] = accelerator_affinity

    if "models" not in required_capabilities:
        model_id = _normalize_optional_non_empty(serving_context.get("model_id"))
        if model_id is not None:
            required_capabilities["models"] = model_id


def _resolve_prefix_cache_key_backend_affinity(
    *,
    request: Mapping[str, Any],
    runtime_host: Any,
    required_tags: Mapping[str, str] | None,
    required_capabilities: Mapping[str, Any] | None,
) -> str | None:
    serving_context = _resolve_request_serving_context(request)
    if serving_context is None:
        return None

    prefix_cache_key = _normalize_optional_non_empty(serving_context.get("prefix_cache_key"))
    if prefix_cache_key is None:
        return None

    find_backend_containers = getattr(runtime_host, "find_backend_containers", None)
    if not callable(find_backend_containers):
        return None

    candidate_records = find_backend_containers(
        required_tags=required_tags,
        required_capabilities=required_capabilities,
        include_metrics=True,
    )
    candidate_backend_ids = sorted(
        backend_id
        for backend_id in (
            _eligible_backend_id_from_record(record) for record in candidate_records
        )
        if backend_id is not None
    )
    if not candidate_backend_ids:
        return None

    digest = hashlib.blake2b(prefix_cache_key.encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(candidate_backend_ids)
    return candidate_backend_ids[index]


def _eligible_backend_id_from_record(record: Any) -> str | None:
    if not isinstance(record, Mapping):
        return None
    backend_id = _normalize_optional_non_empty(record.get("backend_id"))
    if backend_id is None:
        return None

    metrics = record.get("metrics")
    if isinstance(metrics, Mapping):
        healthy = metrics.get("healthy")
        schedulable = metrics.get("schedulable")
        if healthy is False or schedulable is False:
            return None
    return backend_id


def _resolve_request_serving_context(request: Mapping[str, Any]) -> Mapping[str, Any] | None:
    serving_context = request.get("serving_context")
    if isinstance(serving_context, Mapping):
        return serving_context

    metadata = request.get("metadata")
    if isinstance(metadata, Mapping):
        metadata_serving_context = metadata.get("serving_context")
        if isinstance(metadata_serving_context, Mapping):
            return metadata_serving_context
    return None


def _normalize_optional_non_empty(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    return normalized


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


def _normalize_tags(raw_tags: Any) -> dict[str, str]:
    if not isinstance(raw_tags, Mapping):
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_value in raw_tags.items():
        key = _normalize_optional_non_empty(raw_key)
        value = _normalize_optional_non_empty(raw_value)
        if key is None or value is None:
            continue
        normalized[key] = value
    return normalized


def _normalize_capability_mapping(raw_capabilities: Any) -> dict[str, Any]:
    if not isinstance(raw_capabilities, Mapping):
        return {}
    normalized: dict[str, Any] = {}
    for raw_key, raw_value in raw_capabilities.items():
        key = _normalize_optional_non_empty(raw_key)
        if key is None:
            continue
        normalized[key] = _normalize_capability_value(raw_value)
    return normalized


def _normalize_capability_value(raw_value: Any) -> Any:
    if isinstance(raw_value, Mapping):
        return {
            str(key): _normalize_capability_value(value)
            for key, value in raw_value.items()
            if _normalize_optional_non_empty(key) is not None
        }
    if isinstance(raw_value, (list, tuple, set, frozenset)):
        return [_normalize_capability_value(item) for item in raw_value]
    return raw_value


__all__ = [
    "submit_backend_job",
    "resolve_actor_backend_requirements",
]
