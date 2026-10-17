from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sage.runtime.cancellation import RequestCancellation, bind_request_cancellation

from sage.runtime.flownet import (
    FlowRequestOutcomeError, actor, bootstrap_runtime, build_runtime_client, flow,
)


_entered = Event()
_release = Event()
_downstream = []


def test_call_deadline_expiry_during_operator_prevents_downstream(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("sage.runtime.cancellation.monotonic", lambda: clock[0])
    _entered.clear()
    _release.clear()
    _downstream.clear()
    bootstrap = bootstrap_runtime(node_mode="local")
    try:
        client = build_runtime_client(owner="test", runtime_host=bootstrap.runtime_host)
        endpoint = cancellable_flow.bind("running-in", "running-out").endpoint(
            client=client, reuse_existing=False
        )
        with ThreadPoolExecutor(max_workers=1) as caller:
            running = caller.submit(endpoint.call, "expired-during-work", timeout=5)
            try:
                assert _entered.wait(3)
                clock[0] = float("inf")
            finally:
                _release.set()
            with pytest.raises(FlowRequestOutcomeError) as error:
                running.result(timeout=3)
            assert error.value.outcome_status == "aborted"
        assert _downstream == []
        assert endpoint._requests == {}
        endpoint.close()
    finally:
        _release.set()
        bootstrap.shutdown()


def test_call_expired_budget_does_not_start_operators():
    _entered.clear()
    _downstream.clear()
    bootstrap = bootstrap_runtime(node_mode="local")
    try:
        client = build_runtime_client(owner="test", runtime_host=bootstrap.runtime_host)
        endpoint = cancellable_flow.bind("deadline-in", "deadline-out").endpoint(
            client=client, reuse_existing=False
        )
        with pytest.raises(FlowRequestOutcomeError) as error:
            endpoint.call("expired", timeout=0)
        assert error.value.outcome_status == "aborted"
        assert not _entered.is_set()
        assert _downstream == []
        assert endpoint._requests == {}
        endpoint.close()
    finally:
        bootstrap.shutdown()


def test_parent_scope_cancellation_is_inherited_without_upward_propagation():
    bootstrap = bootstrap_runtime(node_mode="local")
    try:
        client = build_runtime_client(owner="test", runtime_host=bootstrap.runtime_host)
        endpoint = cancellable_flow.bind("scope-in", "scope-out").endpoint(
            client=client, reuse_existing=False
        )
        parent = RequestCancellation()
        with bind_request_cancellation(parent):
            first = endpoint.open_request()
            second = endpoint.open_request()
        first.cancel()
        assert not parent.cancelled
        assert not second.status()["cancellation_requested"]
        parent.cancel()
        assert second.status()["cancellation_requested"]
        second.write("must-not-run")
        second.finish()
        with pytest.raises(FlowRequestOutcomeError) as error:
            second.collect(timeout=3)
        assert error.value.outcome_status == "aborted"
        first.release()
        second.release()
        assert not endpoint.open_request().status()["cancellation_requested"]
        endpoint.close()
    finally:
        bootstrap.shutdown()


@actor(uri="actor://tests/cancellation/slow", namespace="tests.cancel")
class SlowActor:
    def run(self, payload):
        _entered.set()
        assert _release.wait(3)
        return payload


@actor(uri="actor://tests/cancellation/after", namespace="tests.cancel")
class AfterActor:
    def run(self, payload):
        _downstream.append(payload)
        return payload


@flow(uri="flow://tests/cancellation/request", namespace="tests.cancel")
def cancellable_flow(init_stream):
    return init_stream.map(SlowActor().run).map(AfterActor().run)


@pytest.mark.parametrize("before_start", [True, False])
def test_request_cancel_prevents_downstream_and_reports_aborted(before_start):
    _entered.clear()
    _release.clear()
    _downstream.clear()
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19483")
    try:
        client = build_runtime_client(owner="test", runtime_host=bootstrap.runtime_host)
        endpoint = cancellable_flow.bind("cancel-in", "cancel-out").endpoint(
            client=client, reuse_existing=False
        )
        request = endpoint.open_request(request_id="cancelled")
        if before_start:
            request.cancel()
            request.write({"value": 1})
            assert not _entered.is_set()
        else:
            with ThreadPoolExecutor(max_workers=1) as caller:
                running = caller.submit(request.write, {"value": 1})
                try:
                    assert _entered.wait(3)
                    request.cancel()
                    assert not running.done()  # cancellation does not kill a thread
                finally:
                    _release.set()
                running.result(timeout=3)
        request.finish()
        with pytest.raises(FlowRequestOutcomeError) as error:
            request.collect(timeout=3)
        assert error.value.outcome_status == "aborted"
        assert request.status()["cancellation_requested"]
        assert _downstream == []
        request.release()
        # Cancellation must not poison the next request on the same endpoint.
        _release.set()
        assert endpoint.call({"value": 2}) == [{"value": 2}]
        assert _downstream == [{"value": 2}]
        completed = endpoint.submit({"value": 3})
        assert completed.collect() == [{"value": 3}]
        completed.cancel()
        assert completed.status()["outcome_status"] == "succeeded"
        completed.release()
    finally:
        _release.set()
        bootstrap.shutdown()
