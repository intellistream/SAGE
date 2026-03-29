from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Callable, Iterable, Iterator, Mapping
from concurrent.futures import Future as ConcurrentFuture
from dataclasses import dataclass
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_models import (
    FLOW_STACK_FRAME_KIND_FLATMAP_CONTINUATION,
    FLOW_STACK_FRAME_KIND_LOOP_SCOPE,
    FLOW_STACK_FRAME_KIND_PROCESS_RETURN,
    EventCursor,
    FlowProgramRef,
    FlowStackFrame,
)
from sage.runtime.flownet.runtime.flowengine.operator_runtime import (
    CollectiveRuntime,
    FlatMapContinuationRuntime,
    FlatMapContractError,
    JoinReducerRuntime,
    LoopGateEvaluation,
    LoopOperatorContractError,
    LoopStepEvaluation,
    MergeReducerRuntime,
    OperatorExecutionError,
    ReducerRuntime,
    StatefulProcessRuntime,
    evaluate_loop_gate,
    evaluate_loop_step,
    evaluate_loop_step_from_directives,
    evaluate_operator,
    resolve_loop_body_program_ref,
)


@dataclass(frozen=True)
class CursorStepResult:
    operator_type: str
    next_cursors: tuple[EventCursor, ...]
    terminal_outputs: tuple[tuple[Any, dict[str, str]], ...]
    event_chain_delta: int
    process_called: bool

    @property
    def terminal_payloads(self) -> tuple[Any, ...]:
        return tuple(payload for payload, _tags in self.terminal_outputs)


_LOOP_BODY_SUBFLOW_FRAME_META_KEY = "loop_body_subflow_call"
_AGGREGATE_RESUME_PAYLOADS_FRAME_META_KEY = "aggregate_resume_payloads"
_LOOP_BODY_SUBFLOW_RESULT_META_KEY = "loop_body_subflow_result"
_FLOW_PROGRAM_LINEAGE_META_KEY = "flow_program_lineage"
_ESCALATION_DEPTH_META_KEY = "escalation_depth"
_ESCALATION_LAST_REF_META_KEY = "escalation_last_ref"
_ESCALATION_BUDGET_USED_META_KEY = "escalation_budget_used"
_FACTORY_RESOLUTION_MS_META_KEY = "factory_resolution_ms"
_FACTORY_OUTCOME_META_KEY = "factory_outcome"
_FACTORY_CALLS_COUNT_META_KEY = "factory_calls_count"

_DEFAULT_ESCALATION_MAX_DEPTH = 6
_DEFAULT_ESCALATION_MAX_BUDGET_STEPS = 1_200
_DEFAULT_ESCALATION_MAX_FACTORY_CALLS_PER_EVENT_GROUP = 32
_DEFAULT_ESCALATION_MAX_FANOUT_PER_RESOLUTION = 128


def materialize_exception_fallback_step(
    *,
    cursor: EventCursor,
    fallback_payloads: tuple[Any, ...],
    flow_program: Any | None,
) -> CursorStepResult:
    """Materialize fallback decision into canonical cursor-step semantics."""
    fallback_outputs = _bind_output_tags(
        base_tags=cursor.tags,
        outputs=fallback_payloads,
        output_tags=None,
    )
    downstream_node_ids = _resolve_cursor_downstream_node_ids(
        cursor=cursor,
        flow_program=flow_program,
    )
    if downstream_node_ids:
        next_cursors = _spawn_linear_cursors(
            cursor=cursor,
            outputs=fallback_outputs,
            downstream_node_ids=downstream_node_ids,
        )
        return CursorStepResult(
            operator_type="exception/fallback",
            next_cursors=next_cursors,
            terminal_outputs=(),
            event_chain_delta=len(next_cursors) - 1,
            process_called=False,
        )

    if cursor.flow_stack:
        next_cursors = _spawn_resume_cursors(
            cursor=cursor,
            outputs=fallback_outputs,
        )
        return CursorStepResult(
            operator_type="exception/fallback",
            next_cursors=next_cursors,
            terminal_outputs=(),
            event_chain_delta=len(next_cursors) - 1,
            process_called=False,
        )

    return CursorStepResult(
        operator_type="exception/fallback",
        next_cursors=(),
        terminal_outputs=fallback_outputs,
        event_chain_delta=-1,
        process_called=False,
    )


def materialize_exception_drop_step(
    *,
    action: str = "drop",
) -> CursorStepResult:
    normalized_action = str(action or "").strip() or "drop"
    if normalized_action not in {"drop", "abort"}:
        normalized_action = "drop"
    return CursorStepResult(
        operator_type=f"exception/{normalized_action}",
        next_cursors=(),
        terminal_outputs=(),
        event_chain_delta=-1,
        process_called=False,
    )


def execute_cursor_step(
    *,
    cursor: EventCursor,
    flow_program: Any,
    invoke_target: Callable[[Any, Any, dict[str, str], int | None], Any] | None = None,
    state_runtime: StatefulProcessRuntime | None = None,
    reducer_runtime: ReducerRuntime | None = None,
    join_reducer_runtime: JoinReducerRuntime | None = None,
    merge_reducer_runtime: MergeReducerRuntime | None = None,
    collective_runtime: CollectiveRuntime | None = None,
    flatmap_runtime: FlatMapContinuationRuntime | None = None,
    resolve_process_entry_nodes: Callable[[FlowProgramRef], tuple[str, ...]] | None = None,
    child_chain_id_factory: Callable[[EventCursor, Any, int], str] | None = None,
) -> CursorStepResult:
    transformation = _lookup_transformation(flow_program, cursor.pc_node_id)
    operator_type = str(getattr(transformation, "type", "")).strip()
    resolved_flatmap_runtime = flatmap_runtime or FlatMapContinuationRuntime()
    if operator_type == "flatmap":
        return _execute_flatmap_cursor_step(
            cursor=cursor,
            transformation=transformation,
            invoke_target=invoke_target,
            flatmap_runtime=resolved_flatmap_runtime,
        )
    if operator_type == "sys/loop":
        return _execute_loop_cursor_step(
            cursor=cursor,
            transformation=transformation,
            invoke_target=invoke_target,
            resolve_process_entry_nodes=resolve_process_entry_nodes,
            child_chain_id_factory=child_chain_id_factory,
        )

    evaluation = evaluate_operator(
        transformation=transformation,
        payload=cursor.payload,
        tags=cursor.tags,
        seq=cursor.seq,
        invoke_target=invoke_target,
        state_runtime=state_runtime,
        reducer_runtime=reducer_runtime,
        join_reducer_runtime=join_reducer_runtime,
        merge_reducer_runtime=merge_reducer_runtime,
        collective_runtime=collective_runtime,
        event_group_id=cursor.event_group_id,
    )
    output_items = _bind_output_tags(
        base_tags=cursor.tags,
        outputs=evaluation.outputs,
        output_tags=evaluation.output_tags,
    )

    if evaluation.process_program_ref is not None:
        if resolve_process_entry_nodes is None:
            raise OperatorExecutionError(
                "resolve_process_entry_nodes is required for process operator."
            )
        next_cursors = _spawn_process_cursors(
            cursor=cursor,
            transformation=transformation,
            outputs=output_items,
            process_program_ref=evaluation.process_program_ref,
            process_meta=evaluation.process_meta,
            resolve_process_entry_nodes=resolve_process_entry_nodes,
            child_chain_id_factory=child_chain_id_factory,
        )
        return CursorStepResult(
            operator_type=operator_type,
            next_cursors=next_cursors,
            terminal_outputs=(),
            event_chain_delta=len(next_cursors) - 1,
            process_called=True,
        )

    downstream_ids = _resolve_downstream_node_ids(
        transformation=transformation,
        route_node_ids=evaluation.route_node_ids,
    )
    if downstream_ids:
        next_cursors = _spawn_linear_cursors(
            cursor=cursor,
            outputs=output_items,
            downstream_node_ids=downstream_ids,
        )
        return CursorStepResult(
            operator_type=operator_type,
            next_cursors=next_cursors,
            terminal_outputs=(),
            event_chain_delta=len(next_cursors) - 1,
            process_called=False,
        )

    if _has_process_resume_frame(cursor.flow_stack):
        next_cursors = _spawn_resume_cursors(
            cursor=cursor,
            outputs=output_items,
        )
        return CursorStepResult(
            operator_type=operator_type,
            next_cursors=next_cursors,
            terminal_outputs=(),
            event_chain_delta=len(next_cursors) - 1,
            process_called=False,
        )

    return CursorStepResult(
        operator_type=operator_type,
        next_cursors=(),
        terminal_outputs=output_items,
        event_chain_delta=-1,
        process_called=False,
    )


def _execute_flatmap_cursor_step(
    *,
    cursor: EventCursor,
    transformation: Any,
    invoke_target: Callable[[Any, Any, dict[str, str], int | None], Any] | None,
    flatmap_runtime: FlatMapContinuationRuntime,
) -> CursorStepResult:
    flatmap_node_id = _resolve_transformation_node_id(
        transformation,
        operator_name="flatmap",
    )
    has_active_scope, flatmap_scope_frame, base_stack = _resolve_active_flatmap_scope_frame(
        cursor=cursor,
        flatmap_node_id=flatmap_node_id,
    )

    session_id: str | None = None
    should_continue = False
    outputs: tuple[Any, ...] = ()
    if has_active_scope:
        assert flatmap_scope_frame is not None  # narrowed by `has_active_scope`.
        session_id = _extract_flatmap_scope_session_id(flatmap_scope_frame)
        has_item, output = flatmap_runtime.advance_one(session_id=session_id)
        if has_item:
            outputs = (output,)
            should_continue = True
    else:
        result = _invoke_operator_target(
            transformation=transformation,
            payload=cursor.payload,
            tags=cursor.tags,
            seq=cursor.seq,
            invoke_target=invoke_target,
        )
        outputs, session_id, should_continue = _resolve_flatmap_outputs(
            result=result,
            cursor=cursor,
            flatmap_node_id=flatmap_node_id,
            flatmap_runtime=flatmap_runtime,
        )

    output_items = _bind_output_tags(
        base_tags=cursor.tags,
        outputs=outputs,
        output_tags=None,
    )
    stack_cursor = _clone_cursor_with_flow_stack(
        cursor=cursor,
        flow_stack=base_stack,
    )

    next_cursors: list[EventCursor] = []
    if should_continue and session_id is not None:
        flatmap_scope_frame = _build_flatmap_scope_frame(
            cursor=cursor,
            flatmap_node_id=flatmap_node_id,
            session_id=session_id,
            previous_frame=flatmap_scope_frame,
        )
        next_cursors.append(
            EventCursor(
                event_group_id=cursor.event_group_id,
                event_chain_id=cursor.event_chain_id,
                flow_program_ref=cursor.flow_program_ref,
                pc_node_id=cursor.pc_node_id,
                flow_stack=base_stack + (flatmap_scope_frame,),
                payload=cursor.payload,
                tags=dict(cursor.tags),
                seq=cursor.seq,
                origin_topic_ref=cursor.origin_topic_ref,
                convergence_topic_ref=cursor.convergence_topic_ref,
                convergence_topic_epoch=cursor.convergence_topic_epoch,
                meta=dict(cursor.meta),
            )
        )

    if output_items:
        downstream_ids = _resolve_downstream_node_ids(
            transformation=transformation,
            route_node_ids=None,
        )
        if downstream_ids:
            next_cursors.extend(
                _spawn_linear_cursors(
                    cursor=stack_cursor,
                    outputs=output_items,
                    downstream_node_ids=downstream_ids,
                )
            )
        elif _has_process_resume_frame(base_stack):
            next_cursors.extend(
                _spawn_resume_cursors(
                    cursor=stack_cursor,
                    outputs=output_items,
                )
            )
        else:
            return CursorStepResult(
                operator_type="flatmap",
                next_cursors=tuple(next_cursors),
                terminal_outputs=output_items,
                event_chain_delta=len(next_cursors) - 1,
                process_called=False,
            )

    return CursorStepResult(
        operator_type="flatmap",
        next_cursors=tuple(next_cursors),
        terminal_outputs=(),
        event_chain_delta=len(next_cursors) - 1,
        process_called=False,
    )


def _invoke_operator_target(
    *,
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


def _resolve_flatmap_outputs(
    *,
    result: Any,
    cursor: EventCursor,
    flatmap_node_id: str,
    flatmap_runtime: FlatMapContinuationRuntime,
) -> tuple[tuple[Any, ...], str | None, bool]:
    if _is_flatmap_future_like(result):
        if inspect.iscoroutine(result):
            result.close()
        raise FlatMapContractError(
            "flatmap_future_or_coroutine_return_not_supported",
        )

    if _is_flatmap_async_iterator(result):
        session_id = flatmap_runtime.allocate_session_id(
            event_group_id=cursor.event_group_id,
            event_chain_id=cursor.event_chain_id,
            pc_node_id=flatmap_node_id,
        )
        flatmap_runtime.register_async_iterator(
            session_id=session_id,
            iterator=result,
        )
        has_item, output = flatmap_runtime.advance_one(session_id=session_id)
        if has_item:
            return (output,), session_id, True
        return (), None, False

    if _is_flatmap_sync_iterator(result):
        session_id = flatmap_runtime.allocate_session_id(
            event_group_id=cursor.event_group_id,
            event_chain_id=cursor.event_chain_id,
            pc_node_id=flatmap_node_id,
        )
        flatmap_runtime.register_sync_iterator(
            session_id=session_id,
            iterator=result,
        )
        has_item, output = flatmap_runtime.advance_one(session_id=session_id)
        if has_item:
            return (output,), session_id, True
        return (), None, False

    if result is None:
        return (), None, False
    if isinstance(result, tuple):
        return result, None, False
    if isinstance(result, list):
        return tuple(result), None, False
    if isinstance(result, Mapping):
        return (result,), None, False
    if isinstance(result, (str, bytes, bytearray)):
        return (result,), None, False
    if isinstance(result, Iterator):
        return tuple(result), None, False
    if isinstance(result, Iterable):
        return tuple(result), None, False
    return (result,), None, False


def _is_flatmap_future_like(result: Any) -> bool:
    if inspect.isawaitable(result):
        return True
    if isinstance(result, ConcurrentFuture):
        return True
    return False


def _is_flatmap_sync_iterator(result: Any) -> bool:
    if inspect.isgenerator(result):
        return True
    return isinstance(result, Iterator) and not isinstance(
        result,
        (str, bytes, bytearray, Mapping),
    )


def _is_flatmap_async_iterator(result: Any) -> bool:
    if inspect.isasyncgen(result):
        return True
    return isinstance(result, AsyncIterator)


def _execute_loop_cursor_step(
    *,
    cursor: EventCursor,
    transformation: Any,
    invoke_target: Callable[[Any, Any, dict[str, str], int | None], Any] | None,
    resolve_process_entry_nodes: Callable[[FlowProgramRef], tuple[str, ...]] | None,
    child_chain_id_factory: Callable[[EventCursor, Any, int], str] | None,
) -> CursorStepResult:
    loop_node_id = _resolve_transformation_node_id(
        transformation,
        operator_name="loop",
    )
    has_active_loop_scope, loop_scope_frame, base_stack = _resolve_active_loop_scope_frame(
        cursor=cursor,
        loop_node_id=loop_node_id,
    )

    session_id: str | None = None
    iteration = 0
    if has_active_loop_scope:
        assert loop_scope_frame is not None  # narrowed by `has_active_loop_scope`.
        session_id = _extract_loop_scope_session_id(loop_scope_frame)
        iteration = _extract_loop_scope_iteration(loop_scope_frame)

    loop_body_program_ref = resolve_loop_body_program_ref(transformation)
    if _is_loop_body_subflow_result_cursor(cursor):
        if loop_body_program_ref is None:
            raise LoopOperatorContractError(
                "loop body subflow result marker requires flow-program body target.",
            )
        if not has_active_loop_scope or loop_scope_frame is None:
            raise LoopOperatorContractError(
                "loop body subflow result requires active loop scope frame.",
            )
        step = evaluate_loop_step_from_directives(
            session_id=session_id or _extract_loop_scope_session_id(loop_scope_frame),
            iteration=iteration,
            directive_results=_coerce_loop_body_directive_results(cursor.payload),
        )
        return _materialize_loop_step_result(
            cursor=cursor,
            transformation=transformation,
            loop_node_id=loop_node_id,
            base_stack=base_stack,
            previous_loop_scope_frame=loop_scope_frame,
            step=step,
            process_called=False,
        )

    if loop_body_program_ref is not None:
        if resolve_process_entry_nodes is None:
            raise OperatorExecutionError(
                "resolve_process_entry_nodes is required for loop body flow-program ref.",
            )
        gate: LoopGateEvaluation = evaluate_loop_gate(
            transformation=transformation,
            payload=cursor.payload,
            tags=cursor.tags,
            seq=cursor.seq,
            invoke_target=invoke_target,
            event_group_id=cursor.event_group_id,
            session_id=session_id,
            iteration=iteration,
        )
        if not gate.should_continue:
            closed_step = LoopStepEvaluation(
                session_id=gate.session_id,
                iteration=gate.iteration,
                next_iteration=gate.iteration,
                inner_outputs=(),
                outer_outputs=(),
                closed=True,
                close_reason=gate.close_reason,
            )
            return _materialize_loop_step_result(
                cursor=cursor,
                transformation=transformation,
                loop_node_id=loop_node_id,
                base_stack=base_stack,
                previous_loop_scope_frame=loop_scope_frame,
                step=closed_step,
                process_called=False,
            )

        loop_scope_frame_next = _build_loop_scope_frame(
            cursor=cursor,
            loop_node_id=loop_node_id,
            session_id=gate.session_id,
            next_iteration=gate.iteration,
            close_reason=None,
            previous_frame=loop_scope_frame,
        )
        loop_scoped_stack = base_stack + (loop_scope_frame_next,)
        body_input_tags = _merge_loop_tags(
            base_tags=cursor.tags,
            session_id=gate.session_id,
            iteration=gate.iteration,
        )
        body_cursor = _clone_cursor_with_flow_stack_and_meta(
            cursor=cursor,
            flow_stack=loop_scoped_stack,
            meta=_strip_loop_body_subflow_meta(cursor.meta),
        )
        next_cursors = _spawn_process_cursors(
            cursor=body_cursor,
            transformation=transformation,
            outputs=((cursor.payload, body_input_tags),),
            process_program_ref=loop_body_program_ref,
            process_meta=None,
            resolve_process_entry_nodes=resolve_process_entry_nodes,
            child_chain_id_factory=child_chain_id_factory,
            resume_node_ids_override=(cursor.pc_node_id,),
            frame_meta_overrides={
                _LOOP_BODY_SUBFLOW_FRAME_META_KEY: True,
                _AGGREGATE_RESUME_PAYLOADS_FRAME_META_KEY: True,
            },
            apply_guardrails=False,
            allow_lineage_repeat=True,
        )
        return CursorStepResult(
            operator_type="sys/loop",
            next_cursors=next_cursors,
            terminal_outputs=(),
            event_chain_delta=len(next_cursors) - 1,
            process_called=True,
        )

    step = evaluate_loop_step(
        transformation=transformation,
        payload=cursor.payload,
        tags=cursor.tags,
        seq=cursor.seq,
        invoke_target=invoke_target,
        event_group_id=cursor.event_group_id,
        session_id=session_id,
        iteration=iteration,
    )
    return _materialize_loop_step_result(
        cursor=cursor,
        transformation=transformation,
        loop_node_id=loop_node_id,
        base_stack=base_stack,
        previous_loop_scope_frame=loop_scope_frame,
        step=step,
        process_called=False,
    )


def _materialize_loop_step_result(
    *,
    cursor: EventCursor,
    transformation: Any,
    loop_node_id: str,
    base_stack: tuple[FlowStackFrame, ...],
    previous_loop_scope_frame: FlowStackFrame | None,
    step: LoopStepEvaluation,
    process_called: bool,
) -> CursorStepResult:
    loop_scope_frame_next = _build_loop_scope_frame(
        cursor=cursor,
        loop_node_id=loop_node_id,
        session_id=step.session_id,
        next_iteration=step.next_iteration,
        close_reason=step.close_reason,
        previous_frame=previous_loop_scope_frame,
    )
    loop_scoped_stack = base_stack + (loop_scope_frame_next,)
    sanitized_meta = _strip_loop_body_subflow_meta(cursor.meta)

    outer_tags = _merge_loop_tags(
        base_tags=cursor.tags,
        session_id=step.session_id,
        iteration=step.iteration,
    )
    outer_output_items = tuple((payload, dict(outer_tags)) for payload in step.outer_outputs)

    next_cursors: list[EventCursor] = []
    terminal_outputs: list[tuple[Any, dict[str, str]]] = []

    if not step.closed:
        inner_tags = _merge_loop_tags(
            base_tags=cursor.tags,
            session_id=step.session_id,
            iteration=step.next_iteration,
        )
        for payload in step.inner_outputs:
            next_cursors.append(
                EventCursor(
                    event_group_id=cursor.event_group_id,
                    event_chain_id=cursor.event_chain_id,
                    flow_program_ref=cursor.flow_program_ref,
                    pc_node_id=cursor.pc_node_id,
                    flow_stack=loop_scoped_stack,
                    payload=payload,
                    tags=dict(inner_tags),
                    seq=cursor.seq,
                    origin_topic_ref=cursor.origin_topic_ref,
                    convergence_topic_ref=cursor.convergence_topic_ref,
                    convergence_topic_epoch=cursor.convergence_topic_epoch,
                    meta=dict(sanitized_meta),
                )
            )

    if outer_output_items:
        downstream_ids = _resolve_downstream_node_ids(
            transformation=transformation,
            route_node_ids=None,
        )
        stack_cursor = _clone_cursor_with_flow_stack_and_meta(
            cursor=cursor,
            flow_stack=loop_scoped_stack,
            meta=sanitized_meta,
        )
        if downstream_ids:
            next_cursors.extend(
                _spawn_linear_cursors(
                    cursor=stack_cursor,
                    outputs=outer_output_items,
                    downstream_node_ids=downstream_ids,
                )
            )
        elif _has_process_resume_frame(loop_scoped_stack):
            next_cursors.extend(
                _spawn_resume_cursors(
                    cursor=stack_cursor,
                    outputs=outer_output_items,
                )
            )
        else:
            terminal_outputs.extend(
                (payload, dict(output_tags)) for payload, output_tags in outer_output_items
            )

    return CursorStepResult(
        operator_type="sys/loop",
        next_cursors=tuple(next_cursors),
        terminal_outputs=tuple(terminal_outputs),
        event_chain_delta=len(next_cursors) - 1,
        process_called=process_called,
    )


def _is_loop_body_subflow_result_cursor(cursor: EventCursor) -> bool:
    marker = cursor.meta.get(_LOOP_BODY_SUBFLOW_RESULT_META_KEY)
    if isinstance(marker, str):
        return marker.strip().lower() in {"1", "true", "yes", "on"}
    return bool(marker)


def _strip_loop_body_subflow_meta(meta: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(meta)
    copied.pop(_LOOP_BODY_SUBFLOW_RESULT_META_KEY, None)
    return copied


def _coerce_loop_body_directive_results(payload: Any) -> tuple[Any, ...]:
    if (
        isinstance(payload, Mapping)
        and str(payload.get("mode", "")).strip() == "loop_body_directive_batch"
    ):
        directives = payload.get("directives")
        if directives is None:
            return ()
        if isinstance(directives, tuple):
            return directives
        if isinstance(directives, list):
            return tuple(directives)
        raise LoopOperatorContractError("loop body directive batch directives must be list/tuple.")
    return (payload,)


def _bind_output_tags(
    *,
    base_tags: Mapping[str, str],
    outputs: tuple[Any, ...],
    output_tags: tuple[dict[str, str], ...] | None,
) -> tuple[tuple[Any, dict[str, str]], ...]:
    if output_tags is None:
        return tuple((payload, dict(base_tags)) for payload in outputs)
    if len(output_tags) != len(outputs):
        raise OperatorExecutionError("operator output_tags length must match outputs length.")

    resolved: list[tuple[Any, dict[str, str]]] = []
    for payload, overlay in zip(outputs, output_tags, strict=False):
        if not isinstance(overlay, Mapping):
            raise OperatorExecutionError("operator output_tags entries must be mappings.")
        merged_tags = dict(base_tags)
        for key, value in overlay.items():
            merged_tags[str(key)] = str(value)
        resolved.append((payload, merged_tags))
    return tuple(resolved)


def _lookup_transformation(flow_program: Any, pc_node_id: str) -> Any:
    lookup = getattr(flow_program, "lookup_transformation", None)
    transformation = lookup(pc_node_id) if callable(lookup) else None
    if transformation is None:
        transformations = getattr(flow_program, "transformations", None)
        if isinstance(transformations, dict):
            transformation = transformations.get(pc_node_id)

    if transformation is None:
        raise KeyError(f"unknown_pc_node_id:{pc_node_id}")
    return transformation


def _resolve_transformation_node_id(
    transformation: Any,
    *,
    operator_name: str,
) -> str:
    trans_id = getattr(transformation, "trans_id", None)
    if not isinstance(trans_id, str) or not trans_id.strip():
        raise OperatorExecutionError(f"{operator_name} transformation missing valid trans_id")
    return trans_id.strip()


def _resolve_active_flatmap_scope_frame(
    *,
    cursor: EventCursor,
    flatmap_node_id: str,
) -> tuple[bool, FlowStackFrame | None, tuple[FlowStackFrame, ...]]:
    if not cursor.flow_stack:
        return False, None, ()

    top_frame = cursor.flow_stack[-1]
    if _frame_kind(top_frame) != FLOW_STACK_FRAME_KIND_FLATMAP_CONTINUATION:
        return False, None, cursor.flow_stack

    continuation_node_id = _extract_flatmap_scope_node_id(top_frame)
    if continuation_node_id != flatmap_node_id:
        return False, None, cursor.flow_stack
    return True, top_frame, cursor.flow_stack[:-1]


def _extract_flatmap_scope_node_id(frame: FlowStackFrame) -> str:
    frame_meta = getattr(frame, "frame_meta", None)
    if not isinstance(frame_meta, Mapping):
        raise FlatMapContractError("flatmap_continuation frame_meta must be a mapping.")
    node_id = frame_meta.get("flatmap_node_id")
    if not isinstance(node_id, str) or not node_id.strip():
        raise FlatMapContractError(
            "flatmap_continuation frame_meta.flatmap_node_id must be a non-empty string.",
        )
    return node_id.strip()


def _extract_flatmap_scope_session_id(frame: FlowStackFrame) -> str:
    frame_meta = getattr(frame, "frame_meta", None)
    if not isinstance(frame_meta, Mapping):
        raise FlatMapContractError("flatmap_continuation frame_meta must be a mapping.")
    session_id = frame_meta.get("flatmap_session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise FlatMapContractError(
            "flatmap_continuation frame_meta.flatmap_session_id must be a non-empty string.",
        )
    return session_id.strip()


def _build_flatmap_scope_frame(
    *,
    cursor: EventCursor,
    flatmap_node_id: str,
    session_id: str,
    previous_frame: FlowStackFrame | None,
) -> FlowStackFrame:
    previous_meta = {}
    if previous_frame is not None and isinstance(previous_frame.frame_meta, Mapping):
        previous_meta = dict(previous_frame.frame_meta)
    frame_meta = dict(previous_meta)
    frame_meta["flatmap_node_id"] = flatmap_node_id
    frame_meta["flatmap_session_id"] = session_id

    if previous_frame is not None:
        caller_event_chain_id = previous_frame.caller_event_chain_id
        callsite_pc_node_id = previous_frame.callsite_pc_node_id
        resume_flow_program_ref = previous_frame.resume_flow_program_ref
        resume_pc_node_ids = previous_frame.resume_pc_node_ids
    else:
        caller_event_chain_id = cursor.event_chain_id
        callsite_pc_node_id = cursor.pc_node_id
        resume_flow_program_ref = cursor.flow_program_ref
        resume_pc_node_ids = (cursor.pc_node_id,)

    return FlowStackFrame(
        resume_flow_program_ref=resume_flow_program_ref,
        resume_pc_node_ids=tuple(resume_pc_node_ids),
        caller_event_chain_id=caller_event_chain_id,
        callsite_pc_node_id=callsite_pc_node_id,
        frame_meta=frame_meta,
        frame_kind=FLOW_STACK_FRAME_KIND_FLATMAP_CONTINUATION,
    )


def _resolve_active_loop_scope_frame(
    *,
    cursor: EventCursor,
    loop_node_id: str,
) -> tuple[bool, FlowStackFrame | None, tuple[FlowStackFrame, ...]]:
    if not cursor.flow_stack:
        return False, None, ()

    top_frame = cursor.flow_stack[-1]
    if _frame_kind(top_frame) != FLOW_STACK_FRAME_KIND_LOOP_SCOPE:
        return False, None, cursor.flow_stack

    loop_scope_node_id = _extract_loop_scope_node_id(top_frame)
    if loop_scope_node_id != loop_node_id:
        return False, None, cursor.flow_stack
    return True, top_frame, cursor.flow_stack[:-1]


def _extract_loop_scope_node_id(frame: FlowStackFrame) -> str:
    frame_meta = getattr(frame, "frame_meta", None)
    if not isinstance(frame_meta, Mapping):
        raise OperatorExecutionError("loop_scope frame_meta must be a mapping.")
    node_id = frame_meta.get("loop_node_id")
    if not isinstance(node_id, str) or not node_id.strip():
        raise OperatorExecutionError(
            "loop_scope frame_meta.loop_node_id must be a non-empty string."
        )
    return node_id.strip()


def _extract_loop_scope_session_id(frame: FlowStackFrame) -> str:
    frame_meta = getattr(frame, "frame_meta", None)
    if not isinstance(frame_meta, Mapping):
        raise OperatorExecutionError("loop_scope frame_meta must be a mapping.")
    session_id = frame_meta.get("loop_session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise OperatorExecutionError(
            "loop_scope frame_meta.loop_session_id must be a non-empty string."
        )
    return session_id.strip()


def _extract_loop_scope_iteration(frame: FlowStackFrame) -> int:
    frame_meta = getattr(frame, "frame_meta", None)
    if not isinstance(frame_meta, Mapping):
        raise OperatorExecutionError("loop_scope frame_meta must be a mapping.")
    raw_iteration = frame_meta.get("loop_iteration", 0)
    try:
        iteration = int(raw_iteration)
    except (TypeError, ValueError) as exc:
        raise OperatorExecutionError(
            "loop_scope frame_meta.loop_iteration must be an integer >= 0."
        ) from exc
    if iteration < 0:
        raise OperatorExecutionError(
            "loop_scope frame_meta.loop_iteration must be an integer >= 0."
        )
    return iteration


def _build_loop_scope_frame(
    *,
    cursor: EventCursor,
    loop_node_id: str,
    session_id: str,
    next_iteration: int,
    close_reason: str | None,
    previous_frame: FlowStackFrame | None,
) -> FlowStackFrame:
    previous_meta = {}
    if previous_frame is not None and isinstance(previous_frame.frame_meta, Mapping):
        previous_meta = dict(previous_frame.frame_meta)
    frame_meta = dict(previous_meta)
    frame_meta["loop_node_id"] = loop_node_id
    frame_meta["loop_session_id"] = session_id
    frame_meta["loop_iteration"] = int(next_iteration)
    if close_reason is None:
        frame_meta.pop("loop_close_reason", None)
    else:
        frame_meta["loop_close_reason"] = str(close_reason)

    if previous_frame is not None:
        caller_event_chain_id = previous_frame.caller_event_chain_id
        callsite_pc_node_id = previous_frame.callsite_pc_node_id
        resume_flow_program_ref = previous_frame.resume_flow_program_ref
        resume_pc_node_ids = previous_frame.resume_pc_node_ids
    else:
        caller_event_chain_id = cursor.event_chain_id
        callsite_pc_node_id = cursor.pc_node_id
        resume_flow_program_ref = cursor.flow_program_ref
        resume_pc_node_ids = (cursor.pc_node_id,)

    return FlowStackFrame(
        resume_flow_program_ref=resume_flow_program_ref,
        resume_pc_node_ids=tuple(resume_pc_node_ids),
        caller_event_chain_id=caller_event_chain_id,
        callsite_pc_node_id=callsite_pc_node_id,
        frame_meta=frame_meta,
        frame_kind=FLOW_STACK_FRAME_KIND_LOOP_SCOPE,
    )


def _merge_loop_tags(
    *,
    base_tags: Mapping[str, str],
    session_id: str,
    iteration: int,
) -> dict[str, str]:
    merged = dict(base_tags)
    merged["loop_session_id"] = session_id
    merged["loop_iteration"] = str(int(iteration))
    return merged


def _clone_cursor_with_flow_stack(
    *,
    cursor: EventCursor,
    flow_stack: tuple[FlowStackFrame, ...],
) -> EventCursor:
    return EventCursor(
        event_group_id=cursor.event_group_id,
        event_chain_id=cursor.event_chain_id,
        flow_program_ref=cursor.flow_program_ref,
        pc_node_id=cursor.pc_node_id,
        flow_stack=flow_stack,
        payload=cursor.payload,
        tags=dict(cursor.tags),
        seq=cursor.seq,
        origin_topic_ref=cursor.origin_topic_ref,
        convergence_topic_ref=cursor.convergence_topic_ref,
        convergence_topic_epoch=cursor.convergence_topic_epoch,
        meta=dict(cursor.meta),
    )


def _clone_cursor_with_flow_stack_and_meta(
    *,
    cursor: EventCursor,
    flow_stack: tuple[FlowStackFrame, ...],
    meta: Mapping[str, Any],
) -> EventCursor:
    return EventCursor(
        event_group_id=cursor.event_group_id,
        event_chain_id=cursor.event_chain_id,
        flow_program_ref=cursor.flow_program_ref,
        pc_node_id=cursor.pc_node_id,
        flow_stack=flow_stack,
        payload=cursor.payload,
        tags=dict(cursor.tags),
        seq=cursor.seq,
        origin_topic_ref=cursor.origin_topic_ref,
        convergence_topic_ref=cursor.convergence_topic_ref,
        convergence_topic_epoch=cursor.convergence_topic_epoch,
        meta=dict(meta),
    )


def _resolve_downstream_node_ids(
    *,
    transformation: Any,
    route_node_ids: tuple[str, ...] | None,
) -> tuple[str, ...]:
    if route_node_ids is not None:
        return route_node_ids

    downstreams = getattr(transformation, "downstreams", None)
    if downstreams is None:
        return ()
    if not isinstance(downstreams, list):
        raise OperatorExecutionError("transformation.downstreams must be a list.")

    downstream_ids: list[str] = []
    for index, downstream in enumerate(downstreams):
        trans_id = getattr(downstream, "trans_id", None)
        if not isinstance(trans_id, str) or not trans_id.strip():
            raise OperatorExecutionError(f"downstreams[{index}] missing valid trans_id")
        downstream_ids.append(trans_id)
    return tuple(downstream_ids)


def _spawn_linear_cursors(
    *,
    cursor: EventCursor,
    outputs: tuple[tuple[Any, dict[str, str]], ...],
    downstream_node_ids: tuple[str, ...],
) -> tuple[EventCursor, ...]:
    next_cursors: list[EventCursor] = []
    for payload, output_tags in outputs:
        for node_id in downstream_node_ids:
            next_cursors.append(
                EventCursor(
                    event_group_id=cursor.event_group_id,
                    event_chain_id=cursor.event_chain_id,
                    flow_program_ref=cursor.flow_program_ref,
                    pc_node_id=node_id,
                    flow_stack=cursor.flow_stack,
                    payload=payload,
                    tags=dict(output_tags),
                    seq=cursor.seq,
                    origin_topic_ref=cursor.origin_topic_ref,
                    convergence_topic_ref=cursor.convergence_topic_ref,
                    convergence_topic_epoch=cursor.convergence_topic_epoch,
                    meta=dict(cursor.meta),
                )
            )
    return tuple(next_cursors)


def _resolve_cursor_downstream_node_ids(
    *,
    cursor: EventCursor,
    flow_program: Any | None,
) -> tuple[str, ...]:
    if flow_program is None:
        return ()
    try:
        transformation = _lookup_transformation(flow_program, cursor.pc_node_id)
    except Exception:
        return ()

    downstreams = getattr(transformation, "downstreams", None)
    if not isinstance(downstreams, list):
        return ()

    downstream_ids: list[str] = []
    for downstream in downstreams:
        trans_id = getattr(downstream, "trans_id", None)
        if isinstance(trans_id, str) and trans_id.strip():
            downstream_ids.append(trans_id.strip())
    return tuple(downstream_ids)


def _spawn_process_cursors(
    *,
    cursor: EventCursor,
    transformation: Any,
    outputs: tuple[tuple[Any, dict[str, str]], ...],
    process_program_ref: FlowProgramRef,
    process_meta: Mapping[str, Any] | None,
    resolve_process_entry_nodes: Callable[[FlowProgramRef], tuple[str, ...]],
    child_chain_id_factory: Callable[[EventCursor, Any, int], str] | None,
    resume_node_ids_override: tuple[str, ...] | None = None,
    frame_meta_overrides: Mapping[str, Any] | None = None,
    apply_guardrails: bool = True,
    allow_lineage_repeat: bool = False,
) -> tuple[EventCursor, ...]:
    entry_nodes = tuple(resolve_process_entry_nodes(process_program_ref))
    if not entry_nodes:
        raise OperatorExecutionError(
            "process entry nodes must not be empty.",
        )
    fanout_count = len(outputs) * len(entry_nodes)

    guardrails = _resolve_process_guardrails(transformation) if apply_guardrails else None
    if guardrails is not None and fanout_count > guardrails["max_fanout_per_resolution"]:
        raise OperatorExecutionError(
            "process_escalation_guardrail_exceeded:"
            f" max_fanout_per_resolution={guardrails['max_fanout_per_resolution']},"
            f" fanout={fanout_count}",
        )

    ancestor_lineage = _resolve_lineage_from_meta(
        meta=cursor.meta,
        fallback_program_ref=cursor.flow_program_ref,
    )
    child_program_token = _program_ref_token(process_program_ref)
    if (
        guardrails is not None
        and not allow_lineage_repeat
        and child_program_token in ancestor_lineage
    ):
        raise OperatorExecutionError(
            f"process_escalation_cycle_detected:{child_program_token}",
        )

    new_lineage = ancestor_lineage + (child_program_token,)
    escalation_depth = max(0, len(new_lineage) - 1)
    if guardrails is not None and escalation_depth > guardrails["max_depth"]:
        raise OperatorExecutionError(
            "process_escalation_guardrail_exceeded:"
            f" max_depth={guardrails['max_depth']},"
            f" depth={escalation_depth}",
        )

    previous_budget_used = _coerce_non_negative_int(
        cursor.meta.get(_ESCALATION_BUDGET_USED_META_KEY),
        field_name=_ESCALATION_BUDGET_USED_META_KEY,
        default=0,
    )
    budget_increment = 1 if apply_guardrails else 0
    escalation_budget_used = previous_budget_used + budget_increment
    if guardrails is not None and escalation_budget_used > guardrails["max_budget_steps"]:
        raise OperatorExecutionError(
            "process_escalation_guardrail_exceeded:"
            f" max_budget_steps={guardrails['max_budget_steps']},"
            f" budget_used={escalation_budget_used}",
        )

    factory_calls_delta = _coerce_non_negative_int(
        (process_meta or {}).get("factory_calls_delta"),
        field_name="process_meta.factory_calls_delta",
        default=0,
    )
    previous_factory_calls_count = _coerce_non_negative_int(
        cursor.meta.get(_FACTORY_CALLS_COUNT_META_KEY),
        field_name=_FACTORY_CALLS_COUNT_META_KEY,
        default=0,
    )
    factory_calls_count = previous_factory_calls_count + factory_calls_delta
    if (
        guardrails is not None
        and factory_calls_count > guardrails["max_factory_calls_per_event_group"]
    ):
        raise OperatorExecutionError(
            "process_escalation_guardrail_exceeded:"
            f" max_factory_calls_per_event_group={guardrails['max_factory_calls_per_event_group']},"
            f" factory_calls={factory_calls_count}",
        )

    if resume_node_ids_override is None:
        resume_node_ids = _resolve_downstream_node_ids(
            transformation=transformation,
            route_node_ids=None,
        )
    else:
        resume_node_ids = tuple(resume_node_ids_override)
    frame = FlowStackFrame(
        resume_flow_program_ref=cursor.flow_program_ref,
        resume_pc_node_ids=resume_node_ids,
        caller_event_chain_id=cursor.event_chain_id,
        callsite_pc_node_id=cursor.pc_node_id,
        frame_meta=dict(frame_meta_overrides or {}),
        frame_kind=FLOW_STACK_FRAME_KIND_PROCESS_RETURN,
    )

    factory = child_chain_id_factory or _default_child_chain_id

    next_cursors: list[EventCursor] = []
    spawn_index = 0
    for payload, output_tags in outputs:
        for node_id in entry_nodes:
            child_chain_id = factory(cursor, transformation, spawn_index)
            spawn_index += 1
            child_meta = dict(cursor.meta)
            child_meta.setdefault("parent_event_chain_id", cursor.event_chain_id)
            child_meta.setdefault("process_callsite_pc_node_id", cursor.pc_node_id)
            child_meta[_FLOW_PROGRAM_LINEAGE_META_KEY] = list(new_lineage)
            child_meta[_ESCALATION_DEPTH_META_KEY] = escalation_depth
            child_meta[_ESCALATION_LAST_REF_META_KEY] = {
                "program_uri": process_program_ref.program_uri,
                "program_rev": process_program_ref.program_rev,
            }
            child_meta[_ESCALATION_BUDGET_USED_META_KEY] = escalation_budget_used
            child_meta[_FACTORY_CALLS_COUNT_META_KEY] = factory_calls_count
            _merge_process_meta_into_child_meta(
                child_meta=child_meta,
                process_meta=process_meta,
            )
            next_cursors.append(
                EventCursor(
                    event_group_id=cursor.event_group_id,
                    event_chain_id=child_chain_id,
                    flow_program_ref=process_program_ref,
                    pc_node_id=node_id,
                    flow_stack=cursor.flow_stack + (frame,),
                    payload=payload,
                    tags=dict(output_tags),
                    seq=cursor.seq,
                    origin_topic_ref=cursor.origin_topic_ref,
                    convergence_topic_ref=cursor.convergence_topic_ref,
                    convergence_topic_epoch=cursor.convergence_topic_epoch,
                    meta=child_meta,
                )
            )
    return tuple(next_cursors)


def _resolve_process_guardrails(transformation: Any) -> dict[str, int]:
    defaults = {
        "max_depth": _DEFAULT_ESCALATION_MAX_DEPTH,
        "max_budget_steps": _DEFAULT_ESCALATION_MAX_BUDGET_STEPS,
        "max_factory_calls_per_event_group": _DEFAULT_ESCALATION_MAX_FACTORY_CALLS_PER_EVENT_GROUP,
        "max_fanout_per_resolution": _DEFAULT_ESCALATION_MAX_FANOUT_PER_RESOLUTION,
    }
    operator_config = getattr(transformation, "operator_config", None)
    if not isinstance(operator_config, Mapping):
        return defaults
    process_meta = operator_config.get("process")
    if not isinstance(process_meta, Mapping):
        return defaults
    guardrail = process_meta.get("guardrail")
    if guardrail is None:
        return defaults
    if not isinstance(guardrail, Mapping):
        raise OperatorExecutionError(
            "process_guardrail_invalid_contract:operator_config.process.guardrail must be a mapping.",
        )

    resolved = dict(defaults)
    for field_name in (
        "max_depth",
        "max_budget_steps",
        "max_factory_calls_per_event_group",
        "max_fanout_per_resolution",
    ):
        if field_name not in guardrail:
            continue
        resolved[field_name] = _coerce_non_negative_int(
            guardrail.get(field_name),
            field_name=f"process.guardrail.{field_name}",
            default=resolved[field_name],
            minimum=1,
        )
    return resolved


def _resolve_lineage_from_meta(
    *,
    meta: Mapping[str, Any],
    fallback_program_ref: FlowProgramRef,
) -> tuple[str, ...]:
    raw_lineage = meta.get(_FLOW_PROGRAM_LINEAGE_META_KEY)
    lineage: list[str] = []
    if isinstance(raw_lineage, (list, tuple)):
        for item in raw_lineage:
            if isinstance(item, str) and item.strip():
                lineage.append(item.strip())
                continue
            if isinstance(item, Mapping):
                program_uri = item.get("program_uri")
                program_rev = item.get("program_rev")
                if (
                    isinstance(program_uri, str)
                    and program_uri.strip()
                    and isinstance(program_rev, str)
                    and program_rev.strip()
                ):
                    lineage.append(f"{program_uri.strip()}@{program_rev.strip()}")
    if lineage:
        return tuple(lineage)
    return (_program_ref_token(fallback_program_ref),)


def _program_ref_token(program_ref: FlowProgramRef) -> str:
    return f"{program_ref.program_uri}@{program_ref.program_rev}"


def _coerce_non_negative_int(
    raw_value: Any,
    *,
    field_name: str,
    default: int,
    minimum: int = 0,
) -> int:
    if raw_value is None:
        return int(default)
    try:
        value = int(raw_value)
    except Exception as exc:
        raise OperatorExecutionError(
            f"process_guardrail_invalid_value:{field_name}={raw_value!r}",
        ) from exc
    if value < minimum:
        raise OperatorExecutionError(
            f"process_guardrail_invalid_value:{field_name}={raw_value!r}",
        )
    return value


def _merge_process_meta_into_child_meta(
    *,
    child_meta: dict[str, Any],
    process_meta: Mapping[str, Any] | None,
) -> None:
    if not isinstance(process_meta, Mapping):
        return
    if _FACTORY_OUTCOME_META_KEY in process_meta:
        child_meta[_FACTORY_OUTCOME_META_KEY] = process_meta[_FACTORY_OUTCOME_META_KEY]
    if _FACTORY_RESOLUTION_MS_META_KEY in process_meta:
        child_meta[_FACTORY_RESOLUTION_MS_META_KEY] = process_meta[_FACTORY_RESOLUTION_MS_META_KEY]
    fallback_reason = process_meta.get("factory_fallback_reason")
    if fallback_reason is not None:
        child_meta["factory_fallback_reason"] = fallback_reason


def _default_child_chain_id(cursor: EventCursor, transformation: Any, spawn_index: int) -> str:
    trans_id = getattr(transformation, "trans_id", None)
    if not isinstance(trans_id, str) or not trans_id.strip():
        trans_id = "unknown"
    return f"{cursor.event_chain_id}:process:{trans_id}:{spawn_index}"


def _has_process_resume_frame(flow_stack: tuple[FlowStackFrame, ...]) -> bool:
    return _resolve_process_resume_frame(flow_stack) is not None


def _resolve_process_resume_frame(
    flow_stack: tuple[FlowStackFrame, ...],
) -> tuple[FlowStackFrame, tuple[FlowStackFrame, ...]] | None:
    for index in range(len(flow_stack) - 1, -1, -1):
        frame = flow_stack[index]
        if _frame_kind(frame) != FLOW_STACK_FRAME_KIND_PROCESS_RETURN:
            continue
        return frame, flow_stack[:index]
    return None


def _frame_kind(frame: FlowStackFrame) -> str:
    raw_kind = getattr(frame, "frame_kind", FLOW_STACK_FRAME_KIND_PROCESS_RETURN)
    if not isinstance(raw_kind, str):
        return FLOW_STACK_FRAME_KIND_PROCESS_RETURN
    normalized = raw_kind.strip()
    if not normalized:
        return FLOW_STACK_FRAME_KIND_PROCESS_RETURN
    return normalized


def _spawn_resume_cursors(
    *,
    cursor: EventCursor,
    outputs: tuple[tuple[Any, dict[str, str]], ...],
) -> tuple[EventCursor, ...]:
    resume_resolution = _resolve_process_resume_frame(cursor.flow_stack)
    if resume_resolution is None:
        return ()
    frame, remaining_stack = resume_resolution
    resume_node_ids = tuple(frame.resume_pc_node_ids)
    if not resume_node_ids:
        return ()

    frame_meta = frame.frame_meta if isinstance(frame.frame_meta, Mapping) else {}
    aggregate_payloads = bool(frame_meta.get(_AGGREGATE_RESUME_PAYLOADS_FRAME_META_KEY))
    mark_loop_body_result = bool(frame_meta.get(_LOOP_BODY_SUBFLOW_FRAME_META_KEY))

    def _build_resumed_meta() -> dict[str, Any]:
        resumed_meta = dict(cursor.meta)
        resumed_meta.setdefault("resumed_from_process_callsite", frame.callsite_pc_node_id)
        if mark_loop_body_result:
            resumed_meta[_LOOP_BODY_SUBFLOW_RESULT_META_KEY] = "1"
        return resumed_meta

    if aggregate_payloads:
        aggregated_payload = {
            "mode": "loop_body_directive_batch",
            "directives": [payload for payload, _output_tags in outputs],
        }
        if outputs:
            aggregated_tags = dict(outputs[0][1])
        else:
            aggregated_tags = dict(cursor.tags)

        next_cursors: list[EventCursor] = []
        for node_id in resume_node_ids:
            next_cursors.append(
                EventCursor(
                    event_group_id=cursor.event_group_id,
                    event_chain_id=frame.caller_event_chain_id,
                    flow_program_ref=frame.resume_flow_program_ref,
                    pc_node_id=node_id,
                    flow_stack=remaining_stack,
                    payload=aggregated_payload,
                    tags=dict(aggregated_tags),
                    seq=cursor.seq,
                    origin_topic_ref=cursor.origin_topic_ref,
                    convergence_topic_ref=cursor.convergence_topic_ref,
                    convergence_topic_epoch=cursor.convergence_topic_epoch,
                    meta=_build_resumed_meta(),
                )
            )
        return tuple(next_cursors)

    next_cursors: list[EventCursor] = []
    for payload, output_tags in outputs:
        for node_id in resume_node_ids:
            next_cursors.append(
                EventCursor(
                    event_group_id=cursor.event_group_id,
                    event_chain_id=frame.caller_event_chain_id,
                    flow_program_ref=frame.resume_flow_program_ref,
                    pc_node_id=node_id,
                    flow_stack=remaining_stack,
                    payload=payload,
                    tags=dict(output_tags),
                    seq=cursor.seq,
                    origin_topic_ref=cursor.origin_topic_ref,
                    convergence_topic_ref=cursor.convergence_topic_ref,
                    convergence_topic_epoch=cursor.convergence_topic_epoch,
                    meta=_build_resumed_meta(),
                )
            )
    return tuple(next_cursors)


__all__ = [
    "CursorStepResult",
    "execute_cursor_step",
    "materialize_exception_fallback_step",
    "materialize_exception_drop_step",
]
