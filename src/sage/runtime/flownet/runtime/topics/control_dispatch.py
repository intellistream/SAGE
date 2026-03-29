from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sage.runtime.flownet.runtime.topics.normalization import (
    _normalize_non_empty,
    _normalize_non_negative_int,
)
from sage.runtime.flownet.runtime.topics.routing_directory import TopicRoutingDirectory


class TopicControlDispatch:
    """Control-plane done signal routing helper."""

    def __init__(
        self,
        *,
        routing_directory: TopicRoutingDirectory,
        local_address: Callable[[], str],
    ) -> None:
        self._routing_directory = routing_directory
        self._local_address = local_address

    def event_chain_done_or_forward(
        self,
        *,
        topic_uri: str,
        event_group_id: str,
        delta: int,
        epoch: int | None,
        apply_local: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        route = self._routing_directory.require(topic_uri, epoch=epoch)
        expected_epoch = int(route.epoch)
        if route.coordinator_address == self._local_address():
            local_result = apply_local(
                topic_uri=route.topic_uri,
                event_group_id=event_group_id,
                delta=delta,
                epoch=expected_epoch,
            )
            local_result["mode"] = "local"
            return local_result
        return self.build_forward_event_chain_done_intent(
            coordinator_address=route.coordinator_address,
            topic_uri=route.topic_uri,
            epoch=expected_epoch,
            event_group_id=event_group_id,
            delta=delta,
        )

    def producer_done_or_forward(
        self,
        *,
        topic_uri: str,
        event_group_id: str,
        final_seq: int | None,
        expected_total_events: int | None,
        epoch: int | None,
        apply_local: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        route = self._routing_directory.require(topic_uri, epoch=epoch)
        expected_epoch = int(route.epoch)
        if route.coordinator_address == self._local_address():
            local_result = apply_local(
                topic_uri=route.topic_uri,
                event_group_id=event_group_id,
                final_seq=final_seq,
                expected_total_events=expected_total_events,
                epoch=expected_epoch,
            )
            local_result["mode"] = "local"
            return local_result
        return self.build_forward_producer_done_intent(
            coordinator_address=route.coordinator_address,
            topic_uri=route.topic_uri,
            epoch=expected_epoch,
            event_group_id=event_group_id,
            final_seq=final_seq,
            expected_total_events=expected_total_events,
        )

    def request_outcome_or_forward(
        self,
        *,
        topic_uri: str,
        event_group_id: str,
        outcome_status: str,
        outcome_error_type: str | None,
        outcome_error_message: str | None,
        outcome_error_stage: str | None,
        outcome_metadata: dict[str, Any] | None,
        epoch: int | None,
        apply_local: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        route = self._routing_directory.require(topic_uri, epoch=epoch)
        expected_epoch = int(route.epoch)
        if route.coordinator_address == self._local_address():
            local_result = apply_local(
                topic_uri=route.topic_uri,
                event_group_id=event_group_id,
                outcome_status=outcome_status,
                outcome_error_type=outcome_error_type,
                outcome_error_message=outcome_error_message,
                outcome_error_stage=outcome_error_stage,
                outcome_metadata=outcome_metadata,
                epoch=expected_epoch,
            )
            local_result["mode"] = "local"
            return local_result
        return self.build_forward_request_outcome_intent(
            coordinator_address=route.coordinator_address,
            topic_uri=route.topic_uri,
            epoch=expected_epoch,
            event_group_id=event_group_id,
            outcome_status=outcome_status,
            outcome_error_type=outcome_error_type,
            outcome_error_message=outcome_error_message,
            outcome_error_stage=outcome_error_stage,
            outcome_metadata=outcome_metadata,
        )

    def build_forward_event_chain_done_intent(
        self,
        *,
        coordinator_address: str,
        topic_uri: str,
        epoch: int,
        event_group_id: str,
        delta: int,
    ) -> dict[str, Any]:
        return {
            "mode": "forward_event_chain_done",
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
            "delta": int(delta),
        }

    def build_forward_producer_done_intent(
        self,
        *,
        coordinator_address: str,
        topic_uri: str,
        epoch: int,
        event_group_id: str,
        final_seq: int | None,
        expected_total_events: int | None,
    ) -> dict[str, Any]:
        intent: dict[str, Any] = {
            "mode": "forward_producer_done",
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
        }
        if final_seq is not None:
            intent["final_seq"] = _normalize_non_negative_int(final_seq, field_name="final_seq")
        if expected_total_events is not None:
            intent["expected_total_events"] = _normalize_non_negative_int(
                expected_total_events,
                field_name="expected_total_events",
            )
        return intent

    def build_forward_request_outcome_intent(
        self,
        *,
        coordinator_address: str,
        topic_uri: str,
        epoch: int,
        event_group_id: str,
        outcome_status: str,
        outcome_error_type: str | None,
        outcome_error_message: str | None,
        outcome_error_stage: str | None,
        outcome_metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        intent: dict[str, Any] = {
            "mode": "forward_request_outcome",
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
            "outcome_status": _normalize_non_empty(
                outcome_status,
                field_name="outcome_status",
            )
            .strip()
            .lower(),
        }
        if outcome_error_type is not None:
            intent["outcome_error_type"] = _normalize_non_empty(
                outcome_error_type,
                field_name="outcome_error_type",
            )
        if outcome_error_message is not None:
            intent["outcome_error_message"] = _normalize_non_empty(
                outcome_error_message,
                field_name="outcome_error_message",
            )
        if outcome_error_stage is not None:
            intent["outcome_error_stage"] = _normalize_non_empty(
                outcome_error_stage,
                field_name="outcome_error_stage",
            )
        if outcome_metadata is not None:
            intent["outcome_metadata"] = {
                str(key): value for key, value in dict(outcome_metadata).items()
            }
        return intent


__all__ = ["TopicControlDispatch"]
