"""Qualify native fan-out before applications depend on parallel retrieval."""

from threading import Barrier

import pytest

from sage.runtime.flownet import (
    FlowRequestOutcomeError, actor, bootstrap_runtime, build_runtime_client,
    flow, require_event_cursor,
)


_barriers: dict[str, Barrier] = {}
_finished: set[str] = set()


@actor(uri="actor://tests/parallel-request/left", namespace="tests.parallel")
class LeftBranch:
    def run(self, payload):
        payload["items"].append("left")
        _barriers[payload["id"]].wait(timeout=3)
        assert require_event_cursor().event_group_id == payload["id"]
        if payload.get("fail"):
            raise ValueError("left branch failed")
        return {"id": payload["id"], "branch": "left", "items": payload["items"]}


@actor(uri="actor://tests/parallel-request/right", namespace="tests.parallel")
class RightBranch:
    def run(self, payload):
        payload["items"].append("right")
        _barriers[payload["id"]].wait(timeout=3)
        assert require_event_cursor().event_group_id == payload["id"]
        _finished.add(payload["id"])
        return {"id": payload["id"], "branch": "right", "items": payload["items"]}


@flow(uri="flow://tests/parallel-request/fanout", namespace="tests.parallel")
def fanout_flow(init_stream):
    return init_stream.map(LeftBranch().run).connect(init_stream.map(RightBranch().run))


def test_native_fanout_overlaps_branches_and_correlates_results():
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19481")
    try:
        client = build_runtime_client(owner="test", runtime_host=bootstrap.runtime_host)
        endpoint = fanout_flow.bind("parallel-input", "parallel-output").endpoint(
            client=client, reuse_existing=False
        )
        for index in range(3):
            key = f"request-{index}"
            _barriers[key] = Barrier(2)
            payload = {"id": key, "items": []}
            results = endpoint.call(payload, timeout=10, request_id=key)
            assert payload["items"] == []
            assert sorted(results, key=lambda item: item["branch"]) == [
                {"id": key, "branch": "left", "items": ["left"]},
                {"id": key, "branch": "right", "items": ["right"]},
            ]
    finally:
        bootstrap.shutdown()
        _barriers.clear()
        _finished.clear()


def test_failed_branch_drains_sibling_without_publishing_partial_success():
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19482")
    try:
        client = build_runtime_client(owner="test", runtime_host=bootstrap.runtime_host)
        endpoint = fanout_flow.bind("failed-input", "failed-output").endpoint(
            client=client, reuse_existing=False
        )
        key = "failed-wave"
        _barriers[key] = Barrier(2)
        with pytest.raises(FlowRequestOutcomeError) as failure:
            endpoint.call({"id": key, "items": [], "fail": True}, request_id=key)
        assert key in _finished
        # The runtime publishes one explicit error envelope, not the sibling's
        # otherwise successful output.
        assert len(failure.value.outputs) == 1
        assert failure.value.outputs[0]["error_type"] == "ValueError"
        assert failure.value.outputs[0]["event_group_id"] == key
        assert "branch" not in failure.value.outputs[0]
        assert endpoint._requests == {}
    finally:
        bootstrap.shutdown()
        _barriers.clear()
        _finished.clear()
