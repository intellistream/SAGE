from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

_FLOWNET_URI_SCHEME = "flownet://"
_TOPIC_PREFIX = "topic:"
_DEFAULT_CLUSTER = "local"
_DEFAULT_SCOPE = "default"
_TOPIC_KIND = "topic"


def _normalize_non_empty(value: str, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return normalized


def _normalize_non_negative_int(value: Any, *, field_name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative.")
    return normalized


def _normalize_topic_uri(topic_uri: str) -> str:
    return _canonical_topic_key(_normalize_non_empty(topic_uri, field_name="topic_uri"))


def _canonical_topic_key(topic_id: str) -> str:
    raw_topic_id = _normalize_non_empty(topic_id, field_name="topic_id")
    if raw_topic_id.startswith(_FLOWNET_URI_SCHEME):
        return _normalize_flownet_topic_uri(raw_topic_id)
    if raw_topic_id.startswith(_TOPIC_PREFIX):
        topic_name = raw_topic_id[len(_TOPIC_PREFIX) :].strip()
        if not topic_name:
            raise ValueError("topic shorthand must include a non-empty name.")
        return _build_topic_uri(topic_name)
    if ":" in raw_topic_id:
        return raw_topic_id
    return _build_topic_uri(raw_topic_id)


def _build_topic_uri(topic_name: str) -> str:
    return f"{_FLOWNET_URI_SCHEME}{_DEFAULT_CLUSTER}/{_DEFAULT_SCOPE}/{_TOPIC_KIND}/{topic_name}"


def _normalize_flownet_topic_uri(topic_uri: str) -> str:
    parsed = urlparse(topic_uri)
    if parsed.scheme != "flownet":
        raise ValueError(f"unsupported topic URI scheme: {parsed.scheme!r}")
    if not parsed.netloc:
        raise ValueError("topic URI must include a cluster segment.")
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    if len(path_segments) < 3:
        raise ValueError(
            "topic URI must follow flownet://<cluster>/<scope>/topic/<name>.",
        )
    scope, kind, *name_segments = path_segments
    if kind != _TOPIC_KIND:
        return topic_uri
    topic_name = "/".join(name_segments).strip("/")
    if not topic_name:
        raise ValueError("topic URI must include a non-empty topic name.")
    return f"{_FLOWNET_URI_SCHEME}{parsed.netloc}/{scope}/{_TOPIC_KIND}/{topic_name}"


__all__ = [
    "_normalize_non_empty",
    "_normalize_non_negative_int",
    "_normalize_topic_uri",
]
