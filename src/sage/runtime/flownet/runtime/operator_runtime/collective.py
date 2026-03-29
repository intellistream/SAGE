from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

from ..collective.contracts import CollectiveExecutionRequest, CollectiveExecutionResponse
from ..collective.registry import CollectiveExecutorRegistry
from .errors import CollectiveContractError
from .models import OperatorEvaluation, _CollectiveFrame, _CollectiveRoundState
from .protocols import CollectiveSpec
from .utils import (
    _extract_mapping_value,
    _parse_non_negative_int_strict,
    _parse_positive_int_strict,
    _stable_key_fragment,
)


class CollectiveRuntime:
    """
    Minimal in-memory runtime for `sys/collective`.

    Contract freeze (M9 first slice):
    1. state key = `(operator identity, event_group_id, stage_id, group, round_key)`.
    2. one frame per rank per round (`rank_field`), duplicate rank is contract violation.
    3. round closes only when `world_size` unique ranks arrive.
    4. `all_to_all` list route expansion is supported in topic-fallback semantics.
    """

    def __init__(
        self,
        *,
        time_fn: Callable[[], float] | None = None,
        executor_registry: CollectiveExecutorRegistry | None = None,
    ) -> None:
        self._time_fn = time_fn or time.monotonic
        self._states: dict[tuple[int, str, str, str, str], _CollectiveRoundState] = {}
        self._executor_registry = executor_registry

    def evaluate(
        self,
        *,
        transformation: Any,
        payload: Any,
        tags: Mapping[str, str],
        event_group_id: str | None,
    ) -> OperatorEvaluation:
        if not isinstance(event_group_id, str) or not event_group_id.strip():
            raise CollectiveContractError(
                "sys/collective requires a non-empty event_group_id for round isolation.",
            )
        spec = _extract_collective_spec(transformation)

        round_key = _build_collective_round_key(
            spec=spec,
            payload=payload,
            tags=tags,
            event_group_id=event_group_id,
        )
        state_key = (id(transformation), event_group_id, spec.stage_id, spec.group, round_key)

        now = self._time_fn()
        state = self._states.get(state_key)
        if state is not None and _collective_round_timed_out(
            state=state,
            now=now,
            timeout_ms=spec.timeout_ms,
        ):
            self._states.pop(state_key, None)
            state = None
            if spec.strict:
                raise CollectiveContractError(
                    "collective_round_timeout:"
                    f"stage_id={spec.stage_id},group={spec.group},round_key={round_key}",
                )

        if state is None:
            state = _CollectiveRoundState(
                kind=spec.kind,
                stage_id=spec.stage_id,
                group=spec.group,
                round_key=round_key,
                world_size=spec.world_size,
                start_time=now,
            )
            self._states[state_key] = state

        rank = _resolve_collective_rank(
            spec=spec,
            payload=payload,
            tags=tags,
        )
        tensor = _resolve_collective_tensor(
            spec=spec,
            payload=payload,
        )
        route_targets = _resolve_collective_route_targets(
            spec=spec,
            payload=payload,
            tags=tags,
        )
        if rank in state.frames and spec.strict:
            raise CollectiveContractError(
                "collective_duplicate_rank_in_round:"
                f"rank={rank},stage_id={spec.stage_id},group={spec.group},round_key={round_key}",
            )
        state.frames[rank] = _CollectiveFrame(
            rank=rank,
            payload=payload,
            tensor=tensor,
            route_targets=route_targets,
        )
        if len(state.frames) < spec.world_size:
            return OperatorEvaluation(outputs=())
        outputs, output_tags = _resolve_collective_outputs(
            state=state,
            spec=spec,
            event_group_id=event_group_id,
            executor_registry=self._executor_registry,
        )
        self._states.pop(state_key, None)
        return OperatorEvaluation(
            outputs=outputs,
            output_tags=output_tags,
        )


def _extract_collective_spec(transformation: Any) -> CollectiveSpec:
    operator_config = getattr(transformation, "operator_config", None)
    if not isinstance(operator_config, Mapping):
        raise CollectiveContractError("collective operator_config must be a mapping.")
    collective_meta = operator_config.get("collective")
    if not isinstance(collective_meta, Mapping):
        raise CollectiveContractError("collective operator_config.collective must be a mapping.")

    kind = _collective_as_non_empty_str(
        collective_meta.get("kind"),
        field_name="collective.kind",
    ).lower()
    if kind not in {"all_to_all", "all_reduce", "all_gather"}:
        raise CollectiveContractError(
            "collective.kind must be one of: all_to_all, all_reduce, all_gather.",
        )
    group = _collective_as_non_empty_str(
        collective_meta.get("group"),
        field_name="collective.group",
    )
    world_size = _parse_positive_int_strict(
        collective_meta.get("world_size"),
        field_name="collective.world_size",
        exc_type=CollectiveContractError,
    )
    rank_field = _collective_as_non_empty_str(
        collective_meta.get("rank_field"),
        field_name="collective.rank_field",
    )
    tensor_field = _collective_as_non_empty_str(
        collective_meta.get("tensor_field"),
        field_name="collective.tensor_field",
    )
    round_fields = _extract_collective_round_fields(collective_meta)
    timeout_ms = _parse_positive_int_strict(
        collective_meta.get("timeout_ms", 2_000),
        field_name="collective.timeout_ms",
        exc_type=CollectiveContractError,
    )
    backend = str(collective_meta.get("backend", "auto") or "").strip().lower() or "auto"
    if backend not in {"auto", "topic_fallback", "fast_channel"}:
        raise CollectiveContractError(
            "collective.backend must be one of: auto, topic_fallback, fast_channel.",
        )
    path_tag: str | None = None
    if "path_tag" in collective_meta:
        path_tag = _collective_as_non_empty_str(
            collective_meta.get("path_tag"),
            field_name="collective.path_tag",
        )
    strict = bool(collective_meta.get("strict", True))
    stage_id = collective_meta.get("stage_id")
    if stage_id is None:
        stage_id = getattr(transformation, "trans_id", None)
    stage_id_value = _collective_as_non_empty_str(
        stage_id,
        field_name="collective.stage_id",
    )

    reduce_op: str | None = None
    route_field: str | None = None
    if kind == "all_reduce":
        reduce_op = str(collective_meta.get("reduce_op", "sum") or "").strip().lower() or "sum"
        if reduce_op not in {"sum", "max", "min", "mean"}:
            raise CollectiveContractError(
                "collective.reduce_op must be one of: sum, max, min, mean.",
            )
    if kind == "all_to_all":
        route_field = _collective_as_non_empty_str(
            collective_meta.get("route_field"),
            field_name="collective.route_field",
        )

    return CollectiveSpec(
        kind=kind,
        stage_id=stage_id_value,
        group=group,
        world_size=world_size,
        rank_field=rank_field,
        tensor_field=tensor_field,
        round_fields=round_fields,
        timeout_ms=timeout_ms,
        backend=backend,
        strict=strict,
        reduce_op=reduce_op,
        route_field=route_field,
        path_tag=path_tag,
    )


def _extract_collective_round_fields(collective_meta: Mapping[str, Any]) -> tuple[str, ...]:
    round_fields_raw = collective_meta.get("round_fields")
    if isinstance(round_fields_raw, str):
        round_field = round_fields_raw.strip()
        if not round_field:
            raise CollectiveContractError(
                "collective.round_fields entries must be non-empty strings."
            )
        return (round_field,)
    if not isinstance(round_fields_raw, (list, tuple)):
        raise CollectiveContractError("collective.round_fields must be a list/tuple[str] or str.")
    resolved: list[str] = []
    for index, raw_field in enumerate(round_fields_raw):
        if not isinstance(raw_field, str) or not raw_field.strip():
            raise CollectiveContractError(
                f"collective.round_fields[{index}] must be a non-empty string.",
            )
        resolved.append(raw_field.strip())
    if not resolved:
        raise CollectiveContractError("collective.round_fields must not be empty.")
    return tuple(resolved)


def _build_collective_round_key(
    *,
    spec: CollectiveSpec,
    payload: Any,
    tags: Mapping[str, str],
    event_group_id: str,
) -> str:
    round_values: list[Any] = []
    for round_field in spec.round_fields:
        value = _extract_mapping_value(payload, field_name=round_field)
        if value is None:
            value = tags.get(round_field)
        if value is None:
            raise CollectiveContractError(
                f"collective round field '{round_field}' is missing in payload/tags.",
            )
        round_values.append(value)
    return _stable_key_fragment(
        {
            "event_group_id": event_group_id,
            "stage_id": spec.stage_id,
            "group": spec.group,
            "round_fields": spec.round_fields,
            "round_values": tuple(round_values),
        }
    )


def _collective_round_timed_out(
    *,
    state: _CollectiveRoundState,
    now: float,
    timeout_ms: int,
) -> bool:
    timeout_seconds = float(timeout_ms) / 1000.0
    return (now - state.start_time) >= timeout_seconds


def _resolve_collective_rank(
    *,
    spec: CollectiveSpec,
    payload: Any,
    tags: Mapping[str, str],
) -> int:
    rank_value = _extract_mapping_value(payload, field_name=spec.rank_field)
    if rank_value is None:
        rank_value = tags.get(spec.rank_field)
    if rank_value is None:
        raise CollectiveContractError(
            f"collective rank field '{spec.rank_field}' is missing in payload/tags.",
        )
    rank = _parse_non_negative_int_strict(
        rank_value,
        field_name=f"collective.{spec.rank_field}",
        exc_type=CollectiveContractError,
    )
    if rank >= spec.world_size:
        raise CollectiveContractError(
            f"collective rank out of range: rank={rank}, world_size={spec.world_size}",
        )
    return rank


def _resolve_collective_tensor(
    *,
    spec: CollectiveSpec,
    payload: Any,
) -> Any:
    if not isinstance(payload, Mapping):
        raise CollectiveContractError("collective payload must be a mapping.")
    if spec.tensor_field not in payload:
        raise CollectiveContractError(
            f"collective tensor field '{spec.tensor_field}' is missing in payload.",
        )
    return payload[spec.tensor_field]


def _resolve_collective_route_targets(
    *,
    spec: CollectiveSpec,
    payload: Any,
    tags: Mapping[str, str],
) -> tuple[int, ...]:
    if spec.kind != "all_to_all":
        return ()
    if spec.route_field is None:
        raise CollectiveContractError("all_to_all requires collective.route_field.")

    route_value = _extract_mapping_value(payload, field_name=spec.route_field)
    if route_value is None:
        route_value = tags.get(spec.route_field)
    if route_value is None:
        raise CollectiveContractError(
            f"collective route field '{spec.route_field}' is missing in payload/tags.",
        )
    if isinstance(route_value, (list, tuple, set)):
        raw_targets = list(route_value)
    else:
        raw_targets = [route_value]
    resolved: list[int] = []
    for index, raw_target in enumerate(raw_targets):
        target = _parse_non_negative_int_strict(
            raw_target,
            field_name=f"collective.{spec.route_field}[{index}]",
            exc_type=CollectiveContractError,
        )
        if target >= spec.world_size:
            raise CollectiveContractError(
                "collective route target out of range:"
                f" target={target}, world_size={spec.world_size}",
            )
        resolved.append(target)
    return tuple(resolved)


def _resolve_collective_outputs(
    *,
    state: _CollectiveRoundState,
    spec: CollectiveSpec,
    event_group_id: str,
    executor_registry: CollectiveExecutorRegistry | None,
) -> tuple[tuple[Any, ...], tuple[dict[str, str], ...]]:
    local_outputs, local_tags = _materialize_collective_outputs(
        state=state,
        spec=spec,
    )
    dispatch_requested = bool(spec.path_tag) or spec.backend in {"auto", "fast_channel"}
    if not dispatch_requested:
        return local_outputs, local_tags
    if executor_registry is None:
        if _collective_dispatch_error_is_fatal(spec):
            raise CollectiveContractError(
                "collective_executor_registry_not_configured:"
                f"stage_id={spec.stage_id},group={spec.group},backend={spec.backend},path_tag={spec.path_tag}",
            )
        return local_outputs, _collective_with_fallback_tags(
            local_tags,
            fallback_reason="executor_registry_not_configured",
        )

    request = _build_collective_execution_request(
        state=state,
        spec=spec,
        event_group_id=event_group_id,
    )
    executor = executor_registry.resolve_executor(
        mode=spec.backend,
        path_tag=spec.path_tag,
    )
    if executor is None:
        if _collective_dispatch_error_is_fatal(spec):
            raise CollectiveContractError(
                "collective_executor_not_found:"
                f"stage_id={spec.stage_id},group={spec.group},backend={spec.backend},path_tag={spec.path_tag}",
            )
        return local_outputs, _collective_with_fallback_tags(
            local_tags,
            fallback_reason=(f"executor_not_found:backend={spec.backend},path_tag={spec.path_tag}"),
        )

    try:
        response = executor.execute(request)
    except Exception as exc:
        if _collective_dispatch_error_is_fatal(spec):
            raise CollectiveContractError(
                "collective_executor_dispatch_failed:"
                f"stage_id={spec.stage_id},group={spec.group},backend={spec.backend},path_tag={spec.path_tag}",
            ) from exc
        return local_outputs, _collective_with_fallback_tags(
            local_tags,
            fallback_reason=f"executor_dispatch_failed:{exc}",
        )

    try:
        outputs, output_tags = _materialize_collective_outputs_from_response(
            state=state,
            spec=spec,
            response=response,
        )
    except Exception as exc:
        if _collective_dispatch_error_is_fatal(spec):
            raise CollectiveContractError(
                "collective_executor_response_invalid:"
                f"stage_id={spec.stage_id},group={spec.group},backend={spec.backend},path_tag={spec.path_tag}",
            ) from exc
        return local_outputs, _collective_with_fallback_tags(
            local_tags,
            fallback_reason=f"executor_response_invalid:{exc}",
        )

    return outputs, _collective_with_dispatch_tags(output_tags, response=response)


def _collective_dispatch_error_is_fatal(spec: CollectiveSpec) -> bool:
    if not spec.strict:
        return False
    return bool(spec.path_tag) or spec.backend == "fast_channel"


def _build_collective_execution_request(
    *,
    state: _CollectiveRoundState,
    spec: CollectiveSpec,
    event_group_id: str,
) -> CollectiveExecutionRequest:
    tensor_by_rank = {
        int(rank): frame.tensor
        for rank, frame in sorted(state.frames.items(), key=lambda item: int(item[0]))
    }
    route_targets_by_rank = {
        int(rank): tuple(frame.route_targets)
        for rank, frame in sorted(state.frames.items(), key=lambda item: int(item[0]))
    }
    metadata = {
        "event_group_id": event_group_id,
        "stage_id": spec.stage_id,
        "group": spec.group,
        "round_key": state.round_key,
        "kind": spec.kind,
    }
    return CollectiveExecutionRequest(
        kind=spec.kind,
        stage_id=spec.stage_id,
        group=spec.group,
        round_key=state.round_key,
        world_size=spec.world_size,
        backend_mode=spec.backend,
        strict=spec.strict,
        tensor_field=spec.tensor_field,
        rank_field=spec.rank_field,
        route_field=spec.route_field,
        reduce_op=spec.reduce_op,
        path_tag=spec.path_tag,
        tensor_by_rank=tensor_by_rank,
        route_targets_by_rank=route_targets_by_rank,
        metadata=metadata,
    )


def _materialize_collective_outputs_from_response(
    *,
    state: _CollectiveRoundState,
    spec: CollectiveSpec,
    response: CollectiveExecutionResponse,
) -> tuple[tuple[Any, ...], tuple[dict[str, str], ...]]:
    if response.outputs is not None:
        outputs = tuple(response.outputs)
        raw_output_tags = response.output_tags
        if raw_output_tags is None:
            output_tags = tuple({} for _ in outputs)
        else:
            if len(raw_output_tags) != len(outputs):
                raise CollectiveContractError(
                    "collective_executor_output_tags_length_mismatch:"
                    f"outputs={len(outputs)},tags={len(raw_output_tags)}",
                )
            output_tags = tuple(
                {str(key): str(value) for key, value in dict(item).items()}
                for item in raw_output_tags
            )
        return outputs, output_tags

    output_tensor_by_rank = response.output_tensor_by_rank
    if not isinstance(output_tensor_by_rank, Mapping):
        raise CollectiveContractError(
            "collective executor response must provide output_tensor_by_rank."
        )
    if spec.kind == "all_to_all":
        raise CollectiveContractError(
            "collective executor all_to_all requires explicit outputs/output_tags response.",
        )

    outputs: list[Any] = []
    output_tags: list[dict[str, str]] = []
    sorted_ranks = sorted(state.frames)
    for rank in sorted_ranks:
        if rank not in output_tensor_by_rank:
            raise CollectiveContractError(f"collective executor missing output rank={rank}.")
        frame = state.frames[rank]
        output_payload = _clone_collective_payload(
            payload=frame.payload,
            tensor_field=spec.tensor_field,
            tensor_value=output_tensor_by_rank[rank],
        )
        outputs.append(output_payload)
        output_tags.append(
            _build_collective_output_tags(
                spec=spec,
                round_key=state.round_key,
                rank=rank,
                src_rank=rank,
            )
        )
    return tuple(outputs), tuple(output_tags)


def _collective_with_dispatch_tags(
    tags: tuple[dict[str, str], ...],
    *,
    response: CollectiveExecutionResponse,
) -> tuple[dict[str, str], ...]:
    enriched: list[dict[str, str]] = []
    for raw_tags in tags:
        item = dict(raw_tags)
        item["collective_runtime_dispatch"] = str(bool(response.runtime_dispatch)).lower()
        item["collective_backend_impl"] = str(response.backend_impl or "unknown")
        item["collective_backend_type"] = str(response.backend_type or "unknown")
        item["collective_fallback_used"] = str(bool(response.fallback_used)).lower()
        item["collective_fallback_reason"] = str(response.fallback_reason or "")
        enriched.append(item)
    return tuple(enriched)


def _collective_with_fallback_tags(
    tags: tuple[dict[str, str], ...],
    *,
    fallback_reason: str,
) -> tuple[dict[str, str], ...]:
    enriched: list[dict[str, str]] = []
    for raw_tags in tags:
        item = dict(raw_tags)
        item["collective_runtime_dispatch"] = "false"
        item["collective_fallback_used"] = "true"
        item["collective_fallback_reason"] = str(fallback_reason or "")
        enriched.append(item)
    return tuple(enriched)


def _materialize_collective_outputs(
    *,
    state: _CollectiveRoundState,
    spec: CollectiveSpec,
) -> tuple[tuple[Any, ...], tuple[dict[str, str], ...]]:
    round_key = state.round_key

    outputs: list[Any] = []
    output_tags: list[dict[str, str]] = []
    sorted_ranks = sorted(state.frames)
    if spec.kind == "all_gather":
        gathered = tuple(state.frames[rank].tensor for rank in sorted_ranks)
        for rank in sorted_ranks:
            frame = state.frames[rank]
            output_payload = _clone_collective_payload(
                payload=frame.payload,
                tensor_field=spec.tensor_field,
                tensor_value=gathered,
            )
            outputs.append(output_payload)
            output_tags.append(
                _build_collective_output_tags(
                    spec=spec,
                    round_key=round_key,
                    rank=rank,
                    src_rank=rank,
                )
            )
        return tuple(outputs), tuple(output_tags)

    if spec.kind == "all_reduce":
        if spec.reduce_op is None:
            raise CollectiveContractError("all_reduce requires collective.reduce_op.")
        reduced = _reduce_collective_values(
            values=tuple(state.frames[rank].tensor for rank in sorted_ranks),
            reduce_op=spec.reduce_op,
        )
        for rank in sorted_ranks:
            frame = state.frames[rank]
            output_payload = _clone_collective_payload(
                payload=frame.payload,
                tensor_field=spec.tensor_field,
                tensor_value=reduced,
            )
            outputs.append(output_payload)
            output_tags.append(
                _build_collective_output_tags(
                    spec=spec,
                    round_key=round_key,
                    rank=rank,
                    src_rank=rank,
                )
            )
        return tuple(outputs), tuple(output_tags)

    if spec.kind == "all_to_all":
        if spec.route_field is None:
            raise CollectiveContractError("all_to_all requires collective.route_field.")
        for src_rank in sorted_ranks:
            frame = state.frames[src_rank]
            for dst_rank in frame.route_targets:
                output_payload = _clone_collective_payload(
                    payload=frame.payload,
                    tensor_field=spec.tensor_field,
                    tensor_value=frame.tensor,
                )
                if isinstance(output_payload, dict):
                    output_payload[spec.rank_field] = dst_rank
                    output_payload[spec.route_field] = dst_rank
                    output_payload["collective_src_rank"] = src_rank
                outputs.append(output_payload)
                output_tags.append(
                    _build_collective_output_tags(
                        spec=spec,
                        round_key=round_key,
                        rank=dst_rank,
                        src_rank=src_rank,
                    )
                )
        return tuple(outputs), tuple(output_tags)

    raise CollectiveContractError(f"unsupported_collective_kind:{spec.kind}")


def _clone_collective_payload(
    *,
    payload: Any,
    tensor_field: str,
    tensor_value: Any,
) -> Any:
    if isinstance(payload, Mapping):
        cloned = dict(payload)
        cloned[tensor_field] = tensor_value
        return cloned
    return {
        "payload": payload,
        tensor_field: tensor_value,
    }


def _build_collective_output_tags(
    *,
    spec: CollectiveSpec,
    round_key: str,
    rank: int,
    src_rank: int,
) -> dict[str, str]:
    return {
        "collective_kind": spec.kind,
        "collective_group": spec.group,
        "collective_stage_id": spec.stage_id,
        "collective_round_key": str(round_key),
        "collective_world_size": str(spec.world_size),
        "collective_rank": str(rank),
        "collective_src_rank": str(src_rank),
    }


def _reduce_collective_values(
    *,
    values: tuple[Any, ...],
    reduce_op: str,
) -> Any:
    if not values:
        raise CollectiveContractError("collective reduce values must not be empty.")
    if reduce_op == "sum":
        acc = values[0]
        for value in values[1:]:
            try:
                acc = acc + value
            except Exception as exc:
                raise CollectiveContractError("collective all_reduce sum failed.") from exc
        return acc
    if reduce_op == "max":
        try:
            return max(values)
        except Exception as exc:
            raise CollectiveContractError("collective all_reduce max failed.") from exc
    if reduce_op == "min":
        try:
            return min(values)
        except Exception as exc:
            raise CollectiveContractError("collective all_reduce min failed.") from exc
    if reduce_op == "mean":
        acc = values[0]
        for value in values[1:]:
            try:
                acc = acc + value
            except Exception as exc:
                raise CollectiveContractError("collective all_reduce mean sum failed.") from exc
        try:
            return acc / len(values)
        except Exception as exc:
            raise CollectiveContractError("collective all_reduce mean division failed.") from exc
    raise CollectiveContractError(f"unsupported_collective_reduce_op:{reduce_op}")


def _collective_as_non_empty_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CollectiveContractError(f"{field_name} must be a non-empty string.")
    return value.strip()


__all__ = [
    "CollectiveRuntime",
]
