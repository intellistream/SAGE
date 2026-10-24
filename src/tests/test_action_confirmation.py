from concurrent.futures import ThreadPoolExecutor

import pytest

from sage.runtime.action_confirmation import ActionConfirmations, ConfirmationError
from sage.runtime.effect_cancellation import EffectFences, EffectCancelled
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.operation_receipts import OperationReceipts


def test_read_is_owner_bound_nonmutating_and_does_not_execute(tmp_path, monkeypatch):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.sqlite3"))
    gate = ActionConfirmations(store, namespace="read", clock=lambda: 10)
    draft = gate.prepare("owner", {"topic": "synthetic"}, ttl_seconds=1)
    receipts = OperationReceipts(store, namespace="read")
    receipts.commit("committed", inputs={}, slots=(("test", "test", "one"),),
                    transition=lambda values: ({"accepted": True}, {("test", "test", "one"): 1}))
    monkeypatch.setattr(store, "update_many", lambda *args, **kwargs: pytest.fail("read must not write or execute"))
    assert receipts.read("absent") is None
    assert receipts.read("committed") == {"accepted": True}
    assert gate.read("owner", draft["action_id"])["status"] == "pending"
    with pytest.raises(ConfirmationError, match="not_found"):
        gate.read("another-owner", draft["action_id"])
    gate.clock = lambda: 12
    assert gate.read("owner", draft["action_id"])["status"] == "expired"
    assert store.peek(gate._slot("owner", draft["action_id"]))["status"] == "pending"
    store.close()


def test_immutable_owner_scoped_proposal_and_restart(tmp_path):
    path = str(tmp_path / "state.sqlite3")
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    gate = ActionConfirmations(store, namespace="test", clock=lambda: 100)
    draft = gate.prepare("owner-a", {"topic": "a"}, operation_id="one")
    assert draft["status"] == "pending"
    assert gate.prepare("owner-a", {"topic": "a"}, operation_id="one") == draft
    draft["payload"]["topic"] = "mutated caller copy"
    assert gate.prepare("owner-a", {"topic": "a"}, operation_id="one")["payload"] == {"topic": "a"}
    with pytest.raises(ConfirmationError, match="payload_conflict"):
        gate.prepare("owner-a", {"topic": "changed"}, operation_id="one")
    with pytest.raises(ConfirmationError, match="not_found"):
        gate.resolve("owner-b", draft["action_id"], decision="confirm")
    store.close()
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        gate = ActionConfirmations(store, namespace="test", clock=lambda: 101)
        result = gate.resolve("owner-a", draft["action_id"], decision="confirm")
        assert result["payload"] == {"topic": "a"}
        assert gate.resolve("owner-a", draft["action_id"], decision="confirm") == result
        with pytest.raises(ConfirmationError, match="already_confirmed"):
            gate.resolve("owner-a", draft["action_id"], decision="cancel")
    finally:
        store.close()


def test_cancel_expiry_and_racing_decisions(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.sqlite3"))
    try:
        now = [0]
        gate = ActionConfirmations(store, namespace="test", clock=lambda: now[0])
        draft = gate.prepare("a", {}, ttl_seconds=1)
        now[0] = 2
        with pytest.raises(ConfirmationError, match="expired"):
            gate.resolve("a", draft["action_id"], decision="confirm")
        assert gate.resolve("a", draft["action_id"], decision="cancel")["status"] == "cancelled"
        with pytest.raises(ConfirmationError, match="already_cancelled"):
            gate.resolve("a", draft["action_id"], decision="confirm")
        draft = gate.prepare("a", {})
        def decide(value):
            try:
                return gate.resolve("a", draft["action_id"], decision=value)["status"]
            except ConfirmationError:
                return "conflict"
        with ThreadPoolExecutor(2) as pool:
            outcomes = list(pool.map(decide, ["confirm", "cancel"]))
        assert outcomes.count("conflict") == 1
    finally:
        store.close()


def test_sealed_scope_rejects_stale_prepare_and_its_replay(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.sqlite3"))
    try:
        gate = ActionConfirmations(store, namespace="test")
        fences = EffectFences(store, namespace="test")
        guard = fences.prepare_guard("request")
        gate.prepare("owner", {}, operation_id="before", guard=guard)
        fences.seal("request")
        for operation in ("before", "after"):
            with pytest.raises(EffectCancelled):
                gate.prepare("owner", {}, operation_id=operation, guard=guard)
    finally:
        store.close()
