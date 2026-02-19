"""Regression tests for context propagation API in sage-common (Issue #1435).

Validates that ContextSlot and run_in_executor_with_context behave correctly
across sync, async, and executor boundaries. These are the single source of
truth; Flownet no longer carries a duplicate implementation.
"""

from __future__ import annotations

import asyncio
import concurrent.futures

from sage.common.utils import ContextSlot, run_in_executor_with_context

# ──────────────────────────────────────────────────────────────────────────────
# Basic ContextSlot behaviour
# ──────────────────────────────────────────────────────────────────────────────


def test_context_slot_default_none() -> None:
    slot: ContextSlot[int] = ContextSlot("test_default")
    assert slot.get() is None


def test_context_slot_default_value() -> None:
    slot: ContextSlot[str] = ContextSlot("test_default_val", default="hello")
    assert slot.get() == "hello"


def test_context_slot_set_and_get() -> None:
    slot: ContextSlot[int] = ContextSlot("test_set_get")
    token = slot.set(42)
    assert slot.get() == 42
    slot.reset(token)
    assert slot.get() is None


def test_context_slot_use_context_manager() -> None:
    slot: ContextSlot[str] = ContextSlot("test_use_cm")
    assert slot.get() is None
    with slot.use("active"):
        assert slot.get() == "active"
    assert slot.get() is None


def test_context_slot_nested_use() -> None:
    slot: ContextSlot[int] = ContextSlot("test_nested")
    with slot.use(1):
        assert slot.get() == 1
        with slot.use(2):
            assert slot.get() == 2
        assert slot.get() == 1
    assert slot.get() is None


def test_context_slot_use_restores_on_exception() -> None:
    slot: ContextSlot[str] = ContextSlot("test_exc_restore")
    try:
        with slot.use("set"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert slot.get() is None


# ──────────────────────────────────────────────────────────────────────────────
# Context isolation: each "thread" has its own copy
# ──────────────────────────────────────────────────────────────────────────────


def test_context_slot_thread_isolation() -> None:
    """Values set in one thread must not leak to other threads."""
    slot: ContextSlot[str] = ContextSlot("test_thread_iso")

    results: list[str | None] = [None, None]

    def reader(idx: int) -> None:
        results[idx] = slot.get()

    token = slot.set("main_value")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        # Submit tasks *before* the slot is set in the worker threads
        f1 = pool.submit(reader, 0)
        f2 = pool.submit(reader, 1)
        f1.result()
        f2.result()

    # Workers see None because they don't inherit the calling thread's ctx
    assert results[0] is None
    assert results[1] is None
    slot.reset(token)


# ──────────────────────────────────────────────────────────────────────────────
# run_in_executor_with_context: context IS propagated
# ──────────────────────────────────────────────────────────────────────────────


def test_run_in_executor_with_context_propagates() -> None:
    """run_in_executor_with_context must copy the caller's context into the thread."""
    slot: ContextSlot[str] = ContextSlot("test_exec_ctx")

    async def inner() -> str | None:
        loop = asyncio.get_running_loop()
        token = slot.set("propagated")
        try:
            future = run_in_executor_with_context(loop, slot.get)
            return await asyncio.wrap_future(future)
        finally:
            slot.reset(token)

    result = asyncio.run(inner())
    assert result == "propagated"


def test_run_in_executor_does_not_modify_original_context() -> None:
    """Changes made inside the executor must not affect the caller's context."""
    slot: ContextSlot[str] = ContextSlot("test_exec_isolation")

    def mutate_and_return() -> str | None:
        slot.set("from_executor")
        return slot.get()

    async def inner() -> None:
        loop = asyncio.get_running_loop()
        token = slot.set("original")
        try:
            future = run_in_executor_with_context(loop, mutate_and_return)
            executor_val = await asyncio.wrap_future(future)
            assert executor_val == "from_executor"
            # Caller is unaffected
            assert slot.get() == "original"
        finally:
            slot.reset(token)

    asyncio.run(inner())


# ──────────────────────────────────────────────────────────────────────────────
# Async context preservation
# ──────────────────────────────────────────────────────────────────────────────


def test_context_preserved_across_await() -> None:
    """ContextVar values must survive await points in the same coroutine."""
    slot: ContextSlot[int] = ContextSlot("test_async_await")

    async def coro() -> None:
        with slot.use(99):
            await asyncio.sleep(0)
            assert slot.get() == 99

    asyncio.run(coro())


def test_context_not_shared_between_tasks() -> None:
    """Two concurrent tasks each have their own context copy."""
    slot: ContextSlot[str] = ContextSlot("test_task_isolation")
    collected: list[str | None] = []

    async def task(value: str) -> None:
        with slot.use(value):
            await asyncio.sleep(0)
            collected.append(slot.get())

    async def main() -> None:
        await asyncio.gather(task("a"), task("b"))

    asyncio.run(main())
    assert sorted(collected) == ["a", "b"]
