from __future__ import annotations

from collections.abc import Callable, Mapping
from threading import RLock
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_models import FlowProgramRef


class FlowProgramCache:
    """Runtime flow-program cache with optional pull callback on cache miss."""

    def __init__(
        self,
        *,
        pull_program: Callable[[FlowProgramRef], Any | None] | None = None,
    ) -> None:
        self._programs: dict[FlowProgramRef, Any] = {}
        self._pull_program = pull_program
        self._lock = RLock()

    def register(self, *, flow_program_ref: FlowProgramRef, flow_program: Any) -> None:
        normalized_ref = _normalize_program_ref(flow_program_ref)
        if flow_program is None:
            raise TypeError("flow_program must not be None.")
        with self._lock:
            existing = self._programs.get(normalized_ref)
            if existing is not None and existing is not flow_program:
                existing_hash = _resolve_definition_hash(existing)
                incoming_hash = _resolve_definition_hash(flow_program)
                if (
                    existing_hash is not None
                    and incoming_hash is not None
                    and existing_hash != incoming_hash
                ):
                    raise ValueError(
                        "flow_program_definition_hash_mismatch:"
                        f"{normalized_ref.program_uri}@{normalized_ref.program_rev}"
                    )
                return
            self._programs[normalized_ref] = flow_program

    def unregister(self, *, flow_program_ref: FlowProgramRef) -> bool:
        normalized_ref = _normalize_program_ref(flow_program_ref)
        with self._lock:
            return self._programs.pop(normalized_ref, None) is not None

    def resolve(self, *, flow_program_ref: FlowProgramRef) -> Any | None:
        normalized_ref = _normalize_program_ref(flow_program_ref)
        with self._lock:
            cached = self._programs.get(normalized_ref)
        if cached is not None:
            return cached

        if self._pull_program is None:
            return None
        pulled = self._pull_program(normalized_ref)
        if pulled is None:
            return None
        with self._lock:
            existing = self._programs.get(normalized_ref)
            if existing is not None:
                return existing
            self._programs[normalized_ref] = pulled
            return pulled


def _normalize_program_ref(flow_program_ref: FlowProgramRef) -> FlowProgramRef:
    if not isinstance(flow_program_ref, FlowProgramRef):
        raise TypeError("flow_program_ref must be FlowProgramRef.")
    program_uri = _normalize_non_empty(
        flow_program_ref.program_uri,
        field_name="flow_program_ref.program_uri",
    )
    program_rev = _normalize_non_empty(
        flow_program_ref.program_rev,
        field_name="flow_program_ref.program_rev",
    )
    return FlowProgramRef(program_uri=program_uri, program_rev=program_rev)


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _resolve_definition_hash(program: Any) -> str | None:
    metadata = getattr(program, "metadata", None)
    if isinstance(metadata, Mapping):
        value = metadata.get("definition_hash")
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    value = getattr(program, "definition_hash", None)
    normalized = str(value or "").strip()
    if normalized:
        return normalized
    return None


__all__ = ["FlowProgramCache"]
