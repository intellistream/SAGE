from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock

from sage.runtime.flownet.runtime.topics.normalization import (
    _normalize_non_empty,
    _normalize_non_negative_int,
    _normalize_topic_uri,
)


@dataclass
class SubscriberEventGroupProgress:
    event_group_id: str
    request_done_notified: bool = False
    request_done_status: str | None = None
    final_seq: int | None = None
    expected_total_events: int | None = None
    drained_seq: int = 0
    subscriber_done_emitted: bool = False
    updated_at: float = field(default_factory=time.time)


@dataclass
class LocalSubscriberState:
    topic_uri: str
    epoch: int
    subscriber_id: str
    event_group_progress: dict[str, SubscriberEventGroupProgress] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)


class TopicSubscriberRegistry:
    """Local subscriber-state holder keyed by (topic_uri, epoch, subscriber_id)."""

    def __init__(self, *, time_fn: Callable[[], float] | None = None):
        self._states: dict[tuple[str, int, str], LocalSubscriberState] = {}
        self._lock = Lock()
        self._time_fn = time_fn or time.time

    def get_or_create(
        self,
        *,
        topic_uri: str,
        epoch: int,
        subscriber_id: str,
    ) -> LocalSubscriberState:
        normalized_topic_uri = _normalize_topic_uri(topic_uri)
        normalized_epoch = _normalize_non_negative_int(epoch, field_name="epoch")
        normalized_subscriber_id = _normalize_non_empty(subscriber_id, field_name="subscriber_id")
        key = (normalized_topic_uri, normalized_epoch, normalized_subscriber_id)
        now = self._time_fn()
        with self._lock:
            state = self._states.get(key)
            if state is None:
                state = LocalSubscriberState(
                    topic_uri=normalized_topic_uri,
                    epoch=normalized_epoch,
                    subscriber_id=normalized_subscriber_id,
                    updated_at=now,
                )
                self._states[key] = state
            else:
                state.updated_at = now
            return state

    def get(
        self,
        *,
        topic_uri: str,
        epoch: int,
        subscriber_id: str,
    ) -> LocalSubscriberState | None:
        normalized_topic_uri = _normalize_topic_uri(topic_uri)
        normalized_epoch = _normalize_non_negative_int(epoch, field_name="epoch")
        normalized_subscriber_id = _normalize_non_empty(subscriber_id, field_name="subscriber_id")
        with self._lock:
            return self._states.get(
                (normalized_topic_uri, normalized_epoch, normalized_subscriber_id)
            )

    def gc_idle(self, *, max_idle_seconds: float) -> int:
        threshold = max(0.0, float(max_idle_seconds))
        now = self._time_fn()
        removed = 0
        with self._lock:
            for key, state in list(self._states.items()):
                if (now - state.updated_at) <= threshold:
                    continue
                if state.event_group_progress:
                    continue
                self._states.pop(key, None)
                removed += 1
        return removed


__all__ = [
    "SubscriberEventGroupProgress",
    "LocalSubscriberState",
    "TopicSubscriberRegistry",
]
