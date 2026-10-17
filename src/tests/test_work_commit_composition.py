import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal

DESTINATION = ("memory", "tenant", "turn")


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_prepare_is_detached_and_does_not_commit(tmp_path, backend):
    store = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(store, namespace="tenant")
    try:
        answer = {"text": ["original"]}
        tasks = {"post": {"input": [1]}}
        prepared = journal.prepare_commit("turn", result=answer, tasks=tasks)
        answer["text"].append("changed")
        tasks["post"]["input"].append(2)
        first = prepared.transform(None)
        first["result"]["text"].append("mutated output")
        first["tasks"]["post"]["payload"]["input"].append(3)
        assert journal.read("turn") is None
        store.update(prepared.slot, prepared.transform)
        assert journal.read("turn")["result"] == {"text": ["original"]}
        assert journal.read("turn")["tasks"]["post"]["payload"] == {"input": [1]}
    finally:
        store.close()


@pytest.mark.parametrize("failure", ["destination", "journal", "serialization"])
def test_composed_failure_rolls_back_destination_and_intent(tmp_path, failure):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(store, namespace="tenant")
    store.update(DESTINATION, lambda old: "old")
    if failure == "journal":
        journal.commit("turn", result="different", tasks={})
    before = journal.read("turn")
    prepared = journal.prepare_commit("turn", result="answer", tasks={"post": "payload"})

    def transform(values):
        if failure == "destination":
            raise ValueError("destination conflict")
        return {DESTINATION: (lambda: None) if failure == "serialization" else "new",
                prepared.slot: prepared.transform(values[prepared.slot])}

    try:
        with pytest.raises((ValueError, AttributeError, TypeError)):
            store.update_many([DESTINATION, prepared.slot], transform)
        assert store.peek(DESTINATION) == "old"
        assert journal.read("turn") == before
    finally:
        store.close()


def test_atomic_destination_and_intent_reopen_replay_preserves_completed_work(tmp_path):
    path = str(tmp_path / "state.db")
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(store, namespace="tenant")
    prepared = journal.prepare_commit("turn", result="answer", tasks={"post": "payload"})

    def transform(values):
        destination = values[DESTINATION]
        if destination is not None and destination["receipt"] != "turn":
            raise ValueError("destination identity conflict")
        return {DESTINATION: destination or {"receipt": "turn", "training_steps": 1},
                prepared.slot: prepared.transform(values[prepared.slot])}

    store.update_many([DESTINATION, prepared.slot], transform)
    lease = journal.claim("turn", "post", lease_seconds=30)
    journal.finish(lease, result="completed")
    store.close()
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(store, namespace="tenant")
    prepared = journal.prepare_commit("turn", result="answer", tasks={"post": "payload"})
    try:
        store.update_many([DESTINATION, prepared.slot], transform)
        assert store.peek(DESTINATION)["training_steps"] == 1
        state = journal.read("turn")
        assert state["tasks"]["post"]["status"] == "done"
        assert state["tasks"]["post"]["result"] == "completed"
        assert state["tasks"]["post"]["attempt"] == 1
    finally:
        store.close()
