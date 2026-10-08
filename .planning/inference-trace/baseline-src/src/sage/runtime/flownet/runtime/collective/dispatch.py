from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import CollectiveExecutionRequest, CollectiveExecutionResponse
from .registry import CollectiveExecutorRegistry, get_default_registry


def dispatch_collective(
    request: CollectiveExecutionRequest,
    *,
    registry: CollectiveExecutorRegistry | None = None,
) -> CollectiveExecutionResponse:
    active_registry = registry or get_default_registry()
    executor = active_registry.resolve_executor(
        mode=request.backend_mode,
        path_tag=request.path_tag,
    )
    if executor is None:
        snapshot = active_registry.snapshot()
        raise RuntimeError(
            "collective_executor_not_found:"
            f"mode={request.backend_mode},path_tag={request.path_tag},"
            f"available_modes={','.join(snapshot.get('modes', ())) or '-'},"
            f"available_path_tags={','.join(snapshot.get('path_tags', ())) or '-'}",
        )
    return executor.execute(request)


def build_dispatcher(
    *,
    registry: CollectiveExecutorRegistry | None = None,
):
    active_registry = registry or get_default_registry()

    def _dispatcher(raw_request: Any) -> Mapping[int, Mapping[str, Any]]:
        request = _coerce_dispatch_request(raw_request)
        response = dispatch_collective(
            request,
            registry=active_registry,
        )
        return _response_to_rank_payload_mapping(
            request=request,
            response=response,
        )

    return _dispatcher


def get_default_dispatcher():
    return build_dispatcher(registry=get_default_registry())


dispatcher = get_default_dispatcher()


def _coerce_dispatch_request(raw_request: Any) -> CollectiveExecutionRequest:
    if isinstance(raw_request, CollectiveExecutionRequest):
        return raw_request

    spec = getattr(raw_request, "spec", None)
    tensor_by_rank = getattr(raw_request, "tensor_by_rank", None)
    route_targets_by_rank = getattr(raw_request, "route_targets_by_rank", None)
    if spec is None or not isinstance(tensor_by_rank, Mapping):
        raise TypeError(
            "collective dispatch request must be CollectiveExecutionRequest or runtime dispatch payload."
        )

    kind = str(getattr(spec, "kind", "") or "").strip().lower()
    stage_id = str(getattr(spec, "stage_id", "") or "").strip() or "collective"
    group = str(getattr(spec, "group", "") or "").strip() or "default"
    round_key = str(getattr(spec, "round_id", "") or "").strip() or "round"
    world_size = int(getattr(spec, "world_size", len(tensor_by_rank)) or len(tensor_by_rank))
    backend_mode = str(getattr(spec, "backend", "auto") or "auto").strip().lower() or "auto"
    strict = bool(getattr(spec, "strict", True))
    tensor_field = str(getattr(spec, "tensor_field", "tensor") or "tensor").strip() or "tensor"
    rank_field = str(getattr(spec, "rank_field", "rank") or "rank").strip() or "rank"
    route_field_raw = getattr(spec, "route_field", None)
    route_field = str(route_field_raw).strip() if route_field_raw is not None else None
    reduce_op_raw = getattr(spec, "reduce_op", None)
    reduce_op = str(reduce_op_raw).strip().lower() if reduce_op_raw is not None else None
    path_tag_raw = getattr(spec, "path_tag", None)
    path_tag = str(path_tag_raw).strip() if path_tag_raw is not None else None
    if path_tag == "":
        path_tag = None

    resolved_route_targets_by_rank: dict[int, tuple[int, ...]] = {}
    if isinstance(route_targets_by_rank, Mapping):
        for raw_rank, raw_targets in route_targets_by_rank.items():
            rank = int(raw_rank)
            if isinstance(raw_targets, (list, tuple, set)):
                resolved_route_targets_by_rank[rank] = tuple(int(item) for item in raw_targets)
            else:
                resolved_route_targets_by_rank[rank] = (int(raw_targets),)

    metadata: dict[str, Any] = {}
    for field_name in (
        "requested_backend",
        "requested_algorithm",
        "selector_rule_id",
        "selector_reason",
        "message_bytes",
        "device_type",
        "algorithm",
    ):
        if hasattr(spec, field_name):
            metadata[field_name] = getattr(spec, field_name)

    return CollectiveExecutionRequest(
        kind=kind,
        stage_id=stage_id,
        group=group,
        round_key=round_key,
        world_size=world_size,
        backend_mode=backend_mode,
        strict=strict,
        tensor_field=tensor_field,
        rank_field=rank_field,
        route_field=route_field,
        reduce_op=reduce_op,
        path_tag=path_tag,
        tensor_by_rank={int(rank): value for rank, value in tensor_by_rank.items()},
        route_targets_by_rank=resolved_route_targets_by_rank,
        metadata=metadata,
    )


def _response_to_rank_payload_mapping(
    *,
    request: CollectiveExecutionRequest,
    response: CollectiveExecutionResponse,
) -> Mapping[int, Mapping[str, Any]]:
    output_tensor_by_rank = response.output_tensor_by_rank
    if output_tensor_by_rank is None:
        raise RuntimeError("collective_dispatch_response_missing_output_tensor_by_rank")
    payload_by_rank: dict[int, dict[str, Any]] = {}
    for rank in sorted(request.tensor_by_rank.keys()):
        if rank not in output_tensor_by_rank:
            raise RuntimeError(f"collective_dispatch_missing_rank_output:rank={rank}")
        payload_by_rank[rank] = {
            request.tensor_field: output_tensor_by_rank[rank],
            "collective_backend_impl": str(response.backend_impl),
            "collective_backend_type": str(response.backend_type),
            "collective_runtime_dispatch": bool(response.runtime_dispatch),
            "collective_fallback_used": bool(response.fallback_used),
            "collective_fallback_reason": str(response.fallback_reason or ""),
        }
    return payload_by_rank


__all__ = [
    "dispatch_collective",
    "build_dispatcher",
    "get_default_dispatcher",
    "dispatcher",
]
