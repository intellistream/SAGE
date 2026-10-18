import gc
import weakref
from concurrent.futures import ThreadPoolExecutor
from contextvars import Context, ContextVar
from threading import Barrier

import pytest

from sage.runtime.cancellation import RequestCancelledError
from sage.runtime.event_journal import EventJournal
from sage.runtime.execution_observation import ExecutionObserver
from sage.runtime.flownet import (
    FlowRequestOutcomeError,
    actor,
    bootstrap_runtime,
    build_runtime_client,
    flow,
    flow_exception_handler,
    stateless,
)
from sage.runtime.flownet.runtime.loops import LoopThread
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime

_barriers = {}
_calls = []
_nested_endpoint = None


@stateless(uri="stateless://tests/observation/left", namespace="tests.observation")
def left(payload):
    _calls.append((payload["id"], "left"))
    if payload.get("barrier"):
        _barriers[payload["id"]].wait(timeout=3)
    if payload.get("fail"):
        raise ValueError("private-failure-content")
    if payload.get("cancel"):
        raise RequestCancelledError("private-cancellation-content")
    return "left"


@stateless(uri="stateless://tests/observation/right", namespace="tests.observation")
def right(payload):
    _calls.append((payload["id"], "right"))
    if payload.get("barrier"):
        _barriers[payload["id"]].wait(timeout=3)
    return "right"


@stateless(uri="stateless://tests/observation/nested", namespace="tests.observation")
def nested(payload):
    return _nested_endpoint.call(payload, request_id="inner-" + payload["id"], timeout=5)


@flow(uri="flow://tests/observation/fanout", namespace="tests.observation")
def fanout(init_stream):
    return init_stream.map(left, operator_key="left").connect(init_stream.map(right, operator_key="right"))


@flow(uri="flow://tests/observation/single", namespace="tests.observation")
def single(init_stream):
    return init_stream.map(left, operator_key="left")


@flow(uri="flow://tests/observation/nested", namespace="tests.observation")
def nesting(init_stream):
    return init_stream.map(nested, operator_key="nested")


@actor(uri="actor://tests/observation/recovery", namespace="tests.observation")
class Recovery:
    def decide(self, event):
        mode = event["payload"]["resolution"]
        if mode == "fallback":
            return {"action": "fallback", "fallback_payloads": ["recovered"]}
        return {"action": mode}


@flow(uri="flow://tests/observation/recovered", namespace="tests.observation")
def recovered_flow(init_stream):
    with flow_exception_handler(Recovery().decide):
        return init_stream.map(left, operator_key="left")


def endpoint(program, name):
    bootstrap = bootstrap_runtime(node_mode="local")
    try:
        client = build_runtime_client(owner="observation-test", runtime_host=bootstrap.runtime_host)
        bound = program.bind(name + "-in", name + "-out").endpoint(client=client, reuse_existing=False)
        return bootstrap, bound
    except BaseException:
        bootstrap.shutdown()
        raise


def events_for(events, key):
    return [event for event in events if event.operator_key == key]


def test_real_fanout_reports_live_starts_actual_wave_and_content_free_events():
    bootstrap, bound = endpoint(fanout, "observed-parallel")
    events = []
    _barriers["parallel"] = Barrier(2)
    observer = ExecutionObserver(events.append, trace_id="synthetic-trace")
    try:
        with observer.bind():
            assert sorted(bound.call({"id": "parallel", "barrier": True,
                                      "private": "secret-request-content"},
                                     request_id="parallel", timeout=5)) == ["left", "right"]
        branches = [event for event in events if event.operator_key in {"left", "right"}]
        starts = [event for event in branches if event.state == "started"]
        ends = [event for event in branches if event.state == "completed"]
        assert len(starts) == len(ends) == 2
        assert max(event.sequence for event in starts) < min(event.sequence for event in ends)
        assert len({event.wave_id for event in starts}) == 1
        assert all(event.wave_size == 2 for event in starts)
        assert len({event.node_id for event in starts}) == 2
        # Entry routing is stored in native router configuration, not ordinary
        # Transformation.upstreams. Assert actual materialized cursor edges.
        router = next(event for event in events if event.operator_type == "sys/router"
                      and event.state == "completed")
        assert {node.node_id for node in router.next_nodes} == {event.node_id for event in starts}
        assert {event.execution_id for event in starts} == {event.execution_id for event in ends}
        assert all(event.duration_ns is None for event in starts)
        assert all(event.duration_ns >= 0 for event in ends)
        assert [event.sequence for event in events] == list(range(1, len(events) + 1))
        assert {event.trace_id for event in events} == {"synthetic-trace"}
        assert "secret-request-content" not in repr([event.to_dict() for event in events])
        assert not any(key in events[0].to_dict() for key in ("payload", "tags", "target", "exception"))
    finally:
        bootstrap.shutdown()
        _barriers.clear()


@pytest.mark.parametrize("mode,state", [("fail", "failed"), ("cancel", "cancelled")])
def test_native_failure_and_cancel_are_not_completed_or_secret_bearing(mode, state):
    bootstrap, bound = endpoint(single, "observed-" + mode)
    events = []
    try:
        with ExecutionObserver(events.append).bind():
            with pytest.raises(FlowRequestOutcomeError):
                bound.call({"id": mode, mode: True}, request_id=mode)
        assert [event.state for event in events_for(events, "left")] == ["started", state]
        assert "private-failure-content" not in repr(events)
        assert "private-cancellation-content" not in repr(events)
    finally:
        bootstrap.shutdown()


def test_request_scopes_stay_separate_on_one_resident_executor():
    bootstrap, bound = endpoint(single, "observed-request-scopes")
    try:
        def run(index):
            collected = []
            with ExecutionObserver(collected.append, trace_id=f"trace-{index}").bind():
                assert bound.call({"id": str(index)}, request_id=f"request-{index}") == ["left"]
            return collected

        with ThreadPoolExecutor(max_workers=3) as pool:
            batches = list(pool.map(run, range(6)))
        for index, events in enumerate(batches):
            assert events
            assert {event.trace_id for event in events} == {f"trace-{index}"}
            assert {event.request_id for event in events} == {f"request-{index}"}
        assert len({event.event_id for batch in batches for event in batch}) == sum(map(len, batches))
        # Unobserved calls must not reuse the last request's sink.
        sizes = list(map(len, batches))
        assert bound.call({"id": "unobserved"}, request_id="unobserved") == ["left"]
        assert list(map(len, batches)) == sizes
    finally:
        bootstrap.shutdown()


def test_nested_native_runtime_preserves_parent_execution():
    global _nested_endpoint
    child_bootstrap, child = endpoint(single, "observed-inner")
    parent_bootstrap, parent = endpoint(nesting, "observed-outer")
    events = []
    _nested_endpoint = child
    try:
        with ExecutionObserver(events.append).bind():
            assert parent.call({"id": "nested"}, request_id="nested", timeout=10) == [["left"]]
        outer = next(event for event in events_for(events, "nested") if event.state == "started")
        inner = next(event for event in events_for(events, "left") if event.state == "started")
        assert inner.parent_execution_id == outer.execution_id
        assert inner.request_id == "inner-nested"
        assert inner.program_uri != outer.program_uri
    finally:
        _nested_endpoint = None
        parent_bootstrap.shutdown()
        child_bootstrap.shutdown()


def test_failed_observation_delivery_cannot_run_operator_or_report_success():
    bootstrap, bound = endpoint(single, "observed-sink-failure")
    events = []

    def broken(event):
        if event.operator_key == "left" and event.state == "started":
            raise OSError("secret-sink-credential")
        events.append(event)

    try:
        with ExecutionObserver(broken).bind():
            with pytest.raises(FlowRequestOutcomeError) as raised:
                bound.call({"id": "never-run"}, request_id="observer-failure")
        assert raised.value.error_type == "ExecutionObservationError"
        assert "secret-sink-credential" not in raised.value.message
        assert ("never-run", "left") not in _calls
        assert not events_for(events, "left")
    finally:
        bootstrap.shutdown()


@pytest.mark.parametrize("resolution", ["fallback", "drop", "abort"])
def test_native_exception_resolution_is_not_ordinary_completion(resolution):
    bootstrap, bound = endpoint(recovered_flow, "observed-resolution-" + resolution)
    events = []
    try:
        with ExecutionObserver(events.append).bind():
            payload = {"id": "resolved", "fail": True, "resolution": resolution}
            if resolution == "fallback":
                assert bound.call(payload, request_id=resolution) == ["recovered"]
            else:
                with pytest.raises(FlowRequestOutcomeError):
                    bound.call(payload, request_id=resolution)
        actual = events_for(events, "left")
        assert [event.state for event in actual] == ["started", "recovered" if resolution == "fallback" else "failed"]
        assert actual[-1].resolution == resolution
        assert "private-failure-content" not in repr(events)
    finally:
        bootstrap.shutdown()


def test_reentrant_sink_fails_instead_of_deadlocking_or_executing_child():
    child_bootstrap, child = endpoint(single, "observed-reentrant-child")
    parent_bootstrap, parent = endpoint(single, "observed-reentrant-parent")

    def sink(event):
        if event.operator_key == "left" and event.state == "started":
            child.call({"id": "forbidden-reentrant"}, request_id="forbidden-reentrant", timeout=3)

    try:
        with ExecutionObserver(sink).bind():
            with pytest.raises(FlowRequestOutcomeError) as raised:
                parent.call({"id": "reentrant-parent"}, request_id="reentrant-parent", timeout=5)
        assert raised.value.error_type == "ExecutionObservationError"
        assert ("forbidden-reentrant", "left") not in _calls
        assert ("reentrant-parent", "left") not in _calls
    finally:
        parent_bootstrap.shutdown()
        child_bootstrap.shutdown()


def test_native_events_persist_and_replay_in_existing_event_journal(tmp_path):
    path = str(tmp_path / "events.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = EventJournal(state, namespace="workflow")
    bootstrap, bound = endpoint(single, "observed-durable")
    try:
        observer = ExecutionObserver.journaled(journal, stream_id="owned-stream")
        with observer.bind():
            assert bound.call({"id": "durable", "private": "private-input-never-recorded"},
                              request_id="durable") == ["left"]
        original = journal.read("owned-stream")
        assert original["events"]
        assert all(event["payload"]["type"] == "execution-event" for event in original["events"])
        assert "private-input-never-recorded" not in repr(original)
    finally:
        bootstrap.shutdown()
        state.close()
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        assert EventJournal(reopened, namespace="workflow").read("owned-stream") == original
    finally:
        reopened.close()


@pytest.mark.parametrize("initialize_observed", [False, True])
def test_resident_runtime_does_not_retain_finished_observer(initialize_observed):
    bootstrap = None
    if not initialize_observed:
        bootstrap, bound = endpoint(single, "observed-retention-outside")
    events = []
    observer = ExecutionObserver(events.append)
    reference = weakref.ref(observer)
    try:
        with observer.bind():
            if initialize_observed:
                bootstrap, bound = endpoint(single, "observed-retention-inside")
            assert bound.call({"id": "retention"}, request_id="retention") == ["left"]
        del observer
        gc.collect()
        assert reference() is None, "resident runtime retained a completed request observer"
        assert bound.call({"id": "after-retention"}, request_id="after-retention") == ["left"]
    finally:
        if bootstrap is not None:
            bootstrap.shutdown()


def test_loop_submission_distinguishes_request_and_service_context():
    marker = ContextVar("synthetic-request-scope", default=None)
    token = marker.set("synthetic-sensitive-scope")
    loop = LoopThread("isolated-context-test")

    async def read_scope():
        return marker.get()

    try:
        assert loop.submit(read_scope()).result(timeout=3) == "synthetic-sensitive-scope"
        assert loop.submit(read_scope(), context=Context()).result(timeout=3) is None
        assert marker.get() == "synthetic-sensitive-scope"
    finally:
        marker.reset(token)
        loop.stop()
