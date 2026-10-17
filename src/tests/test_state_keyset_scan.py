import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_keyset_scan_survives_deletion_and_returns_detached_rows(tmp_path, backend):
    store = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    try:
        for key in ["a", "b", "c", "d"]:
            store.update(("active", "work", key), lambda _: {"tasks": []})
        store.update(("history", "work", "b"), lambda _: "excluded")
        store.update(("active", "other", "b"), lambda _: "excluded")
        rows, cursor = store.scan_stage_entries(stage_id="active", namespace="work", limit=2)
        assert [row["key"] for row in rows] == ["a", "b"]
        assert cursor == "b"
        rows[0]["value"]["tasks"].append("not stored")
        assert store.peek(("active", "work", "a")) == {"tasks": []}
        store.delete(("active", "work", "a"))
        store.delete(("active", "work", "b"))
        store.update(("active", "work", "aa"), lambda _: "next sweep")
        rows, cursor = store.scan_stage_entries(
            stage_id="active", namespace="work", after_key=cursor, limit=2)
        assert [row["key"] for row in rows] == ["c", "d"]
        assert cursor is None
        rows, _ = store.scan_stage_entries(stage_id="active", namespace="work")
        assert [row["key"] for row in rows] == ["aa", "c", "d"]
        assert store.scan_stage_entries(stage_id="absent", namespace="work") == ([], None)
    finally:
        store.close()


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": -1}, {"limit": True},
                                   {"limit": 1.5}, {"after_key": 5}])
def test_invalid_scan_arguments_rejected(kwargs):
    store = StatefulProcessRuntime()
    try:
        with pytest.raises(ValueError):
            store.scan_stage_entries(stage_id="active", namespace="work", **kwargs)
    finally:
        store.close()


def test_sqlite_scan_uses_key_range_and_does_not_decode_history(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    try:
        store.update(("active", "work", "z"), lambda _: "pending")
        conn = store._backend._conn
        conn.execute("INSERT INTO state_entries VALUES (?, ?, ?, ?, ?)",
                     ("history", "work", "a", 0, b"not a pickle"))
        conn.commit()
        rows, cursor = store.scan_stage_entries(stage_id="active", namespace="work", after_key="a")
        assert rows[0]["value"] == "pending"
        assert cursor is None
        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT entry_key, updated_at, value_blob FROM state_entries "
            "WHERE stage_id = ? AND namespace = ? AND entry_key > ? ORDER BY entry_key LIMIT ?",
            ("active", "work", "a", 101),
        ).fetchall()
        detail = " ".join(row[3] for row in plan).upper()
        assert "SEARCH" in detail and "ENTRY_KEY>?" in detail
        assert "TEMP B-TREE" not in detail
    finally:
        store.close()
