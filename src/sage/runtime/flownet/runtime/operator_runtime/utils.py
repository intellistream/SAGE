from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any


def _normalize_iterable_outputs(result: Any) -> tuple[Any, ...]:
    if result is None:
        return ()
    if isinstance(result, tuple):
        return result
    if isinstance(result, list):
        return tuple(result)
    if isinstance(result, Iterable) and not isinstance(result, (str, bytes, bytearray, Mapping)):
        return tuple(result)
    return (result,)


def _extract_mapping_value(payload: Any, *, field_name: str) -> Any:
    if not isinstance(payload, Mapping):
        return None
    return payload.get(field_name)


def _parse_positive_int_strict(
    value: Any,
    *,
    field_name: str,
    exc_type: type[Exception],
) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError) as exc:
        raise exc_type(f"{field_name} must be an integer >= 1.") from exc
    if resolved < 1:
        raise exc_type(f"{field_name} must be an integer >= 1.")
    return resolved


def _parse_non_negative_int_strict(
    value: Any,
    *,
    field_name: str,
    exc_type: type[Exception],
) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError) as exc:
        raise exc_type(f"{field_name} must be an integer >= 0.") from exc
    if resolved < 0:
        raise exc_type(f"{field_name} must be an integer >= 0.")
    return resolved


def _stable_key_fragment(value: Any) -> str:
    normalized = _normalize_state_key_component(value)
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def _normalize_state_key_component(value: Any) -> Any:
    if isinstance(value, Mapping):
        items: list[list[Any]] = []
        for key, item_value in value.items():
            items.append(
                [
                    _normalize_state_key_component(key),
                    _normalize_state_key_component(item_value),
                ]
            )
        items.sort(key=lambda item: repr(item[0]))
        return {"dict": items}

    if isinstance(value, (list, tuple)):
        return {"seq": [_normalize_state_key_component(item) for item in value]}

    if isinstance(value, set):
        items = [_normalize_state_key_component(item) for item in value]
        items.sort(key=repr)
        return {"set": items}

    if isinstance(value, (bytes, bytearray)):
        return {"bytes": bytes(value).hex()}

    try:
        hash(value)
    except TypeError:
        return {"repr": repr(value)}
    return value


__all__ = [
    "_normalize_iterable_outputs",
    "_extract_mapping_value",
    "_parse_positive_int_strict",
    "_parse_non_negative_int_strict",
    "_stable_key_fragment",
    "_normalize_state_key_component",
]
