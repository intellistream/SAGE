from __future__ import annotations

import pytest

from sage.runtime.flownet import (
    SharedStateServiceDescriptor,
    V1NodeRuntimeService,
    actor,
    bootstrap_runtime,
    build_runtime_client,
    build_runtime_inspector,
    flow,
    resolve_bound_shared_state_service,
    service,
)


@actor(uri="actor://tests/endpoint-plane/echo", namespace="team.alpha")
class EndpointEchoActor:
    def advance(self, payload: dict[str, int]) -> dict[str, int]:
        return {"value": int(payload.get("value", 0))}


@actor(uri="actor://tests/endpoint-plane/offset", namespace="team.alpha")
class EndpointOffsetActor:
    def advance(self, payload: dict[str, int]) -> dict[str, int]:
        return {"value": int(payload.get("value", 0)) + 1}


@service(uri="service://tests/endpoint-plane/counter", namespace="team.alpha")
class EndpointCounterService:
    def __init__(self) -> None:
        self.value = 0

    def increment(self, delta: int = 1) -> int:
        self.value += int(delta)
        return self.value


@actor(uri="actor://tests/endpoint-plane/shared-state-reader", namespace="team.alpha")
class EndpointSharedStateReaderActor:
    def advance(self, payload: dict[str, int]) -> dict[str, int]:
        counter = resolve_bound_shared_state_service("counter")
        return {"value": int(counter.increment(int(payload.get("delta", 1))))}


@flow(uri="flow://tests/endpoint-plane/echo", namespace="team.alpha")
def endpoint_echo_flow(init_stream):
    return init_stream.map(EndpointEchoActor().advance)


@flow(uri="flow://tests/endpoint-plane/offset", namespace="team.alpha")
def endpoint_offset_flow(init_stream):
    return init_stream.map(EndpointOffsetActor().advance)


@flow(uri="flow://tests/endpoint-plane/shared-state", namespace="team.alpha")
def endpoint_shared_state_flow(init_stream):
    return init_stream.map(EndpointSharedStateReaderActor().advance)


@pytest.fixture
def runtime_client_pair():
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19451")
    client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
    try:
        yield bootstrap, client
    finally:
        bootstrap.shutdown()


def _build_endpoint_inspector(bootstrap):
    node_runtime = V1NodeRuntimeService(
        runtime_host=bootstrap.runtime_host,
        node_id="node-endpoint-plane",
        node_address="127.0.0.1:18891",
    )
    return build_runtime_inspector(
        runtime_host=bootstrap.runtime_host,
        node_control_call=node_runtime.node_control_call,
        default_node_address=node_runtime.node_address,
    )


def test_published_endpoint_can_be_found_and_listed_in_inventory(runtime_client_pair) -> None:
    bootstrap, client = runtime_client_pair

    published = endpoint_echo_flow.bind(
        "endpoint-plane-input-a",
        "endpoint-plane-output-a",
    ).publish(
        client=client,
        name="echo-main",
        version="2026.04",
        reuse_existing=False,
    )

    found = endpoint_echo_flow.find_endpoint(client=client, name="echo-main")
    assert found is not None
    assert found.call({"value": 7}, timeout=5.0) == [{"value": 7}]

    snapshot = published.inspect()
    assert snapshot["name"] == "echo-main"
    assert snapshot["namespace"] == "team.alpha"
    assert snapshot["version"] == "2026.04"
    assert snapshot["flow_uri"] == "flow://tests/endpoint-plane/echo"
    assert snapshot["status"] == "published"

    inspector = _build_endpoint_inspector(bootstrap)
    rows = inspector.list_published_endpoints()
    assert rows[0]["name"] == "echo-main"
    assert rows[0]["namespace"] == "team.alpha"
    assert rows[0]["flow_uri"] == "flow://tests/endpoint-plane/echo"
    assert rows[0]["version"] == "2026.04"


def test_published_endpoint_reuse_existing_returns_same_publication(runtime_client_pair) -> None:
    _, client = runtime_client_pair

    first = endpoint_echo_flow.bind(
        "endpoint-plane-input-reuse",
        "endpoint-plane-output-reuse",
    ).publish(
        client=client,
        name="echo-reuse",
        reuse_existing=False,
    )
    second = endpoint_echo_flow.bind(
        "endpoint-plane-input-reuse",
        "endpoint-plane-output-reuse",
    ).publish(
        client=client,
        name="echo-reuse",
        reuse_existing=True,
    )

    first_snapshot = first.inspect()
    second_snapshot = second.inspect()
    assert first_snapshot["endpoint_id"] == second_snapshot["endpoint_id"]
    assert first_snapshot["flow_instance_id"] == second_snapshot["flow_instance_id"]


def test_published_endpoint_duplicate_name_conflict_fails_fast(runtime_client_pair) -> None:
    _, client = runtime_client_pair

    endpoint_echo_flow.bind(
        "endpoint-plane-input-conflict-a",
        "endpoint-plane-output-conflict-a",
    ).publish(
        client=client,
        name="shared-name",
        reuse_existing=False,
    )

    with pytest.raises(ValueError, match="flow_endpoint_publish_conflict"):
        endpoint_offset_flow.bind(
            "endpoint-plane-input-conflict-b",
            "endpoint-plane-output-conflict-b",
        ).publish(
            client=client,
            name="shared-name",
            reuse_existing=True,
        )


def test_published_endpoint_namespace_mismatch_fails_fast(runtime_client_pair) -> None:
    _, client = runtime_client_pair

    with pytest.raises(ValueError, match="flow_endpoint_namespace_mismatch"):
        endpoint_echo_flow.bind(
            "endpoint-plane-input-namespace",
            "endpoint-plane-output-namespace",
        ).publish(
            client=client,
            name="echo-wrong-ns",
            namespace="team.beta",
            reuse_existing=False,
        )


def test_published_endpoint_missing_binding_fails_fast(runtime_client_pair) -> None:
    _, client = runtime_client_pair

    with pytest.raises(ValueError, match="flow_endpoint_requires_in_out_topic"):
        endpoint_echo_flow.publish(
            client=client,
            name="echo-missing-binding",
            reuse_existing=False,
        )


def test_published_endpoint_inventory_includes_shared_state_bindings(runtime_client_pair) -> None:
    bootstrap, client = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="endpoint-counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="cross_flow",
        recovery_policy="best_effort",
    )
    client.start_shared_state_service(EndpointCounterService, descriptor=descriptor)

    published = endpoint_shared_state_flow.use_shared_state("counter", descriptor).bind(
        "endpoint-plane-input-shared-state",
        "endpoint-plane-output-shared-state",
    ).publish(
        client=client,
        name="shared-state-endpoint",
        reuse_existing=False,
    )

    snapshot = published.inspect()
    assert snapshot["shared_state_bindings"][0]["alias"] == "counter"
    assert snapshot["shared_state_bindings"][0]["contract_id"] == descriptor.contract_id

    inspector = _build_endpoint_inspector(bootstrap)
    rows = inspector.list_published_endpoints()
    shared_state_row = next(row for row in rows if row["name"] == "shared-state-endpoint")
    assert shared_state_row["shared_state_bindings"][0]["contract_id"] == descriptor.contract_id