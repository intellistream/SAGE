from __future__ import annotations

import inspect
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from sage.runtime.flownet.runtime.flowengine.loop_ctx import bind_loop_ctx

from .errors import LoopOperatorContractError
from .models import LoopGateEvaluation, LoopStepEvaluation, OperatorEvaluation, _LoopStepRuntimeCtx
from .process_ref import _coerce_flow_program_ref
from .protocols import LoopDirective, LoopSpec
from .utils import _normalize_iterable_outputs, _stable_key_fragment

_LOOP_MISSING = object()


def evaluate_loop_step(
    *,
    transformation: Any,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
    event_group_id: str | None,
    session_id: str | None = None,
    iteration: int = 0,
) -> LoopStepEvaluation:
    spec = _extract_loop_spec(transformation)
    resolved_iteration = _coerce_loop_iteration(iteration)
    resolved_session_id = (
        _coerce_loop_session_id(session_id)
        if session_id is not None
        else _build_loop_session_id(
            transformation=transformation,
            spec=spec,
            payload=payload,
            tags=tags,
            event_group_id=event_group_id,
        )
    )

    should_continue = bool(
        _invoke_loop_contract_target(
            contract_name="loop.condition",
            target=spec.condition,
            payload=payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
        )
    )
    if not should_continue:
        return LoopStepEvaluation(
            session_id=resolved_session_id,
            iteration=resolved_iteration,
            next_iteration=resolved_iteration,
            inner_outputs=(),
            outer_outputs=(),
            closed=True,
            close_reason="condition_false",
        )

    if resolved_iteration >= spec.max_iterations:
        raise LoopOperatorContractError(
            f"loop_max_iterations_exceeded:{spec.max_iterations}",
        )

    step_ctx = _LoopStepRuntimeCtx(
        iteration_index=resolved_iteration,
        session_id_value=resolved_session_id,
    )
    with bind_loop_ctx(step_ctx):
        body_result = _invoke_loop_contract_target(
            contract_name="loop.body",
            target=spec.body,
            payload=payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
        )

    inner_events, outer_events = _extract_loop_step_events(
        step_ctx=step_ctx,
        result=body_result,
    )
    return LoopStepEvaluation(
        session_id=resolved_session_id,
        iteration=resolved_iteration,
        next_iteration=resolved_iteration + 1,
        inner_outputs=inner_events,
        outer_outputs=outer_events,
        closed=step_ctx.closed,
        close_reason=step_ctx.close_reason,
    )


def evaluate_loop_gate(
    *,
    transformation: Any,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
    event_group_id: str | None,
    session_id: str | None = None,
    iteration: int = 0,
) -> LoopGateEvaluation:
    spec = _extract_loop_spec(transformation)
    resolved_iteration = _coerce_loop_iteration(iteration)
    resolved_session_id = (
        _coerce_loop_session_id(session_id)
        if session_id is not None
        else _build_loop_session_id(
            transformation=transformation,
            spec=spec,
            payload=payload,
            tags=tags,
            event_group_id=event_group_id,
        )
    )

    should_continue = bool(
        _invoke_loop_contract_target(
            contract_name="loop.condition",
            target=spec.condition,
            payload=payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
        )
    )
    if not should_continue:
        return LoopGateEvaluation(
            session_id=resolved_session_id,
            iteration=resolved_iteration,
            should_continue=False,
            close_reason="condition_false",
        )

    if resolved_iteration >= spec.max_iterations:
        raise LoopOperatorContractError(
            f"loop_max_iterations_exceeded:{spec.max_iterations}",
        )

    return LoopGateEvaluation(
        session_id=resolved_session_id,
        iteration=resolved_iteration,
        should_continue=True,
        close_reason=None,
    )


def evaluate_loop_step_from_directives(
    *,
    session_id: str,
    iteration: int,
    directive_results: Iterable[Any],
) -> LoopStepEvaluation:
    resolved_iteration = _coerce_loop_iteration(iteration)
    resolved_session_id = _coerce_loop_session_id(session_id)
    step_ctx = _LoopStepRuntimeCtx(
        iteration_index=resolved_iteration,
        session_id_value=resolved_session_id,
    )

    inner_events: list[Any] = []
    outer_events: list[Any] = []
    for result in directive_results:
        inner_delta, outer_delta = _extract_loop_result_deltas(
            step_ctx=step_ctx,
            result=result,
        )
        inner_events.extend(inner_delta)
        outer_events.extend(outer_delta)

    return LoopStepEvaluation(
        session_id=resolved_session_id,
        iteration=resolved_iteration,
        next_iteration=resolved_iteration + 1,
        inner_outputs=tuple(inner_events),
        outer_outputs=tuple(outer_events),
        closed=step_ctx.closed,
        close_reason=step_ctx.close_reason,
    )


def _evaluate_loop(
    *,
    transformation: Any,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
    event_group_id: str | None,
) -> OperatorEvaluation:
    pending: deque[Any] = deque([payload])
    outputs: list[Any] = []
    loop_iteration = 0
    session_id: str | None = None
    while pending:
        step_payload = pending.popleft()
        step = evaluate_loop_step(
            transformation=transformation,
            payload=step_payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
            event_group_id=event_group_id,
            session_id=session_id,
            iteration=loop_iteration,
        )
        session_id = step.session_id
        outputs.extend(step.outer_outputs)
        loop_iteration = step.next_iteration

        if step.closed:
            pending.clear()
            break
        pending.extend(step.inner_outputs)

    return OperatorEvaluation(outputs=tuple(outputs))


def _extract_loop_spec(transformation: Any) -> LoopSpec:
    loop_meta = _extract_loop_meta(transformation)
    return LoopSpec(
        body=_extract_loop_body(loop_meta),
        condition=_extract_loop_condition(loop_meta),
        max_iterations=_extract_loop_max_iterations(loop_meta),
        key_by=loop_meta.get("key_by"),
    )


def _extract_loop_meta(transformation: Any) -> Mapping[str, Any]:
    operator_config = getattr(transformation, "operator_config", None)
    if not isinstance(operator_config, Mapping):
        raise LoopOperatorContractError("loop operator_config must be a mapping.")
    loop_meta = operator_config.get("loop")
    if not isinstance(loop_meta, Mapping):
        raise LoopOperatorContractError("loop operator_config.loop must be a mapping.")
    return loop_meta


def _extract_loop_body(loop_meta: Mapping[str, Any]) -> Any:
    body = loop_meta.get("body", _LOOP_MISSING)
    if body is _LOOP_MISSING:
        raise LoopOperatorContractError("loop.body is required.")
    return body


def _extract_loop_condition(loop_meta: Mapping[str, Any]) -> Any:
    condition = loop_meta.get("condition", _LOOP_MISSING)
    if condition is _LOOP_MISSING:
        raise LoopOperatorContractError("loop.condition is required.")
    if _coerce_flow_program_ref(condition) is not None:
        raise LoopOperatorContractError("loop.condition does not support flow-program references.")
    return condition


def _extract_loop_max_iterations(loop_meta: Mapping[str, Any]) -> int:
    raw_value = loop_meta.get("max_iterations")
    try:
        max_iterations = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise LoopOperatorContractError("loop.max_iterations must be an integer > 0.") from exc
    if max_iterations <= 0:
        raise LoopOperatorContractError("loop.max_iterations must be an integer > 0.")
    return max_iterations


def _coerce_loop_iteration(raw_iteration: Any) -> int:
    try:
        resolved = int(raw_iteration)
    except (TypeError, ValueError) as exc:
        raise LoopOperatorContractError("loop.iteration must be an integer >= 0.") from exc
    if resolved < 0:
        raise LoopOperatorContractError("loop.iteration must be an integer >= 0.")
    return resolved


def _coerce_loop_session_id(raw_session_id: Any) -> str:
    if not isinstance(raw_session_id, str):
        raise LoopOperatorContractError("loop.session_id must be a string.")
    session_id = raw_session_id.strip()
    if not session_id:
        raise LoopOperatorContractError("loop.session_id must not be empty.")
    return session_id


def _resolve_loop_session_key_source(
    *,
    spec: LoopSpec,
    payload: Any,
    tags: Mapping[str, str],
) -> Any:
    key_by = spec.key_by
    if key_by is None:
        partition_key = tags.get("state_partition_key")
        if isinstance(partition_key, str) and partition_key.strip():
            return partition_key.strip()
        return payload

    if isinstance(key_by, int):
        if not isinstance(payload, (list, tuple)):
            raise LoopOperatorContractError(
                "loop.key_by int requires list/tuple payload.",
            )
        if key_by < 0 or key_by >= len(payload):
            raise LoopOperatorContractError("loop.key_by index out of range.")
        return payload[key_by]

    if isinstance(key_by, str):
        key_field = key_by.strip()
        if not key_field:
            raise LoopOperatorContractError("loop.key_by must be non-empty when str.")
        if isinstance(payload, Mapping) and key_field in payload:
            return payload[key_field]
        if key_field in tags:
            return tags[key_field]
        raise LoopOperatorContractError(
            f"loop.key_by field '{key_field}' is missing in payload/tags.",
        )

    raise LoopOperatorContractError("loop.key_by must be int or str when provided.")


def _build_loop_session_id(
    *,
    transformation: Any,
    spec: LoopSpec,
    payload: Any,
    tags: Mapping[str, str],
    event_group_id: str | None,
) -> str:
    trans_id = getattr(transformation, "trans_id", None)
    if not isinstance(trans_id, str) or not trans_id.strip():
        trans_id = "loop"
    event_group_fragment = (
        event_group_id.strip()
        if isinstance(event_group_id, str) and event_group_id.strip()
        else "__event_group__"
    )
    key_source = _resolve_loop_session_key_source(
        spec=spec,
        payload=payload,
        tags=tags,
    )
    key_fragment = _stable_key_fragment(key_source)
    return f"{event_group_fragment}:{trans_id}:{key_fragment}"


def _invoke_loop_contract_target(
    *,
    contract_name: str,
    target: Any,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
) -> Any:
    if callable(target):
        return _invoke_loop_callable(
            target=target,
            payload=payload,
            tags=tags,
            seq=seq,
        )
    if _coerce_flow_program_ref(target) is not None:
        raise LoopOperatorContractError(
            f"{contract_name} flow-program reference is not supported in phase-1 runtime.",
        )
    if invoke_target is None:
        raise LoopOperatorContractError(
            f"{contract_name} requires callable or invoke_target runtime support.",
        )
    return invoke_target(target, payload, tags, seq)


def _invoke_loop_callable(
    *,
    target: Callable[..., Any],
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
) -> Any:
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return target(payload)

    positional_capacity = 0
    has_var_positional = False
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            has_var_positional = True
            break
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional_capacity += 1

    if has_var_positional:
        return target(payload, tags, seq)
    if positional_capacity >= 3:
        return target(payload, tags, seq)
    if positional_capacity == 2:
        return target(payload, tags)
    if positional_capacity == 1:
        return target(payload)
    return target()


def _extract_loop_step_events(
    *,
    step_ctx: _LoopStepRuntimeCtx,
    result: Any,
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    inner_events = list(step_ctx._inner_events)
    outer_events = list(step_ctx._outer_events)

    inner_delta, outer_delta = _extract_loop_result_deltas(
        step_ctx=step_ctx,
        result=result,
    )
    inner_events.extend(inner_delta)
    outer_events.extend(outer_delta)

    if step_ctx.closed and inner_events:
        raise LoopOperatorContractError(
            "loop step produced continue_events after close.",
        )
    return tuple(inner_events), tuple(outer_events)


def _extract_loop_result_deltas(
    *,
    step_ctx: _LoopStepRuntimeCtx,
    result: Any,
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    inner_events: list[Any] = []
    outer_events: list[Any] = []

    directive = _parse_loop_directive(result)
    if directive is not None:
        inner_events.extend(directive.continue_events)
        inner_events.extend(directive.state_events)
        outer_events.extend(directive.emit_events)
        if directive.done:
            step_ctx.close(reason=directive.close_reason or "done")
    elif result is not None:
        inner_events.extend(_normalize_iterable_outputs(result))

    if step_ctx.closed and inner_events:
        raise LoopOperatorContractError(
            "loop step produced continue_events after close.",
        )
    return tuple(inner_events), tuple(outer_events)


def _parse_loop_directive(result: Any) -> LoopDirective | None:
    if not isinstance(result, Mapping):
        return None
    if not _is_loop_step_result_mapping(result):
        return None

    continue_events = result.get("continue_events")
    emit_events = result.get("emit_events")
    state_value = result.get("state", _LOOP_MISSING)

    done = bool(result.get("done", False))
    close_reason_raw = result.get("close_reason")
    if close_reason_raw is not None and not done:
        raise LoopOperatorContractError("loop.close_reason requires done=True.")

    return LoopDirective(
        continue_events=(
            _normalize_iterable_outputs(continue_events) if continue_events is not None else ()
        ),
        emit_events=(_normalize_iterable_outputs(emit_events) if emit_events is not None else ()),
        state_events=(
            _normalize_iterable_outputs(state_value) if state_value is not _LOOP_MISSING else ()
        ),
        done=done,
        close_reason=(str(close_reason_raw or "done") if done else None),
    )


def _is_loop_step_result_mapping(result: Any) -> bool:
    if not isinstance(result, Mapping):
        return False
    return any(
        field_name in result
        for field_name in (
            "continue_events",
            "emit_events",
            "done",
            "close_reason",
        )
    )


__all__ = [
    "evaluate_loop_step",
    "evaluate_loop_gate",
    "evaluate_loop_step_from_directives",
    "_evaluate_loop",
]
