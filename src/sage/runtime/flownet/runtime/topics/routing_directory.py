from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_models import FlowProgramRef
from sage.runtime.flownet.runtime.topics.normalization import (
    _normalize_non_empty,
    _normalize_non_negative_int,
    _normalize_topic_uri,
)


@dataclass(frozen=True)
class TopicRouteView:
    topic_uri: str
    coordinator_address: str
    epoch: int


@dataclass(frozen=True)
class FlowProgramRouteView:
    flow_program_ref: FlowProgramRef
    owner_address: str


@dataclass(frozen=True)
class TopicSwitchWindowView:
    topic_uri: str
    old_epoch: int
    new_epoch: int
    old_version_admission_cutoff_s: float
    new_version_first_admission_s: float | None
    new_version_first_admission_event_group_id: str | None
    old_version_last_completion_s: float | None
    old_version_last_completion_event_group_id: str | None
    w_switch_s: float | None
    admission_gap_s: float | None
    overlap_s: float | None
    missing_markers: tuple[str, ...]
    anomalies: tuple[str, ...]
    reason: str | None
    complete: bool


@dataclass
class _TopicSwitchWindowState:
    topic_uri: str
    old_epoch: int
    new_epoch: int
    old_version_admission_cutoff_s: float
    new_version_first_admission_s: float | None = None
    new_version_first_admission_event_group_id: str | None = None
    old_version_last_completion_s: float | None = None
    old_version_last_completion_event_group_id: str | None = None


class TopicRoutingDirectory:
    """
    URI routing view only.

    This directory holds topic coordinator owner snapshots (address + epoch)
    and does not execute coordinator request logic.
    """

    def __init__(self, *, time_fn: Callable[[], float] | None = None):
        self._routes: dict[tuple[str, int], TopicRouteView] = {}
        self._latest_epoch_by_topic: dict[str, int] = {}
        self._latest_switch_window_by_topic: dict[str, _TopicSwitchWindowState] = {}
        self._time_fn = time_fn or time.time
        self._lock = Lock()

    def upsert_route(
        self,
        *,
        topic_uri: str,
        coordinator_address: str,
        epoch: int,
    ) -> TopicRouteView:
        route = TopicRouteView(
            topic_uri=_normalize_topic_uri(topic_uri),
            coordinator_address=_normalize_non_empty(
                coordinator_address,
                field_name="coordinator_address",
            ),
            epoch=_normalize_non_negative_int(epoch, field_name="epoch"),
        )
        switch_cutoff_s = _coerce_observed_at_s(
            self._time_fn(),
            field_name="switch_cutoff_s",
        )
        with self._lock:
            key = (route.topic_uri, route.epoch)
            self._routes[key] = route
            previous_latest = self._latest_epoch_by_topic.get(route.topic_uri)
            if previous_latest is None or route.epoch >= previous_latest:
                self._latest_epoch_by_topic[route.topic_uri] = route.epoch
            if previous_latest is not None and route.epoch > previous_latest:
                self._latest_switch_window_by_topic[route.topic_uri] = _TopicSwitchWindowState(
                    topic_uri=route.topic_uri,
                    old_epoch=previous_latest,
                    new_epoch=route.epoch,
                    old_version_admission_cutoff_s=switch_cutoff_s,
                )
        return route

    def resolve(
        self,
        topic_uri: str,
        *,
        epoch: int | None = None,
    ) -> TopicRouteView | None:
        normalized_topic_uri = _normalize_topic_uri(topic_uri)
        normalized_epoch: int | None = None
        if epoch is not None:
            normalized_epoch = _normalize_non_negative_int(epoch, field_name="epoch")
        with self._lock:
            if normalized_epoch is None:
                latest_epoch = self._latest_epoch_by_topic.get(normalized_topic_uri)
                if latest_epoch is None:
                    return None
                normalized_epoch = latest_epoch
            return self._routes.get((normalized_topic_uri, normalized_epoch))

    def require(
        self,
        topic_uri: str,
        *,
        epoch: int | None = None,
    ) -> TopicRouteView:
        route = self.resolve(topic_uri, epoch=epoch)
        if route is None:
            normalized_topic_uri = _normalize_topic_uri(topic_uri)
            if epoch is None:
                raise RuntimeError(f"topic_route_not_found:{normalized_topic_uri}")
            normalized_epoch = _normalize_non_negative_int(epoch, field_name="epoch")
            raise RuntimeError(
                f"topic_epoch_route_not_found:{normalized_topic_uri}@{normalized_epoch}",
            )
        return route

    def observe_admission(
        self,
        *,
        topic_uri: str,
        epoch: int,
        event_group_id: str,
        observed_at_s: float | None = None,
    ) -> TopicSwitchWindowView | None:
        normalized_topic_uri = _normalize_topic_uri(topic_uri)
        normalized_epoch = _normalize_non_negative_int(epoch, field_name="epoch")
        normalized_event_group_id = _normalize_non_empty(
            event_group_id,
            field_name="event_group_id",
        )
        normalized_observed_at_s = _coerce_observed_at_s(
            observed_at_s if observed_at_s is not None else self._time_fn(),
            field_name="observed_at_s",
        )
        with self._lock:
            switch_state = self._latest_switch_window_by_topic.get(normalized_topic_uri)
            if switch_state is None:
                return None
            if normalized_epoch == switch_state.new_epoch:
                previous = switch_state.new_version_first_admission_s
                if previous is None or normalized_observed_at_s < previous:
                    switch_state.new_version_first_admission_s = normalized_observed_at_s
                    switch_state.new_version_first_admission_event_group_id = (
                        normalized_event_group_id
                    )
            return _build_switch_window_view(switch_state)

    def observe_completion(
        self,
        *,
        topic_uri: str,
        epoch: int,
        event_group_id: str,
        observed_at_s: float | None = None,
    ) -> TopicSwitchWindowView | None:
        normalized_topic_uri = _normalize_topic_uri(topic_uri)
        normalized_epoch = _normalize_non_negative_int(epoch, field_name="epoch")
        normalized_event_group_id = _normalize_non_empty(
            event_group_id,
            field_name="event_group_id",
        )
        normalized_observed_at_s = _coerce_observed_at_s(
            observed_at_s if observed_at_s is not None else self._time_fn(),
            field_name="observed_at_s",
        )
        with self._lock:
            switch_state = self._latest_switch_window_by_topic.get(normalized_topic_uri)
            if switch_state is None:
                return None
            if normalized_epoch == switch_state.old_epoch:
                cutoff_s = switch_state.old_version_admission_cutoff_s
                if normalized_observed_at_s >= cutoff_s:
                    previous = switch_state.old_version_last_completion_s
                    if previous is None or normalized_observed_at_s > previous:
                        switch_state.old_version_last_completion_s = normalized_observed_at_s
                        switch_state.old_version_last_completion_event_group_id = (
                            normalized_event_group_id
                        )
            return _build_switch_window_view(switch_state)

    def switch_window(self, topic_uri: str) -> TopicSwitchWindowView | None:
        normalized_topic_uri = _normalize_topic_uri(topic_uri)
        with self._lock:
            switch_state = self._latest_switch_window_by_topic.get(normalized_topic_uri)
            if switch_state is None:
                return None
            return _build_switch_window_view(switch_state)


class FlowProgramRoutingDirectory:
    """Flow program owner route view keyed by canonical FlowProgramRef."""

    def __init__(self):
        self._routes: dict[FlowProgramRef, FlowProgramRouteView] = {}
        self._lock = Lock()

    def upsert_route(
        self,
        *,
        flow_program_uri: str,
        flow_program_rev: str,
        owner_address: str,
    ) -> FlowProgramRouteView:
        flow_program_ref = _normalize_program_ref(
            flow_program_uri=flow_program_uri,
            flow_program_rev=flow_program_rev,
        )
        route = FlowProgramRouteView(
            flow_program_ref=flow_program_ref,
            owner_address=_normalize_non_empty(
                owner_address,
                field_name="owner_address",
            ),
        )
        with self._lock:
            self._routes[flow_program_ref] = route
        return route

    def resolve(self, flow_program_ref: FlowProgramRef) -> FlowProgramRouteView | None:
        normalized_ref = _coerce_flow_program_ref(flow_program_ref)
        with self._lock:
            return self._routes.get(normalized_ref)

    def require(self, flow_program_ref: FlowProgramRef) -> FlowProgramRouteView:
        route = self.resolve(flow_program_ref)
        if route is None:
            normalized_ref = _coerce_flow_program_ref(flow_program_ref)
            raise RuntimeError(
                "flow_program_route_not_found:"
                f"{normalized_ref.program_uri}@{normalized_ref.program_rev}",
            )
        return route


def _normalize_program_ref(
    *,
    flow_program_uri: str,
    flow_program_rev: str,
) -> FlowProgramRef:
    return FlowProgramRef(
        program_uri=_normalize_non_empty(
            flow_program_uri,
            field_name="flow_program_uri",
        ),
        program_rev=_normalize_non_empty(
            flow_program_rev,
            field_name="flow_program_rev",
        ),
    )


def _coerce_flow_program_ref(raw: Any) -> FlowProgramRef:
    if not isinstance(raw, FlowProgramRef):
        raise TypeError("flow_program_ref must be FlowProgramRef.")
    return _normalize_program_ref(
        flow_program_uri=raw.program_uri,
        flow_program_rev=raw.program_rev,
    )


def _coerce_observed_at_s(raw_value: Any, *, field_name: str) -> float:
    observed_at_s = float(raw_value)
    if observed_at_s < 0:
        raise ValueError(f"{field_name} must be >= 0.")
    return observed_at_s


def _build_switch_window_view(state: _TopicSwitchWindowState) -> TopicSwitchWindowView:
    missing_markers: list[str] = []
    anomalies: list[str] = []

    new_first = state.new_version_first_admission_s
    old_last = state.old_version_last_completion_s
    cutoff = state.old_version_admission_cutoff_s

    if new_first is None:
        missing_markers.append("new_version_first_admission_missing")
    if old_last is None:
        missing_markers.append("old_version_last_completion_missing")
    if old_last is not None and old_last < cutoff:
        anomalies.append("old_version_last_completion_before_cutoff")

    w_switch_s = (old_last - cutoff) if old_last is not None else None
    admission_gap_s = (new_first - cutoff) if new_first is not None else None
    overlap_s = (old_last - new_first) if (old_last is not None and new_first is not None) else None

    complete = not missing_markers and not anomalies
    reason: str | None = None
    if missing_markers:
        reason = "missing_markers:" + ",".join(missing_markers)
    elif anomalies:
        reason = "inconsistent_markers:" + ",".join(anomalies)

    return TopicSwitchWindowView(
        topic_uri=state.topic_uri,
        old_epoch=state.old_epoch,
        new_epoch=state.new_epoch,
        old_version_admission_cutoff_s=cutoff,
        new_version_first_admission_s=new_first,
        new_version_first_admission_event_group_id=state.new_version_first_admission_event_group_id,
        old_version_last_completion_s=old_last,
        old_version_last_completion_event_group_id=state.old_version_last_completion_event_group_id,
        w_switch_s=w_switch_s,
        admission_gap_s=admission_gap_s,
        overlap_s=overlap_s,
        missing_markers=tuple(missing_markers),
        anomalies=tuple(anomalies),
        reason=reason,
        complete=complete,
    )


__all__ = [
    "TopicRouteView",
    "TopicRoutingDirectory",
    "TopicSwitchWindowView",
    "FlowProgramRouteView",
    "FlowProgramRoutingDirectory",
]
