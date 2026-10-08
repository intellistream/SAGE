from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .errors import JoinContractError, OperatorExecutionError, ShuffleOperatorContractError
from .models import OperatorEvaluation
from .protocols import JoinSpec, ShuffleSpec
from .reducers import _parse_reducer_partition_id
from .utils import _extract_mapping_value, _stable_key_fragment


def _extract_route_node_ids(transformation: Any) -> tuple[str, ...]:
    operator_config = getattr(transformation, "operator_config", None)
    if operator_config is None:
        return ()
    if not isinstance(operator_config, Mapping):
        raise OperatorExecutionError("route operator_config must be a mapping.")

    routes = operator_config.get("routes")
    if routes is None:
        return ()
    if not isinstance(routes, list):
        raise OperatorExecutionError("route operator_config.routes must be a list.")

    route_node_ids: list[str] = []
    for index, route in enumerate(routes):
        if not isinstance(route, Mapping):
            raise OperatorExecutionError(f"route[{index}] must be a mapping.")
        trans = route.get("transformation")
        if isinstance(trans, str) and trans.strip():
            route_node_ids.append(trans.strip())
            continue
        trans_id = getattr(trans, "trans_id", None)
        if isinstance(trans_id, str) and trans_id.strip():
            route_node_ids.append(trans_id)
            continue
        raise OperatorExecutionError(f"route[{index}].transformation missing valid trans_id.")
    return tuple(route_node_ids)


def _evaluate_shuffle(
    *,
    transformation: Any,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
) -> OperatorEvaluation:
    spec = _extract_shuffle_spec(transformation)
    partition_key_source = _resolve_shuffle_partition_key_source(
        spec=spec,
        payload=payload,
        tags=tags,
        seq=seq,
        invoke_target=invoke_target,
    )
    key_fragment = _stable_key_fragment(partition_key_source)
    partition_id = int(key_fragment, 16) % spec.num_partitions

    output_tags = dict(tags)
    output_tags["partition_id"] = str(partition_id)
    output_tags["state_partition_key"] = key_fragment
    output_tags["shuffle_stage_id"] = spec.stage_id
    output_tags["shuffle_num_partitions"] = str(spec.num_partitions)

    route_node_ids = _select_shuffle_route_node_ids(
        transformation=transformation,
        partition_id=partition_id,
    )
    return OperatorEvaluation(
        outputs=(payload,),
        output_tags=(output_tags,),
        route_node_ids=route_node_ids,
    )


def _evaluate_join(
    *,
    transformation: Any,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
) -> OperatorEvaluation:
    shuffle_spec = _extract_shuffle_spec(transformation)
    join_spec = _extract_join_spec(
        transformation=transformation,
        fallback_stage_id=shuffle_spec.stage_id,
        fallback_num_partitions=shuffle_spec.num_partitions,
    )
    if join_spec.num_partitions != shuffle_spec.num_partitions:
        raise JoinContractError("join.num_partitions must match shuffle.num_partitions.")

    control = _extract_join_router_control(payload)
    if control == "done":
        partition_source = _extract_mapping_value(
            payload,
            field_name="partition_id",
        )
        if partition_source is None:
            partition_source = tags.get("partition_id")
        if partition_source is None:
            raise JoinContractError("join done frame requires partition_id in payload or tags.")
        partition_id = _parse_reducer_partition_id(
            partition_source,
            num_partitions=join_spec.num_partitions,
        )
        key_source = _extract_mapping_value(payload, field_name="state_partition_key")
        if key_source is None:
            key_source = tags.get("state_partition_key", partition_id)
        key_fragment = _stable_key_fragment(key_source)
    else:
        key_source = _resolve_shuffle_partition_key_source(
            spec=shuffle_spec,
            payload=payload,
            tags=tags,
            seq=seq,
            invoke_target=invoke_target,
        )
        key_fragment = _stable_key_fragment(key_source)
        partition_id = int(key_fragment, 16) % join_spec.num_partitions

    output_tags = dict(tags)
    output_tags["partition_id"] = str(partition_id)
    output_tags["state_partition_key"] = key_fragment
    output_tags["shuffle_stage_id"] = shuffle_spec.stage_id
    output_tags["shuffle_num_partitions"] = str(join_spec.num_partitions)
    output_tags["join_stage_id"] = join_spec.stage_id
    output_tags["join_num_partitions"] = str(join_spec.num_partitions)
    output_tags["join_side"] = join_spec.side

    route_node_ids = _select_shuffle_route_node_ids(
        transformation=transformation,
        partition_id=partition_id,
    )
    return OperatorEvaluation(
        outputs=(payload,),
        output_tags=(output_tags,),
        route_node_ids=route_node_ids,
    )


def _extract_join_spec(
    *,
    transformation: Any,
    fallback_stage_id: str,
    fallback_num_partitions: int,
) -> JoinSpec:
    join_meta = _extract_join_meta(transformation)
    side = _extract_join_side(transformation)
    return JoinSpec(
        stage_id=_extract_join_stage_id(
            join_meta,
            fallback_stage_id=fallback_stage_id,
        ),
        num_partitions=_extract_join_num_partitions(
            join_meta,
            fallback_num_partitions=fallback_num_partitions,
        ),
        side=side,
    )


def _extract_join_meta(transformation: Any) -> Mapping[str, Any]:
    operator_config = getattr(transformation, "operator_config", None)
    if not isinstance(operator_config, Mapping):
        raise JoinContractError("join operator_config must be a mapping.")
    join_meta = operator_config.get("join")
    if not isinstance(join_meta, Mapping):
        raise JoinContractError("join operator_config.join must be a mapping.")
    return join_meta


def _extract_join_side(transformation: Any) -> str:
    operator_config = getattr(transformation, "operator_config", None)
    if not isinstance(operator_config, Mapping):
        raise JoinContractError("join operator_config must be a mapping.")
    side = str(operator_config.get("side", "")).strip().lower()
    if side not in {"left", "right"}:
        raise JoinContractError("join operator_config.side must be one of: left, right.")
    return side


def _extract_join_stage_id(
    join_meta: Mapping[str, Any],
    *,
    fallback_stage_id: str,
) -> str:
    stage_id = join_meta.get("stage_id", fallback_stage_id)
    if stage_id is None:
        stage_id = fallback_stage_id
    return _join_as_non_empty_str(stage_id, field_name="join.stage_id")


def _extract_join_num_partitions(
    join_meta: Mapping[str, Any],
    *,
    fallback_num_partitions: int,
) -> int:
    raw = join_meta.get("num_partitions", fallback_num_partitions)
    try:
        num_partitions = int(raw)
    except (TypeError, ValueError) as exc:
        raise JoinContractError("join.num_partitions must be an integer >= 1.") from exc
    if num_partitions < 1:
        raise JoinContractError("join.num_partitions must be an integer >= 1.")
    return num_partitions


def _extract_join_router_control(payload: Any) -> str:
    control = _extract_mapping_value(payload, field_name="control")
    if control is None:
        return "data"
    normalized = str(control or "").strip().lower()
    if not normalized:
        return "data"
    if normalized not in {"data", "done"}:
        raise JoinContractError("join.control must be one of: data, done.")
    return normalized


def _extract_shuffle_spec(transformation: Any) -> ShuffleSpec:
    shuffle_meta = _extract_shuffle_meta(transformation)
    return ShuffleSpec(
        stage_id=_extract_shuffle_stage_id(shuffle_meta, transformation),
        num_partitions=_extract_shuffle_num_partitions(shuffle_meta),
        key_fn=shuffle_meta.get("key_fn"),
        key_field=_extract_optional_shuffle_key_field(shuffle_meta.get("key_field")),
        key_index=_extract_shuffle_key_index(shuffle_meta.get("key_index", 0)),
    )


def _extract_optional_shuffle_key_field(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ShuffleOperatorContractError("shuffle.key_field must be a non-empty string.")
    return raw.strip()


def _extract_shuffle_meta(transformation: Any) -> Mapping[str, Any]:
    operator_config = getattr(transformation, "operator_config", None)
    if not isinstance(operator_config, Mapping):
        raise ShuffleOperatorContractError(
            "shuffle operator_config must be a mapping.",
        )
    shuffle_meta = operator_config.get("shuffle")
    if not isinstance(shuffle_meta, Mapping):
        raise ShuffleOperatorContractError(
            "shuffle operator_config.shuffle must be a mapping.",
        )
    return shuffle_meta


def _extract_shuffle_num_partitions(shuffle_meta: Mapping[str, Any]) -> int:
    raw = shuffle_meta.get("num_partitions", 1)
    try:
        num_partitions = int(raw)
    except (TypeError, ValueError) as exc:
        raise ShuffleOperatorContractError(
            "shuffle.num_partitions must be an integer > 0.",
        ) from exc
    if num_partitions <= 0:
        raise ShuffleOperatorContractError(
            "shuffle.num_partitions must be an integer > 0.",
        )
    return num_partitions


def _extract_shuffle_stage_id(shuffle_meta: Mapping[str, Any], transformation: Any) -> str:
    stage_id = shuffle_meta.get("stage_id")
    if stage_id is None:
        stage_id = getattr(transformation, "trans_id", None)
    if not isinstance(stage_id, str) or not stage_id.strip():
        raise ShuffleOperatorContractError("shuffle.stage_id must be a non-empty string.")
    return stage_id.strip()


def _resolve_shuffle_partition_key_source(
    *,
    spec: ShuffleSpec,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
) -> Any:
    if spec.key_fn is not None and spec.key_field is not None:
        raise ShuffleOperatorContractError(
            "shuffle.key_fn cannot be combined with shuffle.key_field.",
        )
    if spec.key_fn is not None and spec.key_index not in (0,):
        raise ShuffleOperatorContractError(
            "shuffle.key_fn cannot be combined with non-default shuffle.key_index.",
        )

    if spec.key_fn is not None:
        if invoke_target is None:
            raise ShuffleOperatorContractError(
                "shuffle.key_fn requires invoke_target runtime support.",
            )
        return invoke_target(spec.key_fn, payload, tags, seq)

    return _extract_shuffle_partition_key_from_payload(
        payload=payload,
        key_index=spec.key_index,
        key_field=spec.key_field,
    )


def _extract_shuffle_key_index(raw: Any) -> int:
    if raw is None:
        return 0
    try:
        key_index = int(raw)
    except (TypeError, ValueError) as exc:
        raise ShuffleOperatorContractError(
            "shuffle.key_index must be an integer >= 0.",
        ) from exc
    if key_index < 0:
        raise ShuffleOperatorContractError("shuffle.key_index must be an integer >= 0.")
    return key_index


def _extract_shuffle_partition_key_from_payload(
    *,
    payload: Any,
    key_index: int,
    key_field: str | None,
) -> Any:
    if key_field is not None:
        if not isinstance(payload, Mapping):
            raise ShuffleOperatorContractError(
                "shuffle.key_field requires mapping payload.",
            )
        if key_field not in payload:
            raise ShuffleOperatorContractError(
                f"shuffle.key_field '{key_field}' is missing in payload.",
            )
        return payload[key_field]

    if isinstance(payload, (list, tuple)):
        if key_index >= len(payload):
            raise ShuffleOperatorContractError("shuffle.key_index out of range.")
        return payload[key_index]

    if key_index != 0:
        raise ShuffleOperatorContractError("shuffle.key_index out of range.")
    return payload


def _select_shuffle_route_node_ids(
    *,
    transformation: Any,
    partition_id: int,
) -> tuple[str, ...] | None:
    downstreams = getattr(transformation, "downstreams", None)
    if downstreams is None:
        return None
    if not isinstance(downstreams, list):
        raise ShuffleOperatorContractError("transformation.downstreams must be a list.")
    if not downstreams:
        return ()

    downstream_node_ids: list[str] = []
    for index, downstream in enumerate(downstreams):
        trans_id = getattr(downstream, "trans_id", None)
        if not isinstance(trans_id, str) or not trans_id.strip():
            raise ShuffleOperatorContractError(
                f"downstreams[{index}] missing valid trans_id",
            )
        downstream_node_ids.append(trans_id)
    selected_index = partition_id % len(downstream_node_ids)
    return (downstream_node_ids[selected_index],)


def _join_as_non_empty_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JoinContractError(f"{field_name} must be a non-empty string.")
    return value.strip()


__all__ = [
    "_extract_route_node_ids",
    "_evaluate_shuffle",
    "_evaluate_join",
]
