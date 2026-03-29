from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sage.runtime.flownet.runtime.topics.normalization import _normalize_non_empty
from sage.runtime.flownet.runtime.topics.routing_directory import TopicRoutingDirectory


class TopicEventDispatch:
    """Data-plane event publish/forward routing helper."""

    def __init__(
        self,
        *,
        routing_directory: TopicRoutingDirectory,
        local_address: Callable[[], str],
    ) -> None:
        self._routing_directory = routing_directory
        self._local_address = local_address

    def publish_or_forward_event(
        self,
        *,
        topic_uri: str,
        event_group_id: str,
        payload: Any,
        tags: dict[str, str] | None,
        seq: int | None,
        epoch: int | None,
        publish_local: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        route = self._routing_directory.require(topic_uri, epoch=epoch)
        expected_epoch = int(route.epoch)
        if route.coordinator_address == self._local_address():
            local_result = publish_local(
                topic_uri=route.topic_uri,
                event_group_id=event_group_id,
                payload=payload,
                tags=tags,
                seq=seq,
                epoch=expected_epoch,
            )
            local_result["mode"] = "local"
            return local_result
        return self.build_forward_topic_event_intent(
            coordinator_address=route.coordinator_address,
            topic_uri=route.topic_uri,
            epoch=expected_epoch,
            event_group_id=event_group_id,
            payload=payload,
            tags=tags,
            seq=seq,
        )

    def build_forward_topic_event_intent(
        self,
        *,
        coordinator_address: str,
        topic_uri: str,
        epoch: int,
        event_group_id: str,
        payload: Any,
        tags: dict[str, str] | None,
        seq: int | None,
    ) -> dict[str, Any]:
        return {
            "mode": "forward_topic_event",
            "coordinator_address": _normalize_non_empty(
                coordinator_address,
                field_name="coordinator_address",
            ),
            "topic_uri": _normalize_non_empty(topic_uri, field_name="topic_uri"),
            "epoch": int(epoch),
            "event_group_id": _normalize_non_empty(
                event_group_id,
                field_name="event_group_id",
            ),
            "payload": payload,
            "tags": dict(tags or {}),
            "seq": seq,
        }


__all__ = ["TopicEventDispatch"]
