from __future__ import annotations

import pytest

from sage.runtime.flownet import (
    FlowRequestOutcomeError,
    V1NodeRuntimeService,
    bootstrap_runtime,
    build_runtime_client,
    build_runtime_inspector,
    flow,
)


@flow(uri="flow://tests/collective/all-reduce", namespace="team.alpha")
def collective_all_reduce_flow(init_stream):
    return init_stream.all_reduce(
        group="workers",
        world_size=2,
        rank_field="rank",
        round_by="round_id",
        tensor_field="tensor",
        backend="auto",
        stage_id="collective-all-reduce",
    )


@flow(uri="flow://tests/collective/fast-channel", namespace="team.alpha")
def collective_missing_fast_channel_flow(init_stream):
    return init_stream.all_reduce(
        group="workers",
        world_size=2,
        rank_field="rank",
        round_by="round_id",
        tensor_field="tensor",
        backend="fast_channel",
        stage_id="collective-fast-channel",
    )


def _write_reduce_round(request, *, round_id: str, left: int, right: int) -> None:
    request.write({"round_id": round_id, "rank": 0, "tensor": left})
    request.write({"round_id": round_id, "rank": 1, "tensor": right})
    request.finish()


def test_collective_all_reduce_uses_default_topic_fallback_executor() -> None:
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19471")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
        endpoint = collective_all_reduce_flow.bind(
            "collective-input",
            "collective-output",
        ).endpoint(client=client, reuse_existing=False)

        request = endpoint.open_request(request_id="collective-happy-path")
        _write_reduce_round(request, round_id="round-1", left=3, right=5)

        assert request.collect(timeout=5.0) == [
            {"round_id": "round-1", "rank": 0, "tensor": 8},
            {"round_id": "round-1", "rank": 1, "tensor": 8},
        ]
    finally:
        bootstrap.shutdown()


def test_collective_missing_fast_channel_executor_fails_with_clear_error() -> None:
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19472")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
        endpoint = collective_missing_fast_channel_flow.bind(
            "collective-missing-input",
            "collective-missing-output",
        ).endpoint(client=client, reuse_existing=False)

        request = endpoint.open_request(request_id="collective-missing-executor")
        _write_reduce_round(request, round_id="round-missing", left=1, right=2)

        with pytest.raises(
            FlowRequestOutcomeError,
            match=r"collective_executor_not_found:.*backend=fast_channel.*available_modes=topic_fallback",
        ):
            request.collect(timeout=5.0)
    finally:
        bootstrap.shutdown()


def test_runtime_inspector_lists_collective_executors() -> None:
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19473")
    try:
        node_runtime = V1NodeRuntimeService(
            runtime_host=bootstrap.runtime_host,
            node_id="node-collective",
            node_address="127.0.0.1:18896",
        )
        inspector = build_runtime_inspector(
            runtime_host=bootstrap.runtime_host,
            node_control_call=node_runtime.node_control_call,
            default_node_address=node_runtime.node_address,
        )

        runtime_snapshot = inspector.runtime_snapshot()
        rows = inspector.list_collective_executors()

        assert runtime_snapshot["collective_executor_count"] == 1
        assert rows == [
            {
                "mode": "topic_fallback",
                "executor_type": "LocalTopicFallbackCollectiveExecutor",
                "executor_module": "sage.runtime.flownet.runtime.collective.executors",
                "path_tags": (),
                "backend_mode": "topic_fallback",
                "backend_impl": "local_topic_fallback",
                "backend_type": "topic_fallback",
                "supported_kinds": ("all_gather", "all_reduce"),
                "supports_path_tags": False,
            }
        ]
    finally:
        bootstrap.shutdown()
