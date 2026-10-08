from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from sage.runtime.flownet.runtime.topics.normalization import (
    _normalize_non_empty,
    _normalize_topic_uri,
)


@dataclass(frozen=True)
class FlowProcessRecord:
    flow_process_uri: str
    flow_program_uri: str
    flow_program_rev: str
    in_topic_uri: str
    out_topic_uri: str
    metadata: dict[str, Any] = field(default_factory=dict)


class FlowProcessCatalog:
    """
    URI/meta view only.

    This catalog stores logical flow-process registrations and does not own
    request convergence ledgers.
    """

    def __init__(self):
        self._records: dict[str, FlowProcessRecord] = {}
        self._lock = Lock()

    def register(
        self,
        *,
        flow_process_uri: str,
        flow_program_uri: str,
        flow_program_rev: str,
        in_topic_uri: str,
        out_topic_uri: str,
        metadata: dict[str, Any] | None = None,
    ) -> FlowProcessRecord:
        record = FlowProcessRecord(
            flow_process_uri=_normalize_non_empty(flow_process_uri, field_name="flow_process_uri"),
            flow_program_uri=_normalize_non_empty(flow_program_uri, field_name="flow_program_uri"),
            flow_program_rev=_normalize_non_empty(flow_program_rev, field_name="flow_program_rev"),
            in_topic_uri=_normalize_topic_uri(in_topic_uri),
            out_topic_uri=_normalize_topic_uri(out_topic_uri),
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._records[record.flow_process_uri] = record
        return record

    def get(self, flow_process_uri: str) -> FlowProcessRecord | None:
        normalized_uri = _normalize_non_empty(flow_process_uri, field_name="flow_process_uri")
        with self._lock:
            return self._records.get(normalized_uri)

    def list(self) -> list[FlowProcessRecord]:
        with self._lock:
            records = list(self._records.values())
        records.sort(key=lambda item: item.flow_process_uri)
        return records

    def delete(self, flow_process_uri: str) -> bool:
        normalized_uri = _normalize_non_empty(flow_process_uri, field_name="flow_process_uri")
        with self._lock:
            return self._records.pop(normalized_uri, None) is not None


__all__ = ["FlowProcessRecord", "FlowProcessCatalog"]
