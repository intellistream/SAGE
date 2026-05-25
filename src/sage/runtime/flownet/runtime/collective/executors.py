from __future__ import annotations

from typing import Any

from .contracts import CollectiveExecutionRequest, CollectiveExecutionResponse
from .registry import CollectiveExecutorRegistry


class LocalTopicFallbackCollectiveExecutor:
    """Minimal default executor for topic-fallback collectives."""

    backend_mode = "topic_fallback"
    backend_impl = "local_topic_fallback"
    supported_kinds = ("all_gather", "all_reduce")

    def describe(self) -> dict[str, Any]:
        return {
            "backend_mode": self.backend_mode,
            "backend_impl": self.backend_impl,
            "backend_type": "topic_fallback",
            "supported_kinds": self.supported_kinds,
            "supports_path_tags": False,
        }

    def execute(self, request: CollectiveExecutionRequest) -> CollectiveExecutionResponse:
        if len(request.tensor_by_rank) != int(request.world_size):
            raise RuntimeError(
                "collective_executor_world_size_mismatch:"
                f"expected={request.world_size},observed={len(request.tensor_by_rank)}"
            )

        sorted_ranks = tuple(sorted(int(rank) for rank in request.tensor_by_rank.keys()))
        if request.kind == "all_gather":
            gathered = tuple(request.tensor_by_rank[rank] for rank in sorted_ranks)
            return CollectiveExecutionResponse(
                output_tensor_by_rank={rank: gathered for rank in sorted_ranks},
                backend_impl=self.backend_impl,
                backend_type="topic_fallback",
                runtime_dispatch=True,
                metadata={
                    "supported_kind": request.kind,
                    "world_size": int(request.world_size),
                },
            )

        if request.kind == "all_reduce":
            reduce_op = str(request.reduce_op or "sum").strip().lower() or "sum"
            reduced = _reduce_collective_values(
                values=tuple(request.tensor_by_rank[rank] for rank in sorted_ranks),
                reduce_op=reduce_op,
            )
            return CollectiveExecutionResponse(
                output_tensor_by_rank={rank: reduced for rank in sorted_ranks},
                backend_impl=self.backend_impl,
                backend_type="topic_fallback",
                runtime_dispatch=True,
                metadata={
                    "supported_kind": request.kind,
                    "reduce_op": reduce_op,
                    "world_size": int(request.world_size),
                },
            )

        raise RuntimeError(
            "collective_executor_kind_not_supported:"
            f"kind={request.kind},backend={self.backend_mode},"
            f"supported={','.join(self.supported_kinds)}"
        )


def ensure_default_collective_executors(
    registry: CollectiveExecutorRegistry,
) -> CollectiveExecutorRegistry:
    if not isinstance(registry, CollectiveExecutorRegistry):
        raise TypeError("registry must be a CollectiveExecutorRegistry.")
    if registry.resolve_executor(mode="topic_fallback") is None:
        registry.register_executor(
            mode="topic_fallback",
            executor=LocalTopicFallbackCollectiveExecutor(),
        )
    return registry


def _reduce_collective_values(*, values: tuple[Any, ...], reduce_op: str) -> Any:
    if not values:
        raise RuntimeError("collective reduce values must not be empty.")
    if reduce_op == "sum":
        acc = values[0]
        for value in values[1:]:
            acc = acc + value
        return acc
    if reduce_op == "max":
        return max(values)
    if reduce_op == "min":
        return min(values)
    if reduce_op == "mean":
        acc = values[0]
        for value in values[1:]:
            acc = acc + value
        return acc / len(values)
    raise RuntimeError(
        f"collective_reduce_op_not_supported:reduce_op={reduce_op},supported=sum,max,min,mean"
    )


__all__ = [
    "LocalTopicFallbackCollectiveExecutor",
    "ensure_default_collective_executors",
]
