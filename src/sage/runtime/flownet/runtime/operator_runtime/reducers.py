from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import JoinContractError, MergeReducerContractError, ReducerContractError
from .models import _JoinReducerState, _MergeReducerState, _ReducerState
from .protocols import (
    JoinReducerFrame,
    JoinReducerSpec,
    MergeReducerFrame,
    MergeReducerSpec,
    ReducerFrame,
    ReducerSpec,
)
from .utils import _extract_mapping_value, _parse_non_negative_int_strict


class ReducerRuntime:
    """
    Minimal in-memory runtime for v1 `sys/reducer`.

    Contract freeze (Lane-C2):
    1. state key = `(operator identity, event_group_id, reducer.stage_id)`.
    2. frame contract:
       - data: raw payload OR `{control="data", partition_id?, value}`
       - flush: `{control="flush", partition_id?}`
       - done: `{control="done", partition_id?}`
    3. terminal output is emitted once all partitions are done.
       `flush` emits snapshot without finalizing state.
    """

    def __init__(self) -> None:
        self._states: dict[tuple[int, str, str], _ReducerState] = {}

    def evaluate(
        self,
        *,
        transformation: Any,
        payload: Any,
        tags: Mapping[str, str],
        event_group_id: str | None,
    ) -> tuple[Any, ...]:
        if not isinstance(event_group_id, str) or not event_group_id.strip():
            raise ReducerContractError(
                "sys/reducer requires a non-empty event_group_id for state isolation.",
            )
        spec = _extract_reducer_spec(transformation)

        state_key = (id(transformation), event_group_id, spec.stage_id)
        state = self._states.get(state_key)
        if state is None:
            state = _ReducerState(
                stage_id=spec.stage_id,
                mode=spec.mode,
                num_partitions=spec.num_partitions,
                groupby=spec.groupby,
                acc=_new_reducer_accumulator(spec.mode),
            )
            self._states[state_key] = state

        frame = _parse_reducer_frame(
            payload=payload,
            tags=tags,
            num_partitions=state.num_partitions,
        )
        if frame.control == "data":
            if frame.partition_id in state.done_partitions:
                # Deterministic late-data drop after partition done.
                return ()
            _accumulate_reducer_value(state=state, value=frame.value)
            return ()

        if frame.control == "flush":
            return (_materialize_reducer_snapshot(state),)

        if frame.partition_id in state.done_partitions:
            return ()
        state.done_partitions.add(frame.partition_id)
        if len(state.done_partitions) < state.num_partitions:
            return ()

        output = _materialize_reducer_snapshot(state)
        self._states.pop(state_key, None)
        return (output,)


class JoinReducerRuntime:
    """
    Minimal in-memory runtime for `sys/join-reducer`.

    Contract freeze (Lane-C3):
    1. state key = `(operator identity, event_group_id, join.stage_id)`.
    2. frame contract:
       - data: raw payload OR `{control="data", side, partition_id?, value}`
       - flush: `{control="flush"}`
       - done: `{control="done", side, partition_id?}`
    3. terminal output is emitted once all partitions are done on both sides.
       Snapshot/final output is deterministic partition-order cartesian pairs.
    """

    def __init__(self) -> None:
        self._states: dict[tuple[int, str, str], _JoinReducerState] = {}

    def evaluate(
        self,
        *,
        transformation: Any,
        payload: Any,
        tags: Mapping[str, str],
        event_group_id: str | None,
    ) -> tuple[Any, ...]:
        if not isinstance(event_group_id, str) or not event_group_id.strip():
            raise JoinContractError(
                "sys/join-reducer requires a non-empty event_group_id for state isolation.",
            )
        spec = _resolve_join_reducer_spec(
            transformation=transformation,
            tags=tags,
        )
        state_key = (id(transformation), event_group_id, spec.stage_id)
        state = self._states.get(state_key)
        if state is None:
            state = _JoinReducerState(
                stage_id=spec.stage_id,
                num_partitions=spec.num_partitions,
            )
            self._states[state_key] = state
        elif state.num_partitions != spec.num_partitions:
            raise JoinContractError(
                "join.num_partitions changed while state is active for the same stage/event_group.",
            )

        frame = _parse_join_reducer_frame(
            payload=payload,
            tags=tags,
            num_partitions=spec.num_partitions,
        )
        if frame.control == "flush":
            return (_materialize_join_reducer_snapshot(state),)

        bucket_done = state.done_left if frame.side == "left" else state.done_right
        if frame.control == "data":
            if frame.partition_id in bucket_done:
                # Deterministic late-data drop after side/partition done.
                return ()
            bucket = state.left if frame.side == "left" else state.right
            bucket.setdefault(frame.partition_id, []).append(frame.value)
            return ()

        if frame.partition_id in bucket_done:
            return ()
        bucket_done.add(frame.partition_id)
        if (
            len(state.done_left) < spec.num_partitions
            or len(state.done_right) < spec.num_partitions
        ):
            return ()

        output = _materialize_join_reducer_snapshot(state)
        self._states.pop(state_key, None)
        return (output,)


class MergeReducerRuntime:
    """
    Minimal in-memory runtime for `sys/merge-reducer`.

    Contract freeze (Lane-C3):
    1. state key = `(operator identity, event_group_id, reducer.stage_id)`.
    2. frame contract:
       - partial: raw payload OR `{control="partial", partition_id?, value}`
       - flush: `{control="flush"}`
       - done: `{control="done", partition_id?}`
    3. terminal output is emitted once all expected partitions have both
       `partial` and `done` markers.
    """

    def __init__(self) -> None:
        self._states: dict[tuple[int, str, str], _MergeReducerState] = {}

    def evaluate(
        self,
        *,
        transformation: Any,
        payload: Any,
        tags: Mapping[str, str],
        event_group_id: str | None,
    ) -> tuple[Any, ...]:
        if not isinstance(event_group_id, str) or not event_group_id.strip():
            raise MergeReducerContractError(
                "sys/merge-reducer requires a non-empty event_group_id for state isolation.",
            )
        spec = _resolve_merge_reducer_spec(
            transformation=transformation,
            tags=tags,
        )
        state_key = (id(transformation), event_group_id, spec.stage_id)
        state = self._states.get(state_key)
        if state is None:
            state = _MergeReducerState(
                stage_id=spec.stage_id,
                mode=spec.mode,
                expected_partition_ids=spec.expected_partition_ids,
                acc=_new_reducer_accumulator(spec.mode),
            )
            self._states[state_key] = state
        elif state.mode != spec.mode or state.expected_partition_ids != spec.expected_partition_ids:
            raise MergeReducerContractError(
                "merge-reducer mode/expected partitions changed while state is active.",
            )

        frame = _parse_merge_reducer_frame(
            payload=payload,
            tags=tags,
            expected_partition_ids=spec.expected_partition_ids,
        )
        if frame.partition_id not in spec.expected_partition_ids:
            return ()

        if frame.control == "flush":
            return (_materialize_merge_reducer_snapshot(state),)

        if frame.control == "partial":
            if frame.partition_id in state.partial_partitions:
                return ()
            state.partial_partitions.add(frame.partition_id)
            state.acc = _merge_partial_into_reducer_accumulator(
                mode=spec.mode,
                acc=state.acc,
                value=frame.value,
            )
            return ()

        if frame.partition_id in state.done_partitions:
            return ()
        state.done_partitions.add(frame.partition_id)
        if not _merge_reducer_is_complete(state):
            return ()

        output = _materialize_merge_reducer_snapshot(state)
        self._states.pop(state_key, None)
        return (output,)


def _extract_reducer_meta(transformation: Any) -> Mapping[str, Any]:
    operator_config = getattr(transformation, "operator_config", None)
    if not isinstance(operator_config, Mapping):
        raise ReducerContractError("reducer operator_config must be a mapping.")
    reducer_meta = operator_config.get("reducer")
    if not isinstance(reducer_meta, Mapping):
        raise ReducerContractError("reducer operator_config.reducer must be a mapping.")
    return reducer_meta


def _extract_reducer_spec(transformation: Any) -> ReducerSpec:
    reducer_meta = _extract_reducer_meta(transformation)
    return ReducerSpec(
        stage_id=_extract_reducer_stage_id(reducer_meta, transformation),
        mode=_extract_reducer_mode(reducer_meta),
        num_partitions=_extract_reducer_num_partitions(reducer_meta),
        groupby=_extract_reducer_groupby(reducer_meta),
    )


def _extract_reducer_stage_id(reducer_meta: Mapping[str, Any], transformation: Any) -> str:
    stage_id = reducer_meta.get("stage_id")
    if stage_id is None:
        stage_id = getattr(transformation, "trans_id", None)
    return _reducer_as_non_empty_str(stage_id, field_name="reducer.stage_id")


def _extract_reducer_mode(reducer_meta: Mapping[str, Any]) -> str:
    mode = _reducer_as_non_empty_str(
        reducer_meta.get("mode", "concat"),
        field_name="reducer.mode",
    )
    if mode not in {
        "count",
        "sum",
        "concat",
        "count_by_key",
        "sum_by_key",
        "concat_by_key",
    }:
        raise ReducerContractError(f"unsupported_reducer_mode:{mode}")
    return mode


def _extract_reducer_num_partitions(reducer_meta: Mapping[str, Any]) -> int:
    raw_value = reducer_meta.get("num_partitions", 1)
    try:
        num_partitions = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ReducerContractError("reducer.num_partitions must be an integer >= 1.") from exc
    if num_partitions < 1:
        raise ReducerContractError("reducer.num_partitions must be an integer >= 1.")
    return num_partitions


def _extract_reducer_groupby(reducer_meta: Mapping[str, Any]) -> Mapping[str, Any]:
    groupby = reducer_meta.get("groupby")
    if groupby is None:
        return {}
    if not isinstance(groupby, Mapping):
        raise ReducerContractError("reducer.groupby must be a mapping when provided.")
    return dict(groupby)


def _parse_reducer_frame(
    *,
    payload: Any,
    tags: Mapping[str, str],
    num_partitions: int,
) -> ReducerFrame:
    control = "data"
    partition_source: Any = None
    value: Any = payload

    if isinstance(payload, Mapping) and "control" in payload:
        control = _normalize_reducer_control(payload.get("control"))
        partition_source = payload.get("partition_id")
        if control == "data":
            value = payload.get("value")
            if "value" not in payload:
                raise ReducerContractError(
                    "reducer data frame with control field requires payload.value.",
                )

    if partition_source is None:
        partition_source = tags.get("partition_id")
    if partition_source is None:
        partition_source = 0
    partition_id = _parse_reducer_partition_id(
        partition_source,
        num_partitions=num_partitions,
    )
    if control != "data":
        value = None
    return ReducerFrame(
        control=control,
        partition_id=partition_id,
        value=value,
    )


def _normalize_reducer_control(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return "data"
    if normalized not in {"data", "flush", "done"}:
        raise ReducerContractError("reducer.control must be one of: data, flush, done.")
    return normalized


def _parse_reducer_partition_id(value: Any, *, num_partitions: int) -> int:
    try:
        partition_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ReducerContractError("reducer.partition_id must be an integer >= 0.") from exc
    if partition_id < 0 or partition_id >= num_partitions:
        raise ReducerContractError("reducer.partition_id out of range.")
    return partition_id


def _new_reducer_accumulator(mode: str) -> Any:
    if mode in {"count_by_key", "sum_by_key", "concat_by_key"}:
        return {}
    if mode == "count":
        return 0
    if mode == "sum":
        return 0
    return []


def _accumulate_reducer_value(*, state: _ReducerState, value: Any) -> None:
    mode = state.mode
    if mode == "count":
        state.acc += 1
        return
    if mode == "sum":
        try:
            state.acc += value
        except Exception as exc:
            raise ReducerContractError("reducer.sum payload is not additive.") from exc
        return
    if mode == "concat":
        state.acc.append(value)
        return

    key = _resolve_reducer_group_key(value, groupby=state.groupby)
    if mode == "count_by_key":
        state.acc[key] = int(state.acc.get(key, 0)) + 1
        return
    if mode == "sum_by_key":
        amount = _resolve_reducer_group_sum_value(value, groupby=state.groupby)
        try:
            state.acc[key] = state.acc.get(key, 0) + amount
        except Exception as exc:
            raise ReducerContractError("reducer.sum_by_key payload value is not additive.") from exc
        return

    bucket = state.acc.setdefault(key, [])
    bucket.append(value)


def _resolve_reducer_group_key(value: Any, *, groupby: Mapping[str, Any]) -> Any:
    key_field = groupby.get("key_field")
    key_index = _parse_groupby_index(
        groupby.get("key_index", 0),
        field_name="reducer.groupby.key_index",
    )

    if isinstance(value, Mapping):
        if key_field is not None:
            field = _reducer_as_non_empty_str(
                key_field,
                field_name="reducer.groupby.key_field",
            )
            if field not in value:
                raise ReducerContractError(
                    f"reducer.groupby.key_field '{field}' is missing in payload."
                )
            return value[field]
        if "key" in value:
            return value["key"]

    if isinstance(value, (list, tuple)):
        if key_index >= len(value):
            raise ReducerContractError("reducer.groupby.key_index out of range.")
        return value[key_index]

    raise ReducerContractError(
        "by-key reducer payload must be mapping(key_field/key) or sequence(key_index).",
    )


def _resolve_reducer_group_sum_value(value: Any, *, groupby: Mapping[str, Any]) -> Any:
    value_field = groupby.get("value_field")
    value_index_raw = groupby.get("value_index")
    key_index = _parse_groupby_index(
        groupby.get("key_index", 0),
        field_name="reducer.groupby.key_index",
    )

    if isinstance(value, Mapping):
        if value_field is not None:
            field = _reducer_as_non_empty_str(
                value_field,
                field_name="reducer.groupby.value_field",
            )
            if field not in value:
                raise ReducerContractError(
                    f"reducer.groupby.value_field '{field}' is missing in payload."
                )
            return value[field]
        if "value" in value:
            return value["value"]

    if isinstance(value, (list, tuple)):
        if value_index_raw is not None:
            value_index = _parse_groupby_index(
                value_index_raw,
                field_name="reducer.groupby.value_index",
            )
            if value_index >= len(value):
                raise ReducerContractError("reducer.groupby.value_index out of range.")
            return value[value_index]
        if len(value) >= 2:
            value_index = 1 if key_index == 0 else 0
            if value_index < len(value):
                return value[value_index]

    raise ReducerContractError(
        "sum_by_key requires value_field/value_index or pair-like sequence payload.",
    )


def _parse_groupby_index(value: Any, *, field_name: str) -> int:
    try:
        index = int(value)
    except (TypeError, ValueError) as exc:
        raise ReducerContractError(f"{field_name} must be an integer >= 0.") from exc
    if index < 0:
        raise ReducerContractError(f"{field_name} must be an integer >= 0.")
    return index


def _materialize_reducer_snapshot(state: _ReducerState) -> Any:
    if state.mode == "count":
        return int(state.acc)
    if state.mode == "sum":
        return state.acc
    if state.mode == "concat":
        return tuple(state.acc)

    items: list[tuple[Any, Any]] = []
    for key, aggregate in state.acc.items():
        if state.mode == "concat_by_key":
            items.append((key, tuple(aggregate)))
        else:
            items.append((key, aggregate))
    items.sort(key=lambda kv: repr(kv[0]))
    return tuple(items)


def _reducer_as_non_empty_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReducerContractError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _resolve_join_reducer_spec(
    *,
    transformation: Any,
    tags: Mapping[str, str],
) -> JoinReducerSpec:
    operator_config = getattr(transformation, "operator_config", None)
    join_meta: Mapping[str, Any] = {}
    if operator_config is not None:
        if not isinstance(operator_config, Mapping):
            raise JoinContractError("join-reducer operator_config must be a mapping when provided.")
        join_meta_raw = operator_config.get("join")
        if join_meta_raw is not None:
            if not isinstance(join_meta_raw, Mapping):
                raise JoinContractError(
                    "join-reducer operator_config.join must be a mapping when provided."
                )
            join_meta = dict(join_meta_raw)

    stage_id_raw = join_meta.get("stage_id")
    tag_stage_id = tags.get("join_stage_id")
    if (
        stage_id_raw is not None
        and tag_stage_id
        and str(stage_id_raw).strip() != str(tag_stage_id).strip()
    ):
        raise JoinContractError("join.stage_id mismatch between operator config and tags.")
    stage_id = stage_id_raw if stage_id_raw is not None else tag_stage_id
    if stage_id is None:
        stage_id = getattr(transformation, "trans_id", None)
    stage_id_value = _join_as_non_empty_str(stage_id, field_name="join.stage_id")

    num_partitions_raw = join_meta.get("num_partitions")
    tag_num_partitions = tags.get("join_num_partitions")
    if num_partitions_raw is None:
        num_partitions_raw = tag_num_partitions
    elif tag_num_partitions is not None:
        try:
            if int(num_partitions_raw) != int(tag_num_partitions):
                raise JoinContractError(
                    "join.num_partitions mismatch between operator config and tags."
                )
        except (TypeError, ValueError) as exc:
            raise JoinContractError("join.num_partitions must be an integer >= 1.") from exc

    if num_partitions_raw is None:
        num_partitions_raw = 1
    try:
        num_partitions = int(num_partitions_raw)
    except (TypeError, ValueError) as exc:
        raise JoinContractError("join.num_partitions must be an integer >= 1.") from exc
    if num_partitions < 1:
        raise JoinContractError("join.num_partitions must be an integer >= 1.")
    return JoinReducerSpec(
        stage_id=stage_id_value,
        num_partitions=num_partitions,
    )


def _parse_join_reducer_frame(
    *,
    payload: Any,
    tags: Mapping[str, str],
    num_partitions: int,
) -> JoinReducerFrame:
    control = _extract_join_reducer_control(payload)
    if control == "flush":
        return JoinReducerFrame(
            control=control,
            side="left",
            partition_id=0,
            value=None,
        )

    side = _resolve_join_reducer_side(payload=payload, tags=tags)
    partition_source = _extract_mapping_value(payload, field_name="partition_id")
    if partition_source is None:
        partition_source = tags.get("partition_id")
    if partition_source is None:
        partition_source = 0
    partition_id = _parse_reducer_partition_id(
        partition_source,
        num_partitions=num_partitions,
    )

    if control == "done":
        return JoinReducerFrame(
            control=control,
            side=side,
            partition_id=partition_id,
            value=None,
        )

    value = payload
    if isinstance(payload, Mapping) and "control" in payload:
        if "value" not in payload:
            raise JoinContractError(
                "join-reducer data frame with control field requires payload.value.",
            )
        value = payload.get("value")
    return JoinReducerFrame(
        control=control,
        side=side,
        partition_id=partition_id,
        value=value,
    )


def _extract_join_reducer_control(payload: Any) -> str:
    control = _extract_mapping_value(payload, field_name="control")
    if control is None:
        return "data"
    normalized = str(control or "").strip().lower()
    if not normalized:
        return "data"
    if normalized not in {"data", "flush", "done"}:
        raise JoinContractError("join-reducer.control must be one of: data, flush, done.")
    return normalized


def _resolve_join_reducer_side(*, payload: Any, tags: Mapping[str, str]) -> str:
    side = _extract_mapping_value(payload, field_name="side")
    if side is None:
        side = tags.get("join_side") or tags.get("side")
    side_value = str(side or "").strip().lower()
    if side_value not in {"left", "right"}:
        raise JoinContractError("join-reducer side must be one of: left, right.")
    return side_value


def _materialize_join_reducer_snapshot(state: _JoinReducerState) -> tuple[tuple[Any, Any], ...]:
    pairs: list[tuple[Any, Any]] = []
    for partition_id in range(state.num_partitions):
        left_values = state.left.get(partition_id, [])
        right_values = state.right.get(partition_id, [])
        for left_value in left_values:
            for right_value in right_values:
                pairs.append((left_value, right_value))
    return tuple(pairs)


def _resolve_merge_reducer_spec(
    *,
    transformation: Any,
    tags: Mapping[str, str],
) -> MergeReducerSpec:
    operator_config = getattr(transformation, "operator_config", None)
    reducer_meta: Mapping[str, Any] = {}
    if operator_config is not None:
        if not isinstance(operator_config, Mapping):
            raise MergeReducerContractError(
                "merge-reducer operator_config must be a mapping when provided."
            )
        reducer_meta_raw = operator_config.get("reducer")
        if reducer_meta_raw is not None:
            if not isinstance(reducer_meta_raw, Mapping):
                raise MergeReducerContractError(
                    "merge-reducer operator_config.reducer must be a mapping when provided.",
                )
            reducer_meta = dict(reducer_meta_raw)

    stage_id_raw = reducer_meta.get("stage_id")
    tag_stage_id = tags.get("reducer_stage_id")
    if (
        stage_id_raw is not None
        and tag_stage_id
        and str(stage_id_raw).strip() != str(tag_stage_id).strip()
    ):
        raise MergeReducerContractError(
            "reducer.stage_id mismatch between operator config and tags."
        )
    stage_id = stage_id_raw if stage_id_raw is not None else tag_stage_id
    if stage_id is None:
        stage_id = getattr(transformation, "trans_id", None)
    stage_id_value = _merge_as_non_empty_str(stage_id, field_name="reducer.stage_id")

    mode_raw = reducer_meta.get("mode")
    tag_mode = tags.get("reducer_mode")
    if mode_raw is not None and tag_mode and str(mode_raw).strip() != str(tag_mode).strip():
        raise MergeReducerContractError("reducer.mode mismatch between operator config and tags.")
    mode = str(mode_raw if mode_raw is not None else (tag_mode or "concat")).strip()
    mode_value = _extract_reducer_mode({"mode": mode})

    num_partitions_raw = reducer_meta.get("num_partitions")
    tag_num_partitions = tags.get("reducer_num_partitions")
    if num_partitions_raw is None:
        num_partitions_raw = tag_num_partitions
    if num_partitions_raw is None:
        num_partitions_raw = 1
    try:
        num_partitions = int(num_partitions_raw)
    except (TypeError, ValueError) as exc:
        raise MergeReducerContractError("reducer.num_partitions must be an integer >= 1.") from exc
    if num_partitions < 1:
        raise MergeReducerContractError("reducer.num_partitions must be an integer >= 1.")

    expected_partition_ids = _parse_merge_expected_partition_ids(
        reducer_meta.get("merge_partitions"),
        num_partitions=num_partitions,
    )
    return MergeReducerSpec(
        stage_id=stage_id_value,
        mode=mode_value,
        expected_partition_ids=expected_partition_ids,
    )


def _parse_merge_expected_partition_ids(raw: Any, *, num_partitions: int) -> tuple[int, ...]:
    if raw is None:
        return tuple(range(num_partitions))
    if not isinstance(raw, (list, tuple)):
        raise MergeReducerContractError(
            "reducer.merge_partitions must be a list/tuple when provided."
        )
    parsed: set[int] = set()
    for item in raw:
        partition_id = _parse_non_negative_int_strict(
            item,
            field_name="reducer.merge_partitions[]",
            exc_type=MergeReducerContractError,
        )
        parsed.add(partition_id)
    if not parsed:
        raise MergeReducerContractError("reducer.merge_partitions must not be empty.")
    return tuple(sorted(parsed))


def _parse_merge_reducer_frame(
    *,
    payload: Any,
    tags: Mapping[str, str],
    expected_partition_ids: tuple[int, ...],
) -> MergeReducerFrame:
    control = _extract_merge_reducer_control(payload)
    if control == "flush":
        # flush does not depend on one partition; keep deterministic placeholder.
        return MergeReducerFrame(
            control=control,
            partition_id=expected_partition_ids[0],
            value=None,
        )

    partition_source = _extract_mapping_value(payload, field_name="partition_id")
    if partition_source is None:
        partition_source = tags.get("partition_id")
    if partition_source is None:
        partition_source = 0
    partition_id = _parse_non_negative_int_strict(
        partition_source,
        field_name="merge-reducer.partition_id",
        exc_type=MergeReducerContractError,
    )

    if control == "done":
        return MergeReducerFrame(
            control=control,
            partition_id=partition_id,
            value=None,
        )

    value = payload
    if isinstance(payload, Mapping) and "control" in payload:
        if "value" not in payload:
            raise MergeReducerContractError(
                "merge-reducer partial frame with control field requires payload.value.",
            )
        value = payload.get("value")
    return MergeReducerFrame(
        control=control,
        partition_id=partition_id,
        value=value,
    )


def _extract_merge_reducer_control(payload: Any) -> str:
    control = _extract_mapping_value(payload, field_name="control")
    if control is None:
        return "partial"
    normalized = str(control or "").strip().lower()
    if not normalized:
        return "partial"
    if normalized not in {"partial", "flush", "done"}:
        raise MergeReducerContractError(
            "merge-reducer.control must be one of: partial, flush, done."
        )
    return normalized


def _merge_partial_into_reducer_accumulator(*, mode: str, acc: Any, value: Any) -> Any:
    if mode == "count":
        try:
            return acc + value
        except Exception as exc:
            raise MergeReducerContractError("merge-reducer.count partial is not additive.") from exc
    if mode == "sum":
        try:
            return acc + value
        except Exception as exc:
            raise MergeReducerContractError("merge-reducer.sum partial is not additive.") from exc
    if mode == "concat":
        if isinstance(value, (list, tuple)):
            acc.extend(value)
        else:
            acc.append(value)
        return acc

    items = _extract_merge_partial_keyed_items(value)
    if mode == "count_by_key":
        for key, partial in items:
            try:
                acc[key] = acc.get(key, 0) + partial
            except Exception as exc:
                raise MergeReducerContractError(
                    "merge-reducer.count_by_key partial value is not additive.",
                ) from exc
        return acc
    if mode == "sum_by_key":
        for key, partial in items:
            try:
                acc[key] = acc.get(key, 0) + partial
            except Exception as exc:
                raise MergeReducerContractError(
                    "merge-reducer.sum_by_key partial value is not additive.",
                ) from exc
        return acc

    for key, partial in items:
        bucket = acc.setdefault(key, [])
        if isinstance(partial, (list, tuple)):
            bucket.extend(partial)
        else:
            bucket.append(partial)
    return acc


def _extract_merge_partial_keyed_items(value: Any) -> tuple[tuple[Any, Any], ...]:
    if isinstance(value, Mapping):
        return tuple((key, item_value) for key, item_value in value.items())
    if isinstance(value, (list, tuple)):
        items: list[tuple[Any, Any]] = []
        for index, item in enumerate(value):
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise MergeReducerContractError(
                    f"merge-reducer by-key partial[{index}] must be a (key, value) pair.",
                )
            items.append((item[0], item[1]))
        return tuple(items)
    raise MergeReducerContractError(
        "merge-reducer by-key partial must be mapping or list/tuple of (key, value) pairs.",
    )


def _merge_reducer_is_complete(state: _MergeReducerState) -> bool:
    expected = set(state.expected_partition_ids)
    return expected.issubset(state.partial_partitions) and expected.issubset(state.done_partitions)


def _materialize_merge_reducer_snapshot(state: _MergeReducerState) -> Any:
    if state.mode == "count":
        return int(state.acc)
    if state.mode == "sum":
        return state.acc
    if state.mode == "concat":
        return tuple(state.acc)

    items: list[tuple[Any, Any]] = []
    for key, aggregate in state.acc.items():
        if state.mode == "concat_by_key":
            items.append((key, tuple(aggregate)))
        else:
            items.append((key, aggregate))
    items.sort(key=lambda kv: repr(kv[0]))
    return tuple(items)


def _join_as_non_empty_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JoinContractError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _merge_as_non_empty_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MergeReducerContractError(f"{field_name} must be a non-empty string.")
    return value.strip()


__all__ = [
    "ReducerRuntime",
    "JoinReducerRuntime",
    "MergeReducerRuntime",
    "_parse_reducer_partition_id",
]
