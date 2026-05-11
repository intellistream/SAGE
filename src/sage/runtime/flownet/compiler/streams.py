from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sage.runtime.flownet.compiler.errors import FlowDefinitionError
from sage.runtime.flownet.compiler.targets import ensure_flow_target, system_target
from sage.runtime.flownet.compiler.transformation import Transformation
from sage.runtime.flownet.contracts.recovery_contract import normalize_recovery_policy

if TYPE_CHECKING:
    from sage.runtime.flownet.core.flow_program import FlowProgram


T = TypeVar("T")


def _normalize_shuffle_key(
    key: Any,
    key_index: int | None,
    key_field: str | None,
) -> tuple[int, str | None]:
    if key is not None:
        if isinstance(key, int):
            key_index = key
        elif isinstance(key, str):
            key_field = key
        else:
            raise FlowDefinitionError("shuffle/join key must be int (index) or str (field).")
    if key_index is None:
        key_index = 0
    return key_index, key_field


def _plan_meta(plan: Any) -> dict[str, Any]:
    return {
        "plan": plan.as_dict(),
        "plan_id": plan.plan_id,
        "stage_id": plan.stage_id,
        "epoch": plan.epoch,
    }


def _normalize_reduce_by_key_mode(mode: str) -> str:
    if mode not in {"sum", "count", "concat"}:
        raise FlowDefinitionError(
            "reduce_by_key mode must be one of: sum, count, concat.",
        )
    return f"{mode}_by_key"


def _coerce_optional_positive_int(raw_value: Any, *, field_name: str) -> int | None:
    if raw_value is None:
        return None
    value = int(raw_value)
    if value <= 0:
        raise FlowDefinitionError(f"{field_name} must be > 0 when provided.")
    return value


def _coerce_loop_body(body: Any) -> Any:
    if callable(body):
        return body
    if _is_target_like(body):
        return _ensure_flow_target(
            body,
            "loop.body",
            allow_flow_program_ref=True,
            require_bound_flow_ref=True,
        )
    raise FlowDefinitionError(
        "loop body must be callable, actor/stateless/symbolic target, or flow-program/symbolic-flow reference.",
    )


def _coerce_loop_condition(condition: Any) -> Any:
    if callable(condition):
        return condition
    if _is_target_like(condition):
        return _ensure_flow_target(condition, "loop.condition", allow_flow_program_ref=False)
    raise FlowDefinitionError(
        "loop condition must be callable or actor/stateless target.",
    )


def _normalize_collective_kind(kind: Any) -> str:
    normalized = str(kind or "").strip().lower()
    if normalized not in {"all_to_all", "all_reduce", "all_gather"}:
        raise FlowDefinitionError(
            "collective kind must be one of: all_to_all, all_reduce, all_gather.",
        )
    return normalized


def _normalize_collective_backend(backend: Any) -> str:
    normalized = str(backend or "").strip().lower() or "auto"
    if normalized not in {"auto", "topic_fallback", "fast_channel"}:
        raise FlowDefinitionError(
            "collective backend must be one of: auto, topic_fallback, fast_channel.",
        )
    return normalized


def _normalize_collective_reduce_op(op: Any) -> str:
    normalized = str(op or "").strip().lower()
    if normalized not in {"sum", "max", "min", "mean"}:
        raise FlowDefinitionError(
            "collective reduce op must be one of: sum, max, min, mean.",
        )
    return normalized


def _normalize_collective_round_fields(round_by: Any) -> tuple[str, ...]:
    if isinstance(round_by, str):
        value = round_by.strip()
        if not value:
            raise FlowDefinitionError("collective round_by field must be a non-empty string.")
        return (value,)
    if not isinstance(round_by, (list, tuple)):
        raise FlowDefinitionError("collective round_by must be a str or tuple/list[str].")
    normalized: list[str] = []
    for raw_field in round_by:
        if not isinstance(raw_field, str) or not raw_field.strip():
            raise FlowDefinitionError("collective round_by entries must be non-empty strings.")
        normalized.append(raw_field.strip())
    if not normalized:
        raise FlowDefinitionError("collective round_by must contain at least one field.")
    return tuple(normalized)


class DataStream(Generic[T]):
    def __init__(
        self, flow_program: FlowProgram, transformation: Transformation | None, init: bool = False
    ):
        self.flow_program = flow_program
        self.transformation = transformation
        self.init = bool(init)

    def map(self, fn_object: Any) -> DataStream:
        transformation = Transformation(
            self.flow_program,
            _ensure_flow_target(fn_object, "map"),
            type="map",
        )
        return self._apply(transformation)

    def process(self, fn_object: Any) -> DataStream:
        transformation = Transformation(
            self.flow_program,
            _ensure_flow_target(
                fn_object,
                "process",
                allow_flow_program_ref=True,
                require_bound_flow_ref=True,
            ),
            type="process",
        )
        return self._apply(transformation)

    def pipe(self, fn_object: Any) -> DataStream:
        del fn_object
        raise FlowDefinitionError(
            "pipe() is removed from v1 surface. Use process(...) instead.",
        )

    def filter(self, fn_object: Any) -> DataStream:
        transformation = Transformation(
            self.flow_program,
            _ensure_flow_target(fn_object, "filter"),
            type="filter",
        )
        return self._apply(transformation)

    def flatmap(self, fn_object: Any) -> DataStream:
        transformation = Transformation(
            self.flow_program,
            _ensure_flow_target(fn_object, "flatmap"),
            type="flatmap",
        )
        return self._apply(transformation)

    def tap(self, fn_object: Any) -> DataStream:
        transformation = Transformation(
            self.flow_program,
            _ensure_flow_target(fn_object, "tap"),
            type="tap",
        )
        return self._apply(transformation)

    def collective(
        self,
        *,
        kind: str,
        group: str,
        world_size: int,
        rank_field: str,
        round_by: str | tuple[str, ...] | list[str],
        tensor_field: str,
        route_field: str | None = None,
        op: str | None = None,
        backend: str = "auto",
        path_tag: str | None = None,
        timeout_ms: int = 2_000,
        strict: bool = True,
        stage_id: str | None = None,
    ) -> DataStream:
        normalized_kind = _normalize_collective_kind(kind)
        normalized_group = str(group or "").strip()
        if not normalized_group:
            raise FlowDefinitionError("collective group must be a non-empty string.")
        normalized_world_size = _coerce_optional_positive_int(
            world_size,
            field_name="collective world_size",
        )
        if normalized_world_size is None:
            raise FlowDefinitionError("collective world_size is required.")
        normalized_rank_field = str(rank_field or "").strip()
        if not normalized_rank_field:
            raise FlowDefinitionError("collective rank_field must be a non-empty string.")
        normalized_round_fields = _normalize_collective_round_fields(round_by)
        normalized_tensor_field = str(tensor_field or "").strip()
        if not normalized_tensor_field:
            raise FlowDefinitionError("collective tensor_field must be a non-empty string.")
        normalized_timeout_ms = _coerce_optional_positive_int(
            timeout_ms,
            field_name="collective timeout_ms",
        )
        if normalized_timeout_ms is None:
            raise FlowDefinitionError("collective timeout_ms is required.")
        normalized_backend = _normalize_collective_backend(backend)
        normalized_path_tag: str | None = None
        if path_tag is not None:
            normalized_path_tag = str(path_tag).strip()
            if not normalized_path_tag:
                raise FlowDefinitionError(
                    "collective path_tag must be a non-empty string when provided."
                )
        normalized_stage_id = None
        if stage_id is not None:
            normalized_stage_id = str(stage_id).strip()
            if not normalized_stage_id:
                raise FlowDefinitionError(
                    "collective stage_id must be a non-empty string when provided."
                )
        normalized_route_field: str | None = None
        if route_field is not None:
            normalized_route_field = str(route_field).strip()
            if not normalized_route_field:
                raise FlowDefinitionError(
                    "collective route_field must be a non-empty string when provided."
                )

        collective_meta: dict[str, Any] = {
            "kind": normalized_kind,
            "group": normalized_group,
            "world_size": normalized_world_size,
            "rank_field": normalized_rank_field,
            "round_fields": list(normalized_round_fields),
            "tensor_field": normalized_tensor_field,
            "backend": normalized_backend,
            "timeout_ms": normalized_timeout_ms,
            "strict": bool(strict),
        }
        if normalized_path_tag is not None:
            collective_meta["path_tag"] = normalized_path_tag
        if normalized_stage_id is not None:
            collective_meta["stage_id"] = normalized_stage_id
        if normalized_kind == "all_reduce":
            collective_meta["reduce_op"] = _normalize_collective_reduce_op(op or "sum")
        elif op is not None:
            raise FlowDefinitionError("collective op is only supported for all_reduce.")
        if normalized_kind == "all_to_all":
            if normalized_route_field is None:
                raise FlowDefinitionError("all_to_all requires route_field.")
            collective_meta["route_field"] = normalized_route_field
        elif normalized_route_field is not None:
            raise FlowDefinitionError("collective route_field is only supported for all_to_all.")

        transformation = Transformation(
            self.flow_program,
            system_target(),
            type="sys/collective",
            operator_config={"collective": collective_meta},
        )
        result = self._apply(transformation)
        if "stage_id" not in collective_meta:
            collective_meta["stage_id"] = transformation.trans_id
        return result

    def all_to_all(
        self,
        *,
        group: str,
        world_size: int,
        rank_field: str,
        round_by: str | tuple[str, ...] | list[str],
        tensor_field: str,
        route_field: str,
        backend: str = "auto",
        path_tag: str | None = None,
        timeout_ms: int = 2_000,
        strict: bool = True,
        stage_id: str | None = None,
    ) -> DataStream:
        return self.collective(
            kind="all_to_all",
            group=group,
            world_size=world_size,
            rank_field=rank_field,
            round_by=round_by,
            tensor_field=tensor_field,
            route_field=route_field,
            backend=backend,
            path_tag=path_tag,
            timeout_ms=timeout_ms,
            strict=strict,
            stage_id=stage_id,
        )

    def all_reduce(
        self,
        *,
        group: str,
        world_size: int,
        rank_field: str,
        round_by: str | tuple[str, ...] | list[str],
        tensor_field: str,
        op: str = "sum",
        backend: str = "auto",
        path_tag: str | None = None,
        timeout_ms: int = 2_000,
        strict: bool = True,
        stage_id: str | None = None,
    ) -> DataStream:
        return self.collective(
            kind="all_reduce",
            group=group,
            world_size=world_size,
            rank_field=rank_field,
            round_by=round_by,
            tensor_field=tensor_field,
            op=op,
            backend=backend,
            path_tag=path_tag,
            timeout_ms=timeout_ms,
            strict=strict,
            stage_id=stage_id,
        )

    def all_gather(
        self,
        *,
        group: str,
        world_size: int,
        rank_field: str,
        round_by: str | tuple[str, ...] | list[str],
        tensor_field: str,
        backend: str = "auto",
        path_tag: str | None = None,
        timeout_ms: int = 2_000,
        strict: bool = True,
        stage_id: str | None = None,
    ) -> DataStream:
        return self.collective(
            kind="all_gather",
            group=group,
            world_size=world_size,
            rank_field=rank_field,
            round_by=round_by,
            tensor_field=tensor_field,
            backend=backend,
            path_tag=path_tag,
            timeout_ms=timeout_ms,
            strict=strict,
            stage_id=stage_id,
        )

    def loop(
        self,
        *,
        body: Any,
        condition: Any,
        max_iterations: int,
        key_by: int | str | None = None,
        max_open_ms: int | None = None,
        max_idle_ms: int | None = None,
        scheduler: dict[str, Any] | None = None,
    ) -> DataStream:
        if key_by is not None and not isinstance(key_by, (int, str)):
            raise FlowDefinitionError("loop key_by must be int (index) or str (field).")
        normalized_max_iterations = _coerce_optional_positive_int(
            max_iterations,
            field_name="loop max_iterations",
        )
        if normalized_max_iterations is None:
            raise FlowDefinitionError("loop max_iterations is required.")
        loop_meta: dict[str, Any] = {
            "body": _coerce_loop_body(body),
            "condition": _coerce_loop_condition(condition),
            "max_iterations": normalized_max_iterations,
        }
        if key_by is not None:
            loop_meta["key_by"] = key_by
        normalized_max_open_ms = _coerce_optional_positive_int(
            max_open_ms,
            field_name="loop max_open_ms",
        )
        if normalized_max_open_ms is not None:
            loop_meta["max_open_ms"] = normalized_max_open_ms
        normalized_max_idle_ms = _coerce_optional_positive_int(
            max_idle_ms,
            field_name="loop max_idle_ms",
        )
        if normalized_max_idle_ms is not None:
            loop_meta["max_idle_ms"] = normalized_max_idle_ms
        if scheduler is not None:
            if not isinstance(scheduler, dict):
                raise FlowDefinitionError("loop scheduler must be a dict when provided.")
            loop_meta["scheduler"] = dict(scheduler)

        transformation = Transformation(
            self.flow_program,
            system_target(),
            type="sys/loop",
            operator_config={"loop": loop_meta},
        )
        return self._apply(transformation)

    def shuffle(
        self,
        *,
        key: int | str | None = None,
        key_index: int | None = None,
        key_field: str | None = None,
        key_fn: Any = None,
        num_partitions: int = 1,
        plan: Any | None = None,
        addresses: list[str] | None = None,
        stage_id: str | None = None,
    ) -> PartitionedStream:
        if plan is not None and stage_id is not None and plan.stage_id != stage_id:
            raise FlowDefinitionError(
                "shuffle stage_id must match plan.stage_id when plan is provided."
            )
        if plan is None and not addresses:
            raise FlowDefinitionError("shuffle() requires addresses when plan is not provided.")
        if key_fn is not None and (
            key is not None or key_index is not None or key_field is not None
        ):
            raise FlowDefinitionError(
                "shuffle() cannot combine key_fn with key/key_index/key_field.",
            )

        shuffle_meta: dict[str, Any] = {
            "num_partitions": num_partitions,
        }
        if key_fn is None:
            key_index, key_field = _normalize_shuffle_key(key, key_index, key_field)
            shuffle_meta["key_index"] = key_index
            if key_field is not None:
                shuffle_meta["key_field"] = key_field
        else:
            shuffle_meta["key_fn"] = _ensure_flow_target(key_fn, "shuffle")
        if addresses:
            shuffle_meta["addresses"] = list(addresses)
        if stage_id is not None:
            shuffle_meta["stage_id"] = stage_id
        elif plan is not None:
            shuffle_meta["stage_id"] = plan.stage_id

        operator_config: dict[str, Any] = {
            "shuffle": shuffle_meta,
        }
        if plan is not None:
            operator_config["sys"] = _plan_meta(plan)

        transformation = Transformation(
            self.flow_program,
            system_target(),
            type="sys/shuffle",
            operator_config=operator_config,
        )
        self._apply(transformation)
        if shuffle_meta.get("stage_id") is None:
            shuffle_meta["stage_id"] = transformation.trans_id
        return PartitionedStream(self.flow_program, transformation, shuffle_meta, plan)

    def repartition(
        self,
        num_partitions: int,
        *,
        key: int | str | None = None,
        key_index: int | None = None,
        key_field: str | None = None,
        plan: Any | None = None,
        addresses: list[str] | None = None,
        stage_id: str | None = None,
    ) -> PartitionedStream:
        return self.shuffle(
            key=key,
            key_index=key_index,
            key_field=key_field,
            num_partitions=num_partitions,
            plan=plan,
            addresses=addresses,
            stage_id=stage_id,
        )

    def key_by(
        self,
        *,
        key: int | str | None = None,
        key_index: int | None = None,
        key_field: str | None = None,
        key_fn: Any = None,
        num_partitions: int = 1,
        plan: Any | None = None,
        addresses: list[str] | None = None,
        stage_id: str | None = None,
    ) -> PartitionedStream:
        if key_fn is not None and (
            key is not None or key_index is not None or key_field is not None
        ):
            raise FlowDefinitionError(
                "key_by() cannot combine key_fn with key/key_index/key_field.",
            )
        return self.shuffle(
            key=key,
            key_index=key_index,
            key_field=key_field,
            key_fn=key_fn,
            num_partitions=num_partitions,
            plan=plan,
            addresses=addresses,
            stage_id=stage_id,
        )

    def join(
        self,
        other: DataStream | ConnectedStreams,
        *,
        key: int | str | None = None,
        key_index: int | None = None,
        key_field: str | None = None,
        num_partitions: int = 1,
        plan: Any | None = None,
        addresses: list[str] | None = None,
        stage_id: str | None = None,
    ) -> DataStream:
        return self.connect(other).join(
            key=key,
            key_index=key_index,
            key_field=key_field,
            num_partitions=num_partitions,
            plan=plan,
            addresses=addresses,
            stage_id=stage_id,
        )

    def groupby(
        self,
        *,
        key: int | str | None = None,
        key_index: int | None = None,
        key_field: str | None = None,
        num_partitions: int = 1,
        plan: Any | None = None,
        addresses: list[str] | None = None,
        stage_id: str | None = None,
    ) -> GroupedStream:
        key_index, key_field = _normalize_shuffle_key(key, key_index, key_field)
        partitioned = self.repartition(
            num_partitions=num_partitions,
            key_index=key_index,
            key_field=key_field,
            plan=plan,
            addresses=addresses,
            stage_id=stage_id,
        )
        return GroupedStream(
            partitioned,
            {
                "key_index": key_index,
                "key_field": key_field,
            },
        )

    def connect(self, other: DataStream | ConnectedStreams) -> ConnectedStreams:
        if isinstance(other, DataStream):
            return ConnectedStreams(self.flow_program, [self.transformation, other.transformation])
        new_transformations = [self.transformation] + other.transformations
        return ConnectedStreams(self.flow_program, new_transformations)

    def _apply(self, transformation: Transformation) -> DataStream:
        transformation.exception_handler_stack = list(self.flow_program._exception_handler_stack)
        if self.transformation is None:
            self.flow_program.set_entry_id(transformation.trans_id)
        else:
            transformation.add_upstream(self.transformation)

        self.flow_program.pipeline.append(transformation)
        self.flow_program.transformations[transformation.trans_id] = transformation
        return DataStream(self.flow_program, transformation)

    def set_return(self) -> None:
        if self.transformation is None:
            return
        self.flow_program.mark_return(self.transformation)

    def set_sink(self) -> None:
        self.set_return()

    def write(self, sink: Any) -> SinkStream:
        target = sink
        if not _is_target_like(sink) and hasattr(sink, "write"):
            target = sink.write
        transformation = Transformation(
            self.flow_program,
            _ensure_flow_target(target, "write"),
            type="sink",
        )
        result = self._apply(transformation)
        self.flow_program.mark_sink(result.transformation)
        return SinkStream(self.flow_program, result.transformation)

    def publish(self, sink: Any) -> SinkStream:
        return self.write(sink)


class SinkStream(DataStream):
    def _raise(self, op: str):
        raise FlowDefinitionError(f"Cannot call {op} on a SinkStream.")

    def map(self, fn_object):  # type: ignore[override]
        return self._raise("map()")

    def process(self, fn_object):  # type: ignore[override]
        return self._raise("process()")

    def pipe(self, fn_object):  # type: ignore[override]
        return self._raise("pipe()")

    def filter(self, fn_object):  # type: ignore[override]
        return self._raise("filter()")

    def flatmap(self, fn_object):  # type: ignore[override]
        return self._raise("flatmap()")

    def tap(self, fn_object):  # type: ignore[override]
        return self._raise("tap()")

    def collective(self, **kwargs):  # type: ignore[override]
        del kwargs
        return self._raise("collective()")

    def all_to_all(self, **kwargs):  # type: ignore[override]
        del kwargs
        return self._raise("all_to_all()")

    def all_reduce(self, **kwargs):  # type: ignore[override]
        del kwargs
        return self._raise("all_reduce()")

    def all_gather(self, **kwargs):  # type: ignore[override]
        del kwargs
        return self._raise("all_gather()")

    def loop(self, **kwargs):  # type: ignore[override]
        del kwargs
        return self._raise("loop()")

    def connect(self, other):  # type: ignore[override]
        return self._raise("connect()")

    def write(self, sink):  # type: ignore[override]
        return self._raise("write()")

    def publish(self, sink):  # type: ignore[override]
        return self._raise("publish()")

    def set_return(self):  # type: ignore[override]
        return self._raise("set_return()")


def _ensure_flow_target(
    target: Any,
    op: str,
    *,
    allow_flow_program_ref: bool = False,
    require_bound_flow_ref: bool = False,
) -> Any:
    return ensure_flow_target(
        target,
        op,
        allow_flow_program_ref=allow_flow_program_ref,
        require_bound_flow_ref=require_bound_flow_ref,
    )


def _is_target_like(target: Any) -> bool:
    try:
        _ensure_flow_target(target, "noop", allow_flow_program_ref=True)
        return True
    except Exception:
        return False


class ConnectedStreams(DataStream):
    def __init__(self, flow_program: FlowProgram, transformations: list[Transformation | None]):
        self.flow_program = flow_program
        self.transformations = [trans for trans in transformations if trans is not None]

        if len(self.transformations) < 2:
            raise FlowDefinitionError("ConnectedStreams requires at least 2 transformations.")
        for trans in self.transformations:
            if trans.flow_program is not flow_program:
                raise FlowDefinitionError(
                    "All transformations must belong to the same flow_program."
                )

    def connect(self, other: DataStream | ConnectedStreams) -> ConnectedStreams:
        if isinstance(other, DataStream):
            new_transformations = self.transformations + [other.transformation]
            return ConnectedStreams(self.flow_program, new_transformations)
        new_transformations = self.transformations + other.transformations
        return ConnectedStreams(self.flow_program, new_transformations)

    def apply(self, transformation: Transformation) -> DataStream:
        transformation.exception_handler_stack = list(self.flow_program._exception_handler_stack)
        for upstream_trans in self.transformations:
            transformation.add_upstream(upstream_trans)
        self.flow_program.pipeline.append(transformation)
        self.flow_program.transformations[transformation.trans_id] = transformation
        return DataStream(self.flow_program, transformation)

    def set_return(self) -> None:
        for transformation in self.transformations:
            self.flow_program.mark_return(transformation)

    def set_sink(self) -> None:
        self.set_return()

    def write(self, sink: Any) -> SinkStream:
        target = sink
        if not _is_target_like(sink) and hasattr(sink, "write"):
            target = sink.write
        transformation = Transformation(
            self.flow_program,
            _ensure_flow_target(target, "write"),
            type="sink",
        )
        result = self.apply(transformation)
        self.flow_program.mark_sink(result.transformation)
        return SinkStream(self.flow_program, result.transformation)

    def publish(self, sink: Any) -> SinkStream:
        return self.write(sink)

    def join(
        self,
        *,
        key: int | str | None = None,
        key_index: int | None = None,
        key_field: str | None = None,
        num_partitions: int = 1,
        plan: Any | None = None,
        addresses: list[str] | None = None,
        stage_id: str | None = None,
    ) -> DataStream:
        if len(self.transformations) != 2:
            raise FlowDefinitionError("join() requires exactly two streams.")
        if plan is not None and stage_id is not None and plan.stage_id != stage_id:
            raise FlowDefinitionError(
                "join stage_id must match plan.stage_id when plan is provided."
            )
        if plan is None and not addresses:
            raise FlowDefinitionError("join() requires addresses when plan is not provided.")

        key_index, key_field = _normalize_shuffle_key(key, key_index, key_field)
        if stage_id is None:
            stage_id = plan.stage_id if plan is not None else None

        shuffle_meta: dict[str, object] = {
            "num_partitions": num_partitions,
            "key_index": key_index,
        }
        if key_field is not None:
            shuffle_meta["key_field"] = key_field
        if addresses:
            shuffle_meta["addresses"] = list(addresses)
        if stage_id is not None:
            shuffle_meta["stage_id"] = stage_id

        join_meta = {
            "stage_id": stage_id,
            "num_partitions": num_partitions,
        }

        base_config: dict[str, object] = {
            "shuffle": shuffle_meta,
            "join": join_meta,
        }
        if plan is not None:
            base_config["sys"] = _plan_meta(plan)

        left_config = dict(base_config)
        left_config["side"] = "left"
        right_config = dict(base_config)
        right_config["side"] = "right"

        left_router = Transformation(
            self.flow_program,
            system_target(),
            type="sys/join",
            operator_config=left_config,
        )
        right_router = Transformation(
            self.flow_program,
            system_target(),
            type="sys/join",
            operator_config=right_config,
        )
        join_reducer = Transformation(
            self.flow_program,
            system_target(),
            type="sys/join-reducer",
        )

        left_router.add_upstream(self.transformations[0])
        right_router.add_upstream(self.transformations[1])
        join_reducer.add_upstream(left_router)
        join_reducer.add_upstream(right_router)

        for trans in (left_router, right_router, join_reducer):
            trans.exception_handler_stack = list(self.flow_program._exception_handler_stack)
            self.flow_program.pipeline.append(trans)
            self.flow_program.transformations[trans.trans_id] = trans

        return DataStream(self.flow_program, join_reducer)


class PartitionedStream(DataStream):
    def __init__(
        self,
        flow_program: FlowProgram,
        transformation: Transformation,
        shuffle_config: dict[str, Any],
        plan: Any | None,
    ):
        super().__init__(flow_program, transformation)
        self._shuffle_config = shuffle_config
        self._plan = plan

    def reduce(
        self,
        *,
        mode: str = "sum",
        plan: Any | None = None,
        stage_id: str | None = None,
        num_partitions: int | None = None,
        reducer_config: dict[str, Any] | None = None,
    ) -> DataStream:
        effective_plan = plan or self._plan
        if (
            effective_plan is not None
            and stage_id is not None
            and effective_plan.stage_id != stage_id
        ):
            raise FlowDefinitionError(
                "reduce stage_id must match plan.stage_id when plan is provided."
            )

        if stage_id is None:
            stage_id = (
                effective_plan.stage_id
                if effective_plan is not None
                else self._shuffle_config.get("stage_id")
            )
        if num_partitions is None:
            if effective_plan is not None:
                num_partitions = effective_plan.num_partitions
            else:
                num_partitions = int(self._shuffle_config.get("num_partitions", 1))

        reducer_meta: dict[str, Any] = {
            "stage_id": stage_id,
            "num_partitions": num_partitions,
            "mode": mode,
        }
        if reducer_config:
            reducer_meta.update(dict(reducer_config))

        reducer_trans = Transformation(
            self.flow_program,
            system_target(),
            type="sys/reducer",
        )
        reducer_stream = self._apply(reducer_trans)

        merge_trans: Transformation | None = None
        if effective_plan is not None and (
            effective_plan.merge_address is not None or effective_plan.merge_partitions is not None
        ):
            merge_trans = Transformation(
                self.flow_program,
                system_target(),
                type="sys/merge-reducer",
            )
            reducer_meta["merge_transformation"] = merge_trans
            reducer_stream = reducer_stream._apply(merge_trans)

        self._shuffle_config["num_partitions"] = num_partitions
        if stage_id is not None:
            self._shuffle_config["stage_id"] = stage_id

        operator_config = self.transformation.operator_config or {}
        operator_config = dict(operator_config)
        operator_config["shuffle"] = self._shuffle_config
        operator_config["reducer"] = reducer_meta
        if effective_plan is not None:
            operator_config["sys"] = _plan_meta(effective_plan)
        self.transformation.operator_config = operator_config

        return reducer_stream

    def process_with_state(
        self,
        handler_ref: Any,
        *,
        state_spec: dict[str, Any] | None = None,
        state_ttl_s: float | None = None,
        stage_id: str | None = None,
        recovery_policy: str = "best_effort",
    ) -> DataStream:
        if state_spec is not None and not isinstance(state_spec, dict):
            raise FlowDefinitionError("process_with_state state_spec must be a dict when provided.")
        if state_ttl_s is not None and float(state_ttl_s) <= 0:
            raise FlowDefinitionError("process_with_state state_ttl_s must be > 0 when provided.")

        effective_stage_id = stage_id or self._shuffle_config.get("stage_id")
        num_partitions = int(self._shuffle_config.get("num_partitions", 1))
        process_meta: dict[str, Any] = {
            "stage_id": effective_stage_id,
            "num_partitions": num_partitions,
            "recovery_policy": normalize_recovery_policy(recovery_policy),
        }
        if state_ttl_s is not None:
            process_meta["state_ttl_s"] = float(state_ttl_s)
        if state_spec is not None:
            process_meta["state_spec"] = dict(state_spec)

        transformation = Transformation(
            self.flow_program,
            _ensure_flow_target(handler_ref, "process_with_state"),
            type="sys/stateful-process",
            operator_config={"stateful_process": process_meta},
        )
        return self._apply(transformation)


class GroupedStream:
    def __init__(self, partitioned: PartitionedStream, groupby_config: dict[str, Any]):
        self._partitioned = partitioned
        self._groupby_config = dict(groupby_config)

    def reduce_by_key(
        self,
        *,
        mode: str = "sum",
        value_field: str | None = None,
        value_index: int | None = None,
        plan: Any | None = None,
        stage_id: str | None = None,
        num_partitions: int | None = None,
    ) -> DataStream:
        reducer_mode = _normalize_reduce_by_key_mode(mode)
        groupby_meta = dict(self._groupby_config)
        if value_field is not None and value_index is not None:
            raise FlowDefinitionError(
                "reduce_by_key accepts only one of value_field or value_index.",
            )
        if mode == "sum":
            if value_field is not None:
                groupby_meta["value_field"] = value_field
            if value_index is not None:
                groupby_meta["value_index"] = value_index

        reducer_config = {"groupby": groupby_meta}
        return self._partitioned.reduce(
            mode=reducer_mode,
            plan=plan,
            stage_id=stage_id,
            num_partitions=num_partitions,
            reducer_config=reducer_config,
        )


__all__ = [
    "DataStream",
    "SinkStream",
    "ConnectedStreams",
    "PartitionedStream",
    "GroupedStream",
]
