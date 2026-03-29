from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_models import EventCursor, FlowProgramRef
from sage.runtime.flownet.runtime.flowengine.operator_executor import (
    CursorStepResult,
    execute_cursor_step,
)
from sage.runtime.flownet.runtime.flowengine.operator_runtime import (
    CollectiveRuntime,
    FlatMapContinuationRuntime,
    JoinReducerRuntime,
    MergeReducerRuntime,
    ReducerRuntime,
    StatefulProcessRuntime,
)


@dataclass(frozen=True)
class FlowExecutionOutput:
    payload: Any
    tags: dict[str, str] | None = None
    seq: int | None = None


@dataclass(frozen=True)
class FlowExecutionReport:
    status: str
    outputs: tuple[FlowExecutionOutput, ...]
    event_chain_delta: int
    error_type: str | None = None
    message: str | None = None


class FlowEngineV1:
    """Phase-1 inline flow executor for per-event handler invocation."""

    def __init__(
        self,
        *,
        state_runtime: StatefulProcessRuntime | None = None,
        reducer_runtime: ReducerRuntime | None = None,
        join_reducer_runtime: JoinReducerRuntime | None = None,
        merge_reducer_runtime: MergeReducerRuntime | None = None,
        collective_runtime: CollectiveRuntime | None = None,
        run_coroutine: Callable[[Awaitable[Any]], Any] | None = None,
        flatmap_runtime: FlatMapContinuationRuntime | None = None,
    ) -> None:
        self._state_runtime = state_runtime or StatefulProcessRuntime()
        self._reducer_runtime = reducer_runtime or ReducerRuntime()
        self._join_reducer_runtime = join_reducer_runtime or JoinReducerRuntime()
        self._merge_reducer_runtime = merge_reducer_runtime or MergeReducerRuntime()
        self._collective_runtime = collective_runtime or CollectiveRuntime()
        self._flatmap_runtime = flatmap_runtime or FlatMapContinuationRuntime(
            run_coroutine=run_coroutine,
        )

    def execute_event(
        self,
        *,
        handler: Callable[[dict[str, Any]], Any],
        invocation: dict[str, Any],
    ) -> FlowExecutionReport:
        try:
            raw_result = handler(invocation)
        except Exception as exc:
            return FlowExecutionReport(
                status="handler_error",
                outputs=(),
                event_chain_delta=0,
                error_type=exc.__class__.__name__,
                message=str(exc),
            )

        outputs, event_chain_delta = _normalize_flow_result(raw_result)
        normalized_outputs = tuple(_normalize_output_item(output) for output in outputs)
        return FlowExecutionReport(
            status="executed",
            outputs=normalized_outputs,
            event_chain_delta=event_chain_delta,
        )

    def execute_cursor_step(
        self,
        *,
        cursor: EventCursor,
        flow_program: Any,
        invoke_target: Callable[[Any, Any, dict[str, str], int | None], Any] | None = None,
        resolve_process_entry_nodes: Callable[[FlowProgramRef], tuple[str, ...]] | None = None,
        child_chain_id_factory: Callable[[EventCursor, Any, int], str] | None = None,
    ) -> CursorStepResult:
        return execute_cursor_step(
            cursor=cursor,
            flow_program=flow_program,
            invoke_target=invoke_target,
            state_runtime=self._state_runtime,
            reducer_runtime=self._reducer_runtime,
            join_reducer_runtime=self._join_reducer_runtime,
            merge_reducer_runtime=self._merge_reducer_runtime,
            collective_runtime=self._collective_runtime,
            flatmap_runtime=self._flatmap_runtime,
            resolve_process_entry_nodes=resolve_process_entry_nodes,
            child_chain_id_factory=child_chain_id_factory,
        )

    def close(self) -> None:
        close_state_runtime = getattr(self._state_runtime, "close", None)
        if callable(close_state_runtime):
            close_state_runtime()


def _normalize_flow_result(result: Any) -> tuple[list[Any], int]:
    outputs: list[Any]
    event_chain_delta = 0
    if result is None:
        outputs = []
    elif isinstance(result, dict):
        raw_outputs = result.get("outputs")
        if raw_outputs is None:
            outputs = []
        elif isinstance(raw_outputs, list):
            outputs = list(raw_outputs)
        elif isinstance(raw_outputs, tuple):
            outputs = list(raw_outputs)
        else:
            outputs = [raw_outputs]
        if "event_chain_delta" in result:
            event_chain_delta = int(result.get("event_chain_delta") or 0)
    elif isinstance(result, list):
        outputs = list(result)
    elif isinstance(result, tuple):
        outputs = list(result)
    else:
        outputs = [result]
    return outputs, event_chain_delta


def _normalize_output_item(output: Any) -> FlowExecutionOutput:
    if isinstance(output, dict) and "payload" in output:
        payload = output.get("payload")
        raw_tags = output.get("tags")
        tags: dict[str, str] | None = None
        if isinstance(raw_tags, dict):
            tags = {str(key): str(value) for key, value in raw_tags.items()}
        raw_seq = output.get("seq")
        seq = int(raw_seq) if raw_seq is not None else None
        return FlowExecutionOutput(payload=payload, tags=tags, seq=seq)
    return FlowExecutionOutput(payload=output)


__all__ = [
    "FlowExecutionOutput",
    "FlowExecutionReport",
    "FlowEngineV1",
]
