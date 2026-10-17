from concurrent.futures import ThreadPoolExecutor

import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime


SLOT = ("commit", "tests", "turn")


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_update_rollback_and_detached_values(tmp_path, backend):
    store = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    try:
        result = store.update(SLOT, lambda _: {"answer": "ok", "tasks": []})
        result["tasks"].append("outside")

        def failing(value):
            value["tasks"].append("partial")
            raise ValueError("rollback")

        with pytest.raises(ValueError, match="rollback"):
            store.update(SLOT, failing)
        assert store.get(SLOT, default=None, ttl_seconds=None) == {"answer": "ok", "tasks": []}
    finally:
        store.close()


def test_sqlite_atomic_update_across_connections_and_reopen(tmp_path):
    path = str(tmp_path / "state.db")
    stores = [StatefulProcessRuntime(backend="sqlite", sqlite_path=path) for _ in range(2)]
    try:
        def increment(store):
            for _ in range(40):
                store.update(SLOT, lambda old: old + 1, default=0)
        with ThreadPoolExecutor(max_workers=2) as workers:
            list(workers.map(increment, stores))
    finally:
        for store in stores:
            store.close()
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        assert reopened.get(SLOT, default=None, ttl_seconds=None) == 80
    finally:
        reopened.close()


def test_sqlite_serialization_failure_rolls_back_and_connection_recovers(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    try:
        store.update(SLOT, lambda _: "original")
        with pytest.raises((AttributeError, TypeError)):
            store.update(SLOT, lambda _: lambda: None)
        assert store.update(SLOT, lambda old: old + "-next") == "original-next"
    finally:
        store.close()


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_update_applies_ttl_inside_atomic_read(tmp_path, backend):
    now = [0.0]
    store = StatefulProcessRuntime(
        backend=backend, sqlite_path=str(tmp_path / "state.db"), time_fn=lambda: now[0],
    )
    try:
        store.update(SLOT, lambda _: 10)
        now[0] = 20.0
        assert store.update(SLOT, lambda old: old + 1, default=0, ttl_seconds=5) == 1
    finally:
        store.close()
