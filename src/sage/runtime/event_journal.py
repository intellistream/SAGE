"""Ordered replayable delivery records on SAGE atomic state.

This journal borrows its store. Durability requires a persistent backend.
Authorization and transport belong to callers; an identifier is not a capability.
Records are retained losslessly per stream, with no implicit TTL or truncation.
Capacity/retention must be configured outside this primitive before large-scale
use: the current state backend rewrites a stream snapshot on each append.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


def _name(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("event_identifier_must_be_nonempty_and_trimmed")
    return value


def _snapshot(value):
    return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))


@dataclass(frozen=True)
class PreparedEventAppend:
    """Pure mutation for this journal's store.update_many transaction.

    Preparing does not publish or acknowledge an event. Use stable event IDs
    when composing with retryable destination/work mutations in the same store.
    """

    slot: tuple[str, str, str]
    transform: Callable[[Any], Any]


class EventJournal:
    def __init__(self, store, *, namespace: str):
        self._store = store
        self.namespace = _name(namespace)

    def _slot(self, stream_id):
        return ("sage-event-journal-v1", self.namespace, _name(stream_id))

    @staticmethod
    def _record(value):
        if value is None:
            return {"version": 1, "events": [], "closed": False}
        if value.get("version") != 1:
            raise ValueError("unsupported_event_journal_version")
        return value

    def prepare_append(self, stream_id, *, event_id, payload, terminal=False):
        """Capture detached input and assign sequence inside the transaction.

        Duplicate IDs with identical content return their original sequence,
        even after closure. Changed content conflicts. A terminal event and
        closure commit together; later new events are rejected.
        """
        slot = self._slot(stream_id)
        event_id = _name(event_id)
        if type(terminal) is not bool:
            raise TypeError("event_terminal_must_be_bool")
        payload = _snapshot(payload)
        encoded_payload = json.dumps(payload, allow_nan=False, sort_keys=True)

        def apply(old):
            record = self._record(old)
            for event in record["events"]:
                if event["id"] == event_id:
                    if (json.dumps(event["payload"], allow_nan=False, sort_keys=True) != encoded_payload
                            or event["terminal"] != terminal):
                        raise ValueError("event_append_conflict")
                    return record
            if record["closed"]:
                raise ValueError("event_stream_closed")
            record["events"].append({"sequence": len(record["events"]) + 1,
                                     "id": event_id, "payload": _snapshot(payload),
                                     "terminal": terminal})
            record["closed"] = terminal
            return record

        return PreparedEventAppend(slot, apply)

    def append(self, stream_id, *, event_id, payload, terminal=False):
        prepared = self.prepare_append(stream_id, event_id=event_id, payload=payload, terminal=terminal)
        record = self._store.update(prepared.slot, prepared.transform)
        return next(event for event in record["events"] if event["id"] == event_id)

    def read(self, stream_id, *, after=0, limit=100):
        """Return a detached page and cursor from one consistent snapshot.

        Sequence zero is before the first event. A future cursor is rejected,
        never silently treated as completed. Missing streams are empty/open so
        consumers may connect before a producer. `closed` describes the stream;
        `caught_up` distinguishes a partial page from reaching its current tail.
        Consumers only finish when both flags are true.
        """
        if type(after) is not int or after < 0 or type(limit) is not int or limit <= 0:
            raise ValueError("invalid_event_cursor_or_limit")
        record = self._record(self._store.peek(self._slot(stream_id)))
        tail = len(record["events"])
        if after > tail:
            raise ValueError("event_cursor_ahead")
        events = record["events"][after:after + limit]
        cursor = events[-1]["sequence"] if events else after
        return _snapshot({"events": events, "cursor": cursor, "tail": tail,
                          "closed": record["closed"], "caught_up": cursor == tail})
