"""Reusable, request-neutral compiled workflow plans.

The cache is deliberately explicit: callers fingerprint only structural
workflow contracts, compile an immutable artifact, and bind request state after
lookup. This prevents identities, inputs, deadlines, evidence, and cancellation
tokens from leaking into reusable plans.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from threading import Event, RLock
from time import monotonic
from typing import Any, Generic, TypeVar

PlanT = TypeVar("PlanT")
BoundT = TypeVar("BoundT")


def _canonical(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _canonical(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, (set, frozenset)):
        normalized = [_canonical(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
    raise TypeError(
        "plan fingerprint values must be JSON-like structural data; "
        f"got {type(value).__name__}"
    )


@dataclass(frozen=True, slots=True)
class PlanFingerprint:
    digest: str
    contract_json: str

    @classmethod
    def build(
        cls,
        *,
        operator_dag: Any,
        schema: Any,
        policy_version: str,
        capabilities: Any,
        retrieval_contract: Any,
        resource_class: str,
        compiler_version: str = "1",
    ) -> PlanFingerprint:
        contract = _canonical(
            {
                "operator_dag": operator_dag,
                "schema": schema,
                "policy_version": str(policy_version),
                "capabilities": capabilities,
                "retrieval_contract": retrieval_contract,
                "resource_class": str(resource_class),
                "compiler_version": str(compiler_version),
            }
        )
        contract_json = json.dumps(
            contract,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return cls(
            digest=hashlib.sha256(contract_json.encode("utf-8")).hexdigest(),
            contract_json=contract_json,
        )


@dataclass(frozen=True, slots=True)
class CompiledWorkflowPlan(Generic[PlanT]):
    fingerprint: PlanFingerprint
    artifact: PlanT
    compile_duration_ms: float


@dataclass(frozen=True, slots=True)
class PlanCacheStats:
    hits: int
    misses: int
    waits: int
    compiles: int
    compile_failures: int
    evictions: int
    entries: int
    negative_entries: int


class PlanCompileError(RuntimeError):
    """A compile failure, including a bounded negative-cache hit."""


@dataclass(slots=True)
class _Entry(Generic[PlanT]):
    plan: CompiledWorkflowPlan[PlanT] | None
    error: str | None
    expires_at: float


class CompiledPlanCache(Generic[PlanT]):
    def __init__(
        self,
        *,
        max_entries: int = 128,
        ttl_seconds: float = 900.0,
        negative_ttl_seconds: float = 2.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        if ttl_seconds <= 0 or negative_ttl_seconds <= 0:
            raise ValueError("cache TTLs must be > 0")
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._negative_ttl_seconds = negative_ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[str, _Entry[PlanT]] = OrderedDict()
        self._inflight: dict[str, Event] = {}
        self._lock = RLock()
        self._hits = self._misses = self._waits = 0
        self._compiles = self._compile_failures = self._evictions = 0

    def get_or_compile(
        self,
        fingerprint: PlanFingerprint,
        compiler: Callable[[], PlanT],
    ) -> CompiledWorkflowPlan[PlanT]:
        key = fingerprint.digest
        while True:
            owner = False
            with self._lock:
                entry = self._entries.get(key)
                now = self._clock()
                if entry is not None and entry.expires_at <= now:
                    del self._entries[key]
                    entry = None
                if entry is not None:
                    self._entries.move_to_end(key)
                    self._hits += 1
                    if entry.error is not None:
                        raise PlanCompileError(entry.error)
                    assert entry.plan is not None
                    return entry.plan
                event = self._inflight.get(key)
                if event is None:
                    event = Event()
                    self._inflight[key] = event
                    self._misses += 1
                    owner = True
                else:
                    self._waits += 1
            if owner:
                break
            event.wait()

        started_at = self._clock()
        try:
            artifact = compiler()
            plan = CompiledWorkflowPlan(
                fingerprint=fingerprint,
                artifact=artifact,
                compile_duration_ms=max(0.0, (self._clock() - started_at) * 1000.0),
            )
        except Exception as exc:
            with self._lock:
                self._compile_failures += 1
                self._insert(
                    key,
                    _Entry(
                        plan=None,
                        error=f"compiled plan failed for {key[:12]}: {exc}",
                        expires_at=self._clock() + self._negative_ttl_seconds,
                    ),
                )
                self._inflight.pop(key).set()
            raise

        with self._lock:
            self._compiles += 1
            self._insert(
                key,
                _Entry(
                    plan=plan,
                    error=None,
                    expires_at=self._clock() + self._ttl_seconds,
                ),
            )
            self._inflight.pop(key).set()
        return plan

    def _insert(self, key: str, entry: _Entry[PlanT]) -> None:
        self._entries[key] = entry
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
            self._evictions += 1

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def stats(self) -> PlanCacheStats:
        with self._lock:
            negative_entries = sum(entry.error is not None for entry in self._entries.values())
            return PlanCacheStats(
                hits=self._hits,
                misses=self._misses,
                waits=self._waits,
                compiles=self._compiles,
                compile_failures=self._compile_failures,
                evictions=self._evictions,
                entries=len(self._entries),
                negative_entries=negative_entries,
            )


def bind_compiled_plan(
    plan: CompiledWorkflowPlan[PlanT],
    request_context: Any,
    binder: Callable[[PlanT, Any], BoundT],
) -> BoundT:
    """Bind request-scoped state without mutating or caching it on the plan."""

    return binder(plan.artifact, request_context)


__all__ = [
    "CompiledPlanCache",
    "CompiledWorkflowPlan",
    "PlanCacheStats",
    "PlanCompileError",
    "PlanFingerprint",
    "bind_compiled_plan",
]
