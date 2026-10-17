from concurrent.futures import ThreadPoolExecutor

import pytest

from sage.runtime.event_journal import EventJournal
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_replay_paging_terminal_and_input_detachment(tmp_path, backend):
    store = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    journal = EventJournal(store, namespace="delivery")
    try:
        assert journal.read("stream")["events"] == []
        payload = {"answer": ["full text"]}
        prepared = journal.prepare_append("stream", event_id="answer", payload=payload)
        payload["answer"].append("outside")
        store.update(prepared.slot, prepared.transform)
        journal.append("stream", event_id="complete", payload={}, terminal=True)
        replay = journal.append("stream", event_id="answer", payload={"answer": ["full text"]})
        assert replay["sequence"] == 1
        replay["payload"]["answer"].append("mutated")
        page = journal.read("stream", limit=1)
        assert page["closed"] and not page["caught_up"]
        assert page["events"][0]["payload"] == {"answer": ["full text"]}
        page = journal.read("stream", after=page["cursor"])
        assert page["closed"] and page["caught_up"] and page["cursor"] == 2
        with pytest.raises(ValueError, match="event_append_conflict"):
            journal.append("stream", event_id="answer", payload="changed")
        with pytest.raises(ValueError, match="event_stream_closed"):
            journal.append("stream", event_id="later", payload={})
        for cursor in (-1, True, 3):
            with pytest.raises(ValueError):
                journal.read("stream", after=cursor)
        with pytest.raises(ValueError):
            journal.append("stream", event_id="bad", payload=float("nan"))
        assert EventJournal(store, namespace="other").read("stream")["events"] == []
    finally:
        store.close()


def test_concurrent_connections_and_reopen(tmp_path):
    path = str(tmp_path / "state.db")
    stores = [StatefulProcessRuntime(backend="sqlite", sqlite_path=path) for _ in range(2)]
    journals = [EventJournal(store, namespace="delivery") for store in stores]
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda i: journals[i % 2].append("stream", event_id=str(i % 20), payload=i % 20), range(40)))
    finally:
        for store in stores:
            store.close()
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        events = EventJournal(reopened, namespace="delivery").read("stream")["events"]
        assert [event["sequence"] for event in events] == list(range(1, 21))
        assert {event["payload"] for event in events} == set(range(20))
    finally:
        reopened.close()


def test_event_and_work_commit_rollback_and_replay(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    events = EventJournal(store, namespace="delivery")
    work = WorkJournal(store, namespace="work")
    try:
        prepared = events.prepare_append("stream", event_id="answer", payload="validated")
        bad_slot = ("test", "rollback", "slot")
        def fail(_):
            raise RuntimeError("abort")
        with pytest.raises(RuntimeError, match="abort"):
            work.commit("request", result="ok", tasks={}, mutations={
                prepared.slot: prepared.transform, bad_slot: fail})
        assert events.read("stream")["events"] == []
        assert work.read("request") is None
        for _ in range(2):
            work.commit("request", result="ok", tasks={}, mutations={prepared.slot: prepared.transform})
        assert len(events.read("stream")["events"]) == 1
    finally:
        store.close()


def test_lost_ack_replays_once_and_json_types_conflict(tmp_path, monkeypatch):
    path = str(tmp_path / "state.db")
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = EventJournal(store, namespace="delivery")
    original = store.update
    def lost_ack(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("ack lost")
    try:
        with monkeypatch.context() as patch:
            patch.setattr(store, "update", lost_ack)
            with pytest.raises(RuntimeError, match="ack lost"):
                journal.append("stream", event_id="one", payload={"number": 1}, terminal=True)
    finally:
        store.close()
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        recovered = EventJournal(reopened, namespace="delivery")
        assert recovered.append("stream", event_id="one", payload={"number": 1}, terminal=True)["sequence"] == 1
        with pytest.raises(ValueError, match="event_append_conflict"):
            recovered.append("stream", event_id="one", payload={"number": True}, terminal=True)
        assert recovered.read("stream")["tail"] == 1
    finally:
        reopened.close()
