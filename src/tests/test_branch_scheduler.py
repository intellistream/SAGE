from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from threading import Barrier, Event, current_thread, enumerate as threads

import pytest

from sage.runtime.flownet.runtime.flowengine.branch_scheduler import BranchScheduler


def test_scheduler_reuses_workers_and_preserves_context_and_order():
    scheduler = BranchScheduler(max_workers=2)
    marker = ContextVar("request-marker", default="missing")
    seen = set()
    barrier = Barrier(2)

    def branch(value):
        seen.add(current_thread())
        barrier.wait(timeout=3)
        return marker.get(), value

    try:
        for index in range(5):
            token = marker.set(str(index))
            try:
                assert scheduler.run(branch, [1, 2]) == [(str(index), 1), (str(index), 2)]
            finally:
                marker.reset(token)
        assert len(seen) == 2
    finally:
        scheduler.close()
    assert not seen.intersection(threads())
    with pytest.raises(RuntimeError, match="branch_scheduler_closed"):
        scheduler.run(branch, [1])


def test_overload_is_rejected_without_executing_and_capacity_recovers():
    scheduler = BranchScheduler(max_workers=1, max_inflight_waves=1)
    entered, release = Event(), Event()

    def blocked(value):
        entered.set()
        assert release.wait(3)
        return value

    try:
        with ThreadPoolExecutor(max_workers=1) as caller:
            running = caller.submit(scheduler.run, blocked, [1])
            try:
                assert entered.wait(3)
                with pytest.raises(RuntimeError, match="branch_scheduler_overloaded"):
                    scheduler.run(lambda _: pytest.fail("rejected work executed"), [2])
            finally:
                release.set()
            assert running.result(timeout=3) == [1]
        assert scheduler.run(lambda value: value, [3]) == [3]
    finally:
        release.set()
        scheduler.close()


def test_failure_drains_sibling_before_releasing_admission():
    scheduler = BranchScheduler(max_workers=2, max_inflight_waves=1)
    failed, entered, release = Event(), Event(), Event()

    def branch(value):
        if value == 0:
            failed.set()
            raise ValueError("failed branch")
        entered.set()
        assert release.wait(3)

    try:
        with ThreadPoolExecutor(max_workers=1) as caller:
            running = caller.submit(scheduler.run, branch, [0, 1])
            try:
                assert failed.wait(3) and entered.wait(3)
                assert not running.done()
                with pytest.raises(RuntimeError, match="branch_scheduler_overloaded"):
                    scheduler.run(lambda value: value, [2])
            finally:
                release.set()
            with pytest.raises(ValueError, match="failed branch"):
                running.result(timeout=3)
        assert scheduler.run(lambda value: value, [3]) == [3]
    finally:
        release.set()
        scheduler.close()


def test_reentrant_wait_fails_instead_of_deadlocking():
    scheduler = BranchScheduler(max_workers=1)
    try:
        with pytest.raises(RuntimeError, match="branch_scheduler_reentrant_wait"):
            scheduler.run(lambda _: scheduler.run(lambda value: value, [1]), [0])
        with pytest.raises(ValueError, match="branch_wave_exceeds_worker_limit"):
            scheduler.run(lambda value: value, [1, 2])
    finally:
        scheduler.close()
