from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_models import FlowProgramRef

from .errors import LoopOperatorContractError


@dataclass(frozen=True)
class OperatorEvaluation:
    outputs: tuple[Any, ...]
    output_tags: tuple[dict[str, str], ...] | None = None
    route_node_ids: tuple[str, ...] | None = None
    process_program_ref: FlowProgramRef | None = None
    process_meta: dict[str, Any] | None = None


@dataclass(frozen=True)
class LoopStepEvaluation:
    session_id: str
    iteration: int
    next_iteration: int
    inner_outputs: tuple[Any, ...]
    outer_outputs: tuple[Any, ...]
    closed: bool
    close_reason: str | None


@dataclass(frozen=True)
class LoopGateEvaluation:
    session_id: str
    iteration: int
    should_continue: bool
    close_reason: str | None


@dataclass
class _StateEntry:
    value: Any
    updated_at: float


@dataclass
class _ReducerState:
    stage_id: str
    mode: str
    num_partitions: int
    groupby: Mapping[str, Any]
    acc: Any
    done_partitions: set[int] = field(default_factory=set)


@dataclass
class _JoinReducerState:
    stage_id: str
    num_partitions: int
    left: dict[int, list[Any]] = field(default_factory=dict)
    right: dict[int, list[Any]] = field(default_factory=dict)
    done_left: set[int] = field(default_factory=set)
    done_right: set[int] = field(default_factory=set)


@dataclass
class _MergeReducerState:
    stage_id: str
    mode: str
    expected_partition_ids: tuple[int, ...]
    acc: Any
    partial_partitions: set[int] = field(default_factory=set)
    done_partitions: set[int] = field(default_factory=set)


@dataclass
class _CollectiveFrame:
    rank: int
    payload: Any
    tensor: Any
    route_targets: tuple[int, ...]


@dataclass
class _CollectiveRoundState:
    kind: str
    stage_id: str
    group: str
    round_key: str
    world_size: int
    start_time: float
    frames: dict[int, _CollectiveFrame] = field(default_factory=dict)


@dataclass
class _LoopStepRuntimeCtx:
    iteration_index: int
    session_id_value: str
    _inner_events: list[Any] = field(default_factory=list)
    _outer_events: list[Any] = field(default_factory=list)
    closed: bool = False
    close_reason: str | None = None

    def emit_inner(self, event: Any) -> None:
        if self.closed:
            raise LoopOperatorContractError("loop_ctx_closed:emit_inner_not_allowed")
        self._inner_events.append(event)

    def emit_outer(self, event: Any) -> None:
        self._outer_events.append(event)

    def close(self, reason: str = "done") -> None:
        normalized_reason = str(reason or "done").strip() or "done"
        self.closed = True
        self.close_reason = normalized_reason

    def iteration(self) -> int:
        return self.iteration_index

    def session_id(self) -> str:
        return self.session_id_value


@dataclass
class _FlatMapContinuationState:
    mode: str
    iterator: Iterator[Any] | AsyncIterator[Any]


__all__ = [
    "OperatorEvaluation",
    "LoopStepEvaluation",
    "LoopGateEvaluation",
    "_StateEntry",
    "_ReducerState",
    "_JoinReducerState",
    "_MergeReducerState",
    "_CollectiveFrame",
    "_CollectiveRoundState",
    "_LoopStepRuntimeCtx",
    "_FlatMapContinuationState",
]
