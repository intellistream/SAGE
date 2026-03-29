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
class EventGroupLedger:
    event_group_id: str
    admission_epoch: int | None = None
    first_admitted_at: float | None = None
    completed_at: float | None = None
    event_chain_pending: int = 0
    producer_done: bool = False
    emitted_event_count: int = 0
    final_seq: int | None = None
    expected_total_events_hint: int | None = None
    request_done_emitted: bool = False
    outcome_status: str = "pending"
    outcome_error_type: str | None = None
    outcome_error_message: str | None = None
    outcome_error_stage: str | None = None
    outcome_metadata: dict[str, object] = field(default_factory=dict)
    observed_flow_program_revs: set[str] = field(default_factory=set)
    updated_at: float = field(default_factory=time.time)


@dataclass
class CoordinatorTopicState:
    topic_uri: str
    epoch: int
    consuming_flow_process_uris: set[str] = field(default_factory=set)
    producing_flow_process_uris: set[str] = field(default_factory=set)
    subscriber_ids: set[str] = field(default_factory=set)
    subscriber_addresses: dict[str, str] = field(default_factory=dict)
    event_group_ledgers: dict[str, EventGroupLedger] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)


class TopicCoordinatorRegistry:
    """
    Local coordinator-state holder.

    State is lazy and keyed by (topic_uri, epoch).
    """

    def __init__(self, *, time_fn: Callable[[], float] | None = None):
        self._states: dict[tuple[str, int], CoordinatorTopicState] = {}
        self._lock = Lock()
        self._time_fn = time_fn or time.time

    def get_or_create(self, topic_uri: str, epoch: int) -> CoordinatorTopicState:
        normalized_topic_uri = _normalize_topic_uri(topic_uri)
        normalized_epoch = _normalize_non_negative_int(epoch, field_name="epoch")
        key = (normalized_topic_uri, normalized_epoch)
        now = self._time_fn()
        with self._lock:
            state = self._states.get(key)
            if state is None:
                state = CoordinatorTopicState(
                    topic_uri=normalized_topic_uri,
                    epoch=normalized_epoch,
                    updated_at=now,
                )
                self._states[key] = state
            else:
                state.updated_at = now
            return state

    def get(self, topic_uri: str, epoch: int) -> CoordinatorTopicState | None:
        normalized_topic_uri = _normalize_topic_uri(topic_uri)
        normalized_epoch = _normalize_non_negative_int(epoch, field_name="epoch")
        with self._lock:
            return self._states.get((normalized_topic_uri, normalized_epoch))

    def discard_flow_process_uri(
        self,
        *,
        topic_uri: str,
        flow_process_uri: str,
    ) -> bool:
        normalized_topic_uri = _normalize_topic_uri(topic_uri)
        normalized_flow_process_uri = _normalize_non_empty(
            flow_process_uri,
            field_name="flow_process_uri",
        )
        now = self._time_fn()
        removed = False
        with self._lock:
            for state in self._states.values():
                if state.topic_uri != normalized_topic_uri:
                    continue
                prev_consuming_count = len(state.consuming_flow_process_uris)
                prev_producing_count = len(state.producing_flow_process_uris)
                state.consuming_flow_process_uris.discard(normalized_flow_process_uri)
                state.producing_flow_process_uris.discard(normalized_flow_process_uri)
                if (
                    len(state.consuming_flow_process_uris) != prev_consuming_count
                    or len(state.producing_flow_process_uris) != prev_producing_count
                ):
                    state.updated_at = now
                    removed = True
        return removed

    def gc_idle(self, *, max_idle_seconds: float) -> int:
        threshold = max(0.0, float(max_idle_seconds))
        now = self._time_fn()
        removed = 0
        with self._lock:
            for key, state in list(self._states.items()):
                self._prune_finished_event_group_ledgers(
                    state=state,
                    now=now,
                    threshold=threshold,
                )
                if self._has_unfinished_event_group(state):
                    continue
                if state.event_group_ledgers:
                    # keep recently-finished ledgers for observability until TTL.
                    continue
                if (now - state.updated_at) <= threshold:
                    continue
                if state.consuming_flow_process_uris:
                    continue
                if state.producing_flow_process_uris:
                    continue
                if state.subscriber_ids:
                    continue
                if state.subscriber_addresses:
                    continue
                self._states.pop(key, None)
                removed += 1
        return removed

    def observability_snapshot(self) -> dict[str, object]:
        now = self._time_fn()
        with self._lock:
            states = list(self._states.values())

        queue_rows: list[dict[str, object]] = []
        tracked_requests = 0
        completed_requests = 0
        active_requests = 0
        pending_event_chains = 0
        active_delay_samples_ms: list[float] = []

        for state in states:
            state_tracked = 0
            state_completed = 0
            state_active = 0
            state_pending_event_chains = 0
            state_delay_samples_ms: list[float] = []

            for ledger in state.event_group_ledgers.values():
                state_tracked += 1
                tracked_requests += 1
                state_pending_event_chains += max(0, int(ledger.event_chain_pending))
                pending_event_chains += max(0, int(ledger.event_chain_pending))

                if self._is_finished_event_group_ledger(ledger):
                    state_completed += 1
                    completed_requests += 1
                    continue

                state_active += 1
                active_requests += 1
                admitted_at = ledger.first_admitted_at or ledger.updated_at
                delay_ms = max(0.0, float(now - admitted_at) * 1000.0)
                state_delay_samples_ms.append(delay_ms)
                active_delay_samples_ms.append(delay_ms)

            if state_tracked <= 0:
                continue

            queue_rows.append(
                {
                    "queue_id": f"{state.topic_uri}@{state.epoch}",
                    "topic_uri": state.topic_uri,
                    "epoch": int(state.epoch),
                    "tracked_requests": state_tracked,
                    "completed_requests": state_completed,
                    "active_requests": state_active,
                    "pending_event_chains": state_pending_event_chains,
                    "queue_delay_ms": (
                        round(max(state_delay_samples_ms), 3) if state_delay_samples_ms else 0.0
                    ),
                }
            )

        queue_rows.sort(key=lambda item: (str(item["topic_uri"]), int(item["epoch"])))
        avg_delay_ms = (
            sum(active_delay_samples_ms) / float(len(active_delay_samples_ms))
            if active_delay_samples_ms
            else 0.0
        )
        max_delay_ms = max(active_delay_samples_ms) if active_delay_samples_ms else 0.0

        return {
            "generated_at_ms": int(now * 1000.0),
            "tracked_requests": tracked_requests,
            "completed_requests": completed_requests,
            "active_requests": active_requests,
            "pending_event_chains": pending_event_chains,
            "queue_delay_ms": {
                "avg": round(avg_delay_ms, 3),
                "max": round(max_delay_ms, 3),
            },
            "queues": queue_rows,
        }

    @staticmethod
    def _has_unfinished_event_group(state: CoordinatorTopicState) -> bool:
        for ledger in state.event_group_ledgers.values():
            if not TopicCoordinatorRegistry._is_finished_event_group_ledger(ledger):
                return True
        return False

    @staticmethod
    def _is_finished_event_group_ledger(ledger: EventGroupLedger) -> bool:
        if not ledger.request_done_emitted:
            return False
        if not ledger.producer_done:
            return False
        if int(ledger.event_chain_pending) != 0:
            return False
        return True

    @staticmethod
    def _prune_finished_event_group_ledgers(
        *,
        state: CoordinatorTopicState,
        now: float,
        threshold: float,
    ) -> None:
        for event_group_id, ledger in list(state.event_group_ledgers.items()):
            if not TopicCoordinatorRegistry._is_finished_event_group_ledger(ledger):
                continue
            if (now - ledger.updated_at) <= threshold:
                continue
            state.event_group_ledgers.pop(event_group_id, None)


__all__ = [
    "EventGroupLedger",
    "CoordinatorTopicState",
    "TopicCoordinatorRegistry",
]
