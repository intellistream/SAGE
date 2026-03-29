from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sage.runtime.flownet.runtime.topics.normalization import (
    _normalize_non_empty,
    _normalize_non_negative_int,
)
from sage.runtime.flownet.runtime.topics.subscriber_registry import (
    LocalSubscriberState,
    SubscriberEventGroupProgress,
)


class SubscriberProgressManager:
    """Subscriber-side request_done/drain convergence keyed by event_group_id."""

    def __init__(
        self,
        *,
        time_fn: Callable[[], float],
        on_subscriber_done: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._time_fn = time_fn
        self._on_subscriber_done = on_subscriber_done

    def normalize_event_group_id(self, event_group_id: str) -> str:
        return _normalize_non_empty(event_group_id, field_name="event_group_id")

    def normalize_subscriber_id(self, subscriber_id: str) -> str:
        return _normalize_non_empty(subscriber_id, field_name="subscriber_id")

    def progress(
        self,
        *,
        state: LocalSubscriberState,
        event_group_id: str,
    ) -> SubscriberEventGroupProgress:
        normalized_event_group_id = self.normalize_event_group_id(event_group_id)
        progress = state.event_group_progress.get(normalized_event_group_id)
        if progress is None:
            progress = SubscriberEventGroupProgress(event_group_id=normalized_event_group_id)
            state.event_group_progress[normalized_event_group_id] = progress
        return progress

    def snapshot(
        self,
        *,
        state: LocalSubscriberState,
        event_group_id: str,
    ) -> dict[str, Any] | None:
        normalized_event_group_id = self.normalize_event_group_id(event_group_id)
        progress = state.event_group_progress.get(normalized_event_group_id)
        if progress is None:
            return None
        return self._snapshot_dict(state=state, progress=progress)

    def apply_request_done_notify(
        self,
        *,
        state: LocalSubscriberState,
        event_group_id: str,
        status: str,
        final_seq: int | None,
        expected_total_events: int | None,
    ) -> dict[str, Any]:
        progress = self.progress(state=state, event_group_id=event_group_id)
        progress.request_done_notified = True
        progress.request_done_status = _normalize_non_empty(status, field_name="status")
        if final_seq is not None:
            normalized_final_seq = _normalize_non_negative_int(final_seq, field_name="final_seq")
            if progress.final_seq is None or normalized_final_seq > progress.final_seq:
                progress.final_seq = normalized_final_seq
        if expected_total_events is not None:
            progress.expected_total_events = _normalize_non_negative_int(
                expected_total_events,
                field_name="expected_total_events",
            )
        progress.updated_at = self._time_fn()
        state.updated_at = progress.updated_at
        subscriber_done = self._maybe_subscriber_done(state=state, progress=progress)
        snapshot = self._snapshot_dict(state=state, progress=progress)
        snapshot["subscriber_done"] = subscriber_done
        return snapshot

    def apply_drain_update(
        self,
        *,
        state: LocalSubscriberState,
        event_group_id: str,
        drained_seq: int,
    ) -> dict[str, Any]:
        progress = self.progress(state=state, event_group_id=event_group_id)
        normalized_drained_seq = _normalize_non_negative_int(drained_seq, field_name="drained_seq")
        if normalized_drained_seq > progress.drained_seq:
            progress.drained_seq = normalized_drained_seq
        progress.updated_at = self._time_fn()
        state.updated_at = progress.updated_at
        subscriber_done = self._maybe_subscriber_done(state=state, progress=progress)
        snapshot = self._snapshot_dict(state=state, progress=progress)
        snapshot["subscriber_done"] = subscriber_done
        return snapshot

    def _snapshot_dict(
        self,
        *,
        state: LocalSubscriberState,
        progress: SubscriberEventGroupProgress,
    ) -> dict[str, Any]:
        return {
            "topic_uri": state.topic_uri,
            "epoch": state.epoch,
            "subscriber_id": state.subscriber_id,
            "event_group_id": progress.event_group_id,
            "request_done_notified": progress.request_done_notified,
            "status": progress.request_done_status,
            "final_seq": progress.final_seq,
            "expected_total_events": progress.expected_total_events,
            "drained_seq": progress.drained_seq,
            "subscriber_done_emitted": progress.subscriber_done_emitted,
        }

    def _maybe_subscriber_done(
        self,
        *,
        state: LocalSubscriberState,
        progress: SubscriberEventGroupProgress,
    ) -> dict[str, Any] | None:
        if progress.subscriber_done_emitted:
            return None
        if not progress.request_done_notified:
            return None
        required_drained_seq = self._resolve_required_drained_seq(progress)
        if progress.drained_seq < required_drained_seq:
            return None
        progress.subscriber_done_emitted = True
        subscriber_done = {
            "topic_uri": state.topic_uri,
            "epoch": state.epoch,
            "event_group_id": progress.event_group_id,
            "subscriber_id": state.subscriber_id,
            "drained_seq": progress.drained_seq,
            "status": progress.request_done_status or "completed",
            "final_seq": progress.final_seq,
            "expected_total_events": progress.expected_total_events,
        }
        if callable(self._on_subscriber_done):
            self._on_subscriber_done(dict(subscriber_done))
        return subscriber_done

    @staticmethod
    def _resolve_required_drained_seq(progress: SubscriberEventGroupProgress) -> int:
        if progress.expected_total_events is not None:
            return int(progress.expected_total_events)
        if progress.final_seq is not None:
            return int(progress.final_seq)
        return 0


__all__ = ["SubscriberProgressManager"]
