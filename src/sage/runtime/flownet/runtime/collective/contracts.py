from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class CollectiveExecutionRequest:
    kind: str
    stage_id: str
    group: str
    round_key: str
    world_size: int
    backend_mode: str
    strict: bool
    tensor_field: str
    rank_field: str
    route_field: str | None
    reduce_op: str | None
    path_tag: str | None = None
    tensor_by_rank: Mapping[int, Any] = field(default_factory=dict)
    route_targets_by_rank: Mapping[int, tuple[int, ...]] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CollectiveExecutionResponse:
    output_tensor_by_rank: Mapping[int, Any] | None = None
    outputs: tuple[Any, ...] | None = None
    output_tags: tuple[Mapping[str, str], ...] | None = None
    backend_impl: str = "local"
    backend_type: str = "local"
    runtime_dispatch: bool = False
    fallback_used: bool = False
    fallback_reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


class CollectiveExecutor(Protocol):
    def execute(self, request: CollectiveExecutionRequest) -> CollectiveExecutionResponse: ...


__all__ = [
    "CollectiveExecutionRequest",
    "CollectiveExecutionResponse",
    "CollectiveExecutor",
]
