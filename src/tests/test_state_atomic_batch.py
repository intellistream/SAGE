import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime

A = ("memory", "turns", "exchange")
B = ("journal", "turns", "intent")


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_batch_detached_values_and_callback_rollback(tmp_path, backend):
    store = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    source = {A: ["answer"], B: ["pending"]}
    try:
        result = store.update_many([A, B], lambda old: source)
        source[A].append("caller")
        result[B].append("observer")

        def fail(old):
            old[A].append("partial")
            raise ValueError("injected failure")

        with pytest.raises(ValueError, match="injected failure"):
            store.update_many([A, B], fail)
        assert store.peek(A) == ["answer"]
        assert store.peek(B) == ["pending"]
    finally:
        store.close()


@pytest.mark.parametrize("slots", [[], [A, A], [A, ("memory ", "turns", "exchange")]])
def test_invalid_slots_rejected_before_callback(tmp_path, slots):
    store = StatefulProcessRuntime()
    try:
        with pytest.raises(ValueError):
            store.update_many(slots, lambda old: pytest.fail("must not execute"))
        assert store.peek(A) is None
    finally:
        store.close()


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
@pytest.mark.parametrize("result", [{A: 1}, {A: 1, B: 2, ("other", "ns", "key"): 3}, None])
def test_result_cannot_omit_or_add_records(tmp_path, backend, result):
    store = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    try:
        store.update_many([A, B], lambda old: {A: "old", B: "old"})
        with pytest.raises(ValueError, match="result_slots_mismatch"):
            store.update_many([A, B], lambda old: result)
        assert store.peek(A) == store.peek(B) == "old"
    finally:
        store.close()


def test_second_serialization_failure_rolls_back_first_sql_write(tmp_path):
    path = str(tmp_path / "state.db")
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        store.update_many([A, B], lambda old: {A: 1, B: 1})
        with pytest.raises((AttributeError, TypeError)):
            store.update_many([A, B], lambda old: {A: 2, B: lambda: None})
        assert store.peek(A) == store.peek(B) == 1
        assert store.update_many([A, B], lambda old: {slot: value + 1 for slot, value in old.items()}) == {A: 2, B: 2}
    finally:
        store.close()


def test_two_connections_serialize_whole_batch_and_reopen(tmp_path):
    path = str(tmp_path / "state.db")
    stores = [StatefulProcessRuntime(backend="sqlite", sqlite_path=path) for _ in range(2)]
    def increment(store):
        for _ in range(30):
            def transform(old):
                assert old[A] == old[B]
                return {A: old[A] + 1, B: old[B] + 1}
            store.update_many([A, B], transform, default=0)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(increment, stores))
    finally:
        for store in stores:
            store.close()
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        assert reopened.peek(A) == reopened.peek(B) == 60
    finally:
        reopened.close()


def test_process_exit_after_first_sql_write_rolls_back_entire_batch(tmp_path):
    path = str(tmp_path / "state.db")
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    store.update_many([A, B], lambda old: {A: 1, B: 1})
    store.close()
    code = f"""
import os
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
s = StatefulProcessRuntime(backend='sqlite', sqlite_path={path!r})
original = s._backend._put_uncommitted
def interrupted(slot, entry):
    original(slot, entry)
    os._exit(25)
s._backend._put_uncommitted = interrupted
s.update_many([{A!r}, {B!r}], lambda old: {{slot: 2 for slot in old}})
"""
    result = subprocess.run([sys.executable, "-c", code], timeout=15, capture_output=True)
    assert result.returncode == 25, result.stderr.decode()
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        assert reopened.peek(A) == reopened.peek(B) == 1
    finally:
        reopened.close()


@pytest.mark.parametrize("before_commit,expected,exit_code", [(True, 1, 23), (False, 2, 24)])
def test_process_exit_before_or_after_batch_commit(tmp_path, before_commit, expected, exit_code):
    path = str(tmp_path / "state.db")
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    store.update_many([A, B], lambda old: {A: 1, B: 1})
    store.close()
    code = f"""
import os
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
s = StatefulProcessRuntime(backend='sqlite', sqlite_path={path!r})
def transform(old):
    if {before_commit!r}:
        os._exit(23)
    return {{slot: 2 for slot in old}}
s.update_many([{A!r}, {B!r}], transform)
os._exit(24)
"""
    result = subprocess.run([sys.executable, "-c", code], timeout=15, capture_output=True)
    assert result.returncode == exit_code, result.stderr.decode()
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        assert reopened.peek(A) == reopened.peek(B) == expected
    finally:
        reopened.close()
