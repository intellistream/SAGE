from __future__ import annotations

from collections.abc import Callable, Mapping
from time import perf_counter
from typing import Any

from .collective import CollectiveRuntime
from .errors import (
    CollectiveContractError,
    JoinContractError,
    MergeReducerContractError,
    OperatorExecutionError,
    ProcessTargetResolutionError,
    ReducerContractError,
    StatefulProcessContractError,
    UnsupportedOperatorTypeError,
)
from .loop import _evaluate_loop
from .models import OperatorEvaluation
from .process_ref import _coerce_flow_program_ref, _resolve_process_program_ref
from .reducers import JoinReducerRuntime, MergeReducerRuntime, ReducerRuntime
from .routing import _evaluate_join, _evaluate_shuffle, _extract_route_node_ids
from .stateful import StatefulProcessRuntime, _invoke_stateful_target
from .utils import _normalize_iterable_outputs

_ADVANCED_UNSUPPORTED_OPERATOR_TYPES = frozenset()
_DEFAULT_PROCESS_FACTORY_TIMEOUT_MS = 50.0
_PROCESS_FACTORY_FAIL_OPEN_ERROR_TOKENS = (
    "scheduler_snapshot_unavailable",
    "cluster_scheduler_metrics_unavailable",
    "scheduler_unavailable",
)


def evaluate_operator(
    *,
    transformation: Any,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
    state_runtime: StatefulProcessRuntime | None = None,
    reducer_runtime: ReducerRuntime | None = None,
    join_reducer_runtime: JoinReducerRuntime | None = None,
    merge_reducer_runtime: MergeReducerRuntime | None = None,
    collective_runtime: CollectiveRuntime | None = None,
    event_group_id: str | None = None,
) -> OperatorEvaluation:
    operator_type = str(getattr(transformation, "type", "")).strip()
    if operator_type == "map":
        result = _invoke_target(transformation, payload, tags, seq, invoke_target)
        return OperatorEvaluation(outputs=(result,))

    if operator_type == "filter":
        keep = bool(_invoke_target(transformation, payload, tags, seq, invoke_target))
        return OperatorEvaluation(outputs=(payload,) if keep else ())

    if operator_type == "flatmap":
        result = _invoke_target(transformation, payload, tags, seq, invoke_target)
        return OperatorEvaluation(outputs=_normalize_iterable_outputs(result))

    if operator_type == "sys/loop":
        return _evaluate_loop(
            transformation=transformation,
            payload=payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
            event_group_id=event_group_id,
        )

    if operator_type in {"route", "sys/router"}:
        route_node_ids = _extract_route_node_ids(transformation)
        return OperatorEvaluation(outputs=(payload,), route_node_ids=route_node_ids)

    if operator_type == "process":
        return _evaluate_process_operator(
            transformation=transformation,
            payload=payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
        )

    if operator_type == "sys/shuffle":
        return _evaluate_shuffle(
            transformation=transformation,
            payload=payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
        )

    if operator_type == "sys/join":
        return _evaluate_join(
            transformation=transformation,
            payload=payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
        )

    if operator_type == "sys/stateful-process":
        if state_runtime is None:
            raise StatefulProcessContractError(
                "state_runtime_not_configured:operator_type=sys/stateful-process",
            )
        result = _invoke_stateful_target(
            transformation=transformation,
            payload=payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
            state_runtime=state_runtime,
        )
        return OperatorEvaluation(outputs=_normalize_iterable_outputs(result))

    if operator_type == "sys/reducer":
        if reducer_runtime is None:
            raise ReducerContractError(
                "reducer_runtime_not_configured:operator_type=sys/reducer",
            )
        outputs = reducer_runtime.evaluate(
            transformation=transformation,
            payload=payload,
            tags=tags,
            event_group_id=event_group_id,
        )
        return OperatorEvaluation(outputs=outputs)

    if operator_type == "sys/join-reducer":
        if join_reducer_runtime is None:
            raise JoinContractError(
                "join_reducer_runtime_not_configured:operator_type=sys/join-reducer",
            )
        outputs = join_reducer_runtime.evaluate(
            transformation=transformation,
            payload=payload,
            tags=tags,
            event_group_id=event_group_id,
        )
        return OperatorEvaluation(outputs=outputs)

    if operator_type == "sys/merge-reducer":
        if merge_reducer_runtime is None:
            raise MergeReducerContractError(
                "merge_reducer_runtime_not_configured:operator_type=sys/merge-reducer",
            )
        outputs = merge_reducer_runtime.evaluate(
            transformation=transformation,
            payload=payload,
            tags=tags,
            event_group_id=event_group_id,
        )
        return OperatorEvaluation(outputs=outputs)

    if operator_type == "sys/collective":
        if collective_runtime is None:
            raise CollectiveContractError(
                "collective_runtime_not_configured:operator_type=sys/collective",
            )
        return collective_runtime.evaluate(
            transformation=transformation,
            payload=payload,
            tags=tags,
            event_group_id=event_group_id,
        )

    if operator_type in _ADVANCED_UNSUPPORTED_OPERATOR_TYPES:
        raise UnsupportedOperatorTypeError(f"unsupported_operator_type:{operator_type}")

    raise UnsupportedOperatorTypeError(f"unsupported_operator_type:{operator_type}")


def _invoke_target(
    transformation: Any,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
) -> Any:
    if invoke_target is None:
        raise OperatorExecutionError(
            f"invoke_target_not_configured:operator_type={getattr(transformation, 'type', None)}",
        )
    target = getattr(transformation, "target", None)
    return invoke_target(target, payload, tags, seq)


def _evaluate_process_operator(
    *,
    transformation: Any,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
) -> OperatorEvaluation:
    target = getattr(transformation, "target", None)
    target_program_ref = _coerce_flow_program_ref(target)
    static_fallback_program_ref = _coerce_flow_program_ref(
        getattr(transformation, "pipe_flow", None)
    )
    if target_program_ref is not None:
        return OperatorEvaluation(
            outputs=(payload,),
            process_program_ref=target_program_ref,
        )

    if target is None:
        if static_fallback_program_ref is not None:
            return OperatorEvaluation(
                outputs=(payload,),
                process_program_ref=static_fallback_program_ref,
            )
        # Preserve the existing canonical error wording for empty process targets.
        child_program_ref = _resolve_process_program_ref(transformation)
        return OperatorEvaluation(
            outputs=(payload,),
            process_program_ref=child_program_ref,
        )

    if not _is_process_factory_target(target):
        if static_fallback_program_ref is not None:
            return OperatorEvaluation(
                outputs=(payload,),
                process_program_ref=static_fallback_program_ref,
            )
        child_program_ref = _resolve_process_program_ref(transformation)
        return OperatorEvaluation(
            outputs=(payload,),
            process_program_ref=child_program_ref,
        )

    timeout_ms = _resolve_process_factory_timeout_ms(transformation)
    started_at = perf_counter()
    try:
        raw_factory_result = _invoke_target(
            transformation=transformation,
            payload=payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
        )
    except Exception as exc:
        elapsed_ms = _elapsed_ms(started_at)
        if _is_process_factory_fail_open_error(exc) and static_fallback_program_ref is not None:
            return OperatorEvaluation(
                outputs=(payload,),
                process_program_ref=static_fallback_program_ref,
                process_meta={
                    "factory_outcome": "fallback",
                    "factory_resolution_ms": elapsed_ms,
                    "factory_calls_delta": 1,
                    "factory_fallback_reason": "timeout_or_scheduler_unavailable",
                },
            )
        raise ProcessTargetResolutionError(
            f"process_factory_call_failed:{exc.__class__.__name__}:{exc}",
        ) from exc

    elapsed_ms = _elapsed_ms(started_at)
    if elapsed_ms > timeout_ms:
        if static_fallback_program_ref is not None:
            return OperatorEvaluation(
                outputs=(payload,),
                process_program_ref=static_fallback_program_ref,
                process_meta={
                    "factory_outcome": "fallback",
                    "factory_resolution_ms": elapsed_ms,
                    "factory_calls_delta": 1,
                    "factory_fallback_reason": "timeout",
                },
            )
        raise ProcessTargetResolutionError(
            f"process_factory_timeout_exceeded:elapsed_ms={elapsed_ms},timeout_ms={timeout_ms}",
        )

    resolved_program_ref = _coerce_flow_program_ref(raw_factory_result)
    if resolved_program_ref is None:
        raise ProcessTargetResolutionError(
            "process_factory_invalid_contract:"
            " expected FlowProgramRef or canonical {program_uri, program_rev}.",
        )

    return OperatorEvaluation(
        outputs=(payload,),
        process_program_ref=resolved_program_ref,
        process_meta={
            "factory_outcome": "ok",
            "factory_resolution_ms": elapsed_ms,
            "factory_calls_delta": 1,
        },
    )


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1_000.0, 3)


def _resolve_process_factory_timeout_ms(transformation: Any) -> float:
    operator_config = getattr(transformation, "operator_config", None)
    if not isinstance(operator_config, Mapping):
        return _DEFAULT_PROCESS_FACTORY_TIMEOUT_MS
    process_meta = operator_config.get("process")
    if not isinstance(process_meta, Mapping):
        return _DEFAULT_PROCESS_FACTORY_TIMEOUT_MS
    raw_timeout = process_meta.get("factory_timeout_ms")
    if raw_timeout is None:
        return _DEFAULT_PROCESS_FACTORY_TIMEOUT_MS
    try:
        timeout_ms = float(raw_timeout)
    except Exception as exc:
        raise ProcessTargetResolutionError(
            f"process_factory_timeout_invalid:factory_timeout_ms={raw_timeout!r}",
        ) from exc
    if timeout_ms <= 0:
        raise ProcessTargetResolutionError(
            f"process_factory_timeout_invalid:factory_timeout_ms={raw_timeout!r}",
        )
    return timeout_ms


def _is_process_factory_fail_open_error(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    message = str(exc or "").strip().lower()
    if not message:
        return False
    return any(token in message for token in _PROCESS_FACTORY_FAIL_OPEN_ERROR_TOKENS)


def _is_process_factory_target(target: Any) -> bool:
    if callable(target):
        return True
    return _is_actor_target_like(target)


def _is_actor_target_like(target: Any) -> bool:
    if isinstance(target, Mapping):
        if _is_actor_replica_pool_target_like(target):
            return True
        return all(
            isinstance(target.get(field_name), str) and str(target.get(field_name)).strip()
            for field_name in ("address", "actor_id", "method")
        )
    return all(
        isinstance(getattr(target, field_name, None), str)
        and str(getattr(target, field_name, None)).strip()
        for field_name in ("address", "actor_id", "method")
    )


def _is_actor_replica_pool_target_like(target: Mapping[str, Any]) -> bool:
    kind = str(target.get("kind") or "").strip()
    if kind != "actor_replica_pool_ref":
        return False
    method = target.get("method")
    replicas = target.get("replicas")
    if not isinstance(method, str) or not method.strip():
        return False
    if not isinstance(replicas, list) or not replicas:
        return False
    for replica in replicas:
        if not isinstance(replica, Mapping):
            return False
        address = replica.get("address")
        actor_id = replica.get("actor_id")
        if not isinstance(address, str) or not address.strip():
            return False
        if not isinstance(actor_id, str) or not actor_id.strip():
            return False
    return True


__all__ = [
    "evaluate_operator",
]
