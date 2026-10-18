from concurrent.futures import ThreadPoolExecutor

import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.operation_receipts import OperationConflict, OperationReceipts

OLD = ("booking", "calendar", "records")
NEW = ("outbox", "notifications", "request")
EVIDENCE = {"historical_delivery": "unknown", "automatic_resend": False}


def migrate(receipts, **overrides):
    args = dict(migration_id="outbox-v2", old_slots=[OLD], new_slots=[OLD, NEW], evidence=EVIDENCE)
    args.update(overrides)
    return receipts.migrate_destinations("request", **args)


def seed(store):
    receipts = OperationReceipts(store, namespace="owner")
    receipts.commit("request", inputs={"a": 1}, slots=[OLD],
                    transition=lambda values: ({"accepted": True}, {OLD: "pending"}))
    store.update(OLD, lambda _: "confirmed")
    return receipts


def test_migration_preserves_result_current_state_and_unknown_external_outcome(tmp_path):
    path = str(tmp_path / "state.db")
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    receipts = seed(store)
    audit = migrate(receipts)
    assert audit["original_receipt"]["destinations"] == [list(OLD)]
    assert audit["evidence"] == EVIDENCE
    assert migrate(receipts) == audit
    store.close()
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        receipts = OperationReceipts(store, namespace="owner")
        def forbidden(_):
            pytest.fail("historical producer must not run")
        assert receipts.commit("request", inputs={"a": 1}, slots=[NEW, OLD],
                               transition=forbidden) == {"accepted": True}
        assert store.peek(OLD) == "confirmed"
        assert store.peek(NEW) is None  # No automatic historical mail admission.
        with pytest.raises(OperationConflict):
            receipts.commit("request", inputs={"a": 2}, slots=[NEW, OLD], transition=forbidden)
        with pytest.raises(OperationConflict):
            migrate(receipts, evidence={"historical_delivery": "sent"})
    finally:
        store.close()


def test_failed_migration_rolls_back_receipt_and_audit(tmp_path, monkeypatch):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    receipts = seed(store)
    put = store._backend._put_uncommitted
    def fail(slot, entry):
        put(slot, entry)
        if slot[0] == "sage-operation-migrations-v1":
            raise OSError("synthetic migration failure")
    try:
        with monkeypatch.context() as patch:
            patch.setattr(store._backend, "_put_uncommitted", fail)
            with pytest.raises(OSError):
                migrate(receipts)
        original = store.peek(("sage-operation-receipts-v1", "owner", "request"))
        assert original["destinations"] == [list(OLD)]
        assert migrate(receipts)["original_receipt"] == original
    finally:
        store.close()


def test_independent_connections_migrate_idempotently(tmp_path):
    path = str(tmp_path / "state.db")
    stores = [StatefulProcessRuntime(backend="sqlite", sqlite_path=path) for _ in range(2)]
    seed(stores[0])
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda store: migrate(OperationReceipts(store, namespace="owner")), stores))
        assert results[0] == results[1]
        assert stores[0].peek(NEW) is None
    finally:
        for store in stores:
            store.close()


@pytest.mark.parametrize("overrides", [
    {"new_slots": [NEW]}, {"new_slots": [OLD]}, {"new_slots": [OLD, NEW, NEW]},
    {"new_slots": [OLD, ("sage-operation-migrations-v1", "owner", "audit")]},
    {"evidence": {}}, {"old_slots": [("other", "calendar", "records")]},
])
def test_invalid_migration_is_fail_closed(tmp_path, overrides):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    receipts = seed(store)
    try:
        with pytest.raises(ValueError):
            migrate(receipts, **overrides)
        assert store.peek(OLD) == "confirmed"
        assert store.peek(NEW) is None
    finally:
        store.close()
