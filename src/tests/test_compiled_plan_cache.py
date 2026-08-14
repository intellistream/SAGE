from __future__ import annotations

import gc
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor

import pytest

from sage.runtime import CompiledPlanCache, PlanCompileError, PlanFingerprint, bind_compiled_plan


def _fingerprint(*, policy_version: str = "v1") -> PlanFingerprint:
    return PlanFingerprint.build(
        operator_dag=[{"id": "retrieve"}, {"id": "answer", "after": ["retrieve"]}],
        schema={"input": "Question", "output": "Answer"},
        policy_version=policy_version,
        capabilities={"model": "chat", "retrieval": True},
        retrieval_contract={"kind": "public-knowledge", "version": 2},
        resource_class="interactive-npu",
    )


def test_fingerprint_is_canonical_and_versioned() -> None:
    first = _fingerprint()
    same = _fingerprint()
    changed = _fingerprint(policy_version="v2")
    assert first == same
    assert first.digest != changed.digest


def test_warm_lookup_compiles_once() -> None:
    cache: CompiledPlanCache[tuple[str, ...]] = CompiledPlanCache()
    calls = 0

    def compile_plan() -> tuple[str, ...]:
        nonlocal calls
        calls += 1
        return ("retrieve", "answer")

    first = cache.get_or_compile(_fingerprint(), compile_plan)
    second = cache.get_or_compile(_fingerprint(), compile_plan)
    assert first is second
    assert calls == 1
    assert cache.stats().hits == 1


def test_twenty_concurrent_misses_are_single_flight() -> None:
    cache: CompiledPlanCache[object] = CompiledPlanCache()
    calls = 0
    lock = threading.Lock()
    release = threading.Event()

    def compile_plan() -> object:
        nonlocal calls
        with lock:
            calls += 1
        release.wait(timeout=2)
        return object()

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(cache.get_or_compile, _fingerprint(), compile_plan) for _ in range(20)]
        wait_deadline = time.monotonic() + 2.0
        while cache.stats().waits < 19 and time.monotonic() < wait_deadline:
            time.sleep(0.001)
        release.set()
        plans = [future.result(timeout=2) for future in futures]

    assert calls == 1
    assert len({id(plan) for plan in plans}) == 1
    assert cache.stats().waits == 19


def test_negative_cache_expires_and_recovers() -> None:
    now = [10.0]
    cache: CompiledPlanCache[str] = CompiledPlanCache(
        negative_ttl_seconds=2.0,
        clock=lambda: now[0],
    )
    calls = 0

    def compile_plan() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("invalid graph")
        return "compiled"

    with pytest.raises(ValueError, match="invalid graph"):
        cache.get_or_compile(_fingerprint(), compile_plan)
    with pytest.raises(PlanCompileError, match="invalid graph"):
        cache.get_or_compile(_fingerprint(), compile_plan)
    assert calls == 1
    now[0] += 2.1
    assert cache.get_or_compile(_fingerprint(), compile_plan).artifact == "compiled"
    assert calls == 2


def test_request_context_is_not_retained_after_bind() -> None:
    class RequestContext:
        pass

    cache = CompiledPlanCache[str]()
    plan = cache.get_or_compile(_fingerprint(), lambda: "static-plan")
    context = RequestContext()
    context_ref = weakref.ref(context)
    assert bind_compiled_plan(plan, context, lambda artifact, _: artifact) == "static-plan"
    del context
    gc.collect()
    assert context_ref() is None
