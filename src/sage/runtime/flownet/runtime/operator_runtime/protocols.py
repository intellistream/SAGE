from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LoopSpec:
    body: Any
    condition: Any
    max_iterations: int
    key_by: int | str | None


@dataclass(frozen=True)
class LoopDirective:
    continue_events: tuple[Any, ...]
    emit_events: tuple[Any, ...]
    state_events: tuple[Any, ...]
    done: bool
    close_reason: str | None


@dataclass(frozen=True)
class StatefulSpec:
    stage_id: str
    namespace: str
    ttl_seconds: float | None
    state_spec: Mapping[str, Any] | None


@dataclass(frozen=True)
class ShuffleSpec:
    stage_id: str
    num_partitions: int
    key_fn: Any | None
    key_field: str | None
    key_index: int


@dataclass(frozen=True)
class JoinSpec:
    stage_id: str
    num_partitions: int
    side: str


@dataclass(frozen=True)
class ReducerSpec:
    stage_id: str
    mode: str
    num_partitions: int
    groupby: Mapping[str, Any]


@dataclass(frozen=True)
class JoinReducerSpec:
    stage_id: str
    num_partitions: int


@dataclass(frozen=True)
class MergeReducerSpec:
    stage_id: str
    mode: str
    expected_partition_ids: tuple[int, ...]


@dataclass(frozen=True)
class CollectiveSpec:
    kind: str
    stage_id: str
    group: str
    world_size: int
    rank_field: str
    tensor_field: str
    round_fields: tuple[str, ...]
    timeout_ms: int
    backend: str
    strict: bool
    reduce_op: str | None = None
    route_field: str | None = None
    path_tag: str | None = None


@dataclass(frozen=True)
class ReducerFrame:
    control: str
    partition_id: int
    value: Any


@dataclass(frozen=True)
class JoinReducerFrame:
    control: str
    side: str
    partition_id: int
    value: Any


@dataclass(frozen=True)
class MergeReducerFrame:
    control: str
    partition_id: int
    value: Any


__all__ = [
    "LoopSpec",
    "LoopDirective",
    "StatefulSpec",
    "ShuffleSpec",
    "JoinSpec",
    "ReducerSpec",
    "JoinReducerSpec",
    "MergeReducerSpec",
    "CollectiveSpec",
    "ReducerFrame",
    "JoinReducerFrame",
    "MergeReducerFrame",
]
