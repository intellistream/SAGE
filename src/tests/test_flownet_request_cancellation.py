from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from sage.runtime.flownet import (
    FlowRequestOutcomeError, actor, bootstrap_runtime, build_runtime_client, flow,
)


_entered = Event()
_release = Event()
_downstream = []


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
