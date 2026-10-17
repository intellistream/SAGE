import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import StaleTaskLeaseError, WorkJournal


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_index_tracks_retry_terminal_failure_and_offline_extension(tmp_path, backend):
    state = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="index")
    def active():
        return [row["key"] for row in state.scan_stage_entries(
            stage_id="sage-work-active-v1", namespace="index")[0]]
    try:
        journal.commit("r", result="answer", tasks={"a": {}, "b": {}}, dependencies={"b": ["a"]})
        assert active() == ["r"]
        lease = journal.claim("r", "a", lease_seconds=30)
        journal.renew(lease, lease_seconds=30)
        journal.finish(lease, retry=True)
        assert active() == ["r"]
        lease = journal.claim("r", "a", lease_seconds=30)
        journal.fail(lease, code="bad_input")
        assert active() == []
        assert journal.read("r")["tasks"]["b"]["status"] == "blocked"
        journal.extend_tasks("r", tasks={"final": {}}, dependencies={"final": ["a", "b"]},
                             settled=["final"])
        assert active() == ["r"]
        final = journal.claim("r", "final", lease_seconds=30)
        journal.finish(final)
        assert active() == []
        with pytest.raises(StaleTaskLeaseError):
            journal.finish(lease)
        assert active() == []
    finally:
        state.close()


def test_prepared_composition_rolls_back_index_and_persists_it_on_reopen(tmp_path):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(state, namespace="index")
    prepared = journal.prepare_commit("r", result=None, tasks={"a": {}})
    destination = ("application", "index", "receipt")
    try:
        with pytest.raises((TypeError, AttributeError)):
            state.update_many((*prepared.slots, destination),
                              lambda old: {**prepared.apply(old), destination: lambda: None})
        assert journal.read("r") is None
        assert state.peek(prepared.index_slot) is None
        state.update_many(prepared.slots, prepared.apply)
    finally:
        state.close()
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        assert state.peek(prepared.index_slot) is True
        assert WorkJournal(state, namespace="index").read("r")["version"] == 5
        with pytest.raises(ValueError, match="cannot_mutate_journal"):
            WorkJournal(state, namespace="index").commit(
                "other", result=None, tasks={}, mutations={prepared.index_slot: lambda _: None})
    finally:
        state.close()
