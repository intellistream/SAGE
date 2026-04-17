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


@service(uri="service://tests/shared-state/counter", namespace="team.alpha")
class CounterStateService:
    def __init__(self) -> None:
        self.value = 0

    def increment(self, delta: int = 1) -> int:
        self.value += int(delta)
        return self.value

    def read(self) -> int:
        return self.value

    def snapshot_state(self) -> dict[str, int]:
        return {"value": int(self.value)}

    def restore_state(self, snapshot: dict[str, int]) -> None:
        self.value = int(snapshot.get("value", 0))


class NonCheckpointCounterStateService:
    def __init__(self) -> None:
        self.value = 0

    def increment(self, delta: int = 1) -> int:
        self.value += int(delta)
        return self.value

    def read(self) -> int:
        return self.value


@actor(uri="actor://tests/shared-state/reader", namespace="team.alpha")
class SharedStateReaderActor:
    def advance(self, payload: dict[str, int]) -> int:
        counter = resolve_bound_shared_state_service("counter")
        return int(counter.increment(int(payload.get("delta", 1))))


@actor(uri="actor://tests/governance/echo", namespace="team.alpha")
class EchoActor:
    def advance(self, payload: dict[str, int]) -> dict[str, int]:
        return {"value": int(payload.get("value", 0))}


@flow(uri="flow://tests/shared-state/reader", namespace="team.alpha")
def shared_state_flow(init_stream):
    return init_stream.map(SharedStateReaderActor().advance)


@flow(uri="flow://tests/shared-state/reader-beta", namespace="team.beta")
def beta_namespace_flow(init_stream):
    return init_stream.map(SharedStateReaderActor().advance)


@flow(uri="flow://tests/shared-state/reader-public", namespace="team.gamma")
def gamma_namespace_flow(init_stream):
    return init_stream.map(SharedStateReaderActor().advance)


@flow(uri="flow://tests/governance/echo", namespace="team.alpha")
def echo_flow(init_stream):
    return init_stream.map(EchoActor().advance)


@pytest.fixture
def runtime_client_pair():
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19431")
    primary = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
    secondary = build_runtime_client(owner="bob", runtime_host=bootstrap.runtime_host)
    try:
        yield bootstrap, primary, secondary
    finally:
        bootstrap.shutdown()


def _build_scheduler_inspector(bootstrap):
    node_runtime = V1NodeRuntimeService(
        runtime_host=bootstrap.runtime_host,
        node_id="node-governance",
        node_address="127.0.0.1:18889",
    )
    return build_runtime_inspector(
        runtime_host=bootstrap.runtime_host,
        node_control_call=node_runtime.node_control_call,
        default_node_address=node_runtime.node_address,
    )


def test_shared_state_descriptor_validation_rejects_invalid_visibility() -> None:
    with pytest.raises(ValueError, match="visibility must be one of"):
        SharedStateServiceDescriptor(
            service_name="counter",
            namespace="team.alpha",
            owner="alice",
            visibility="hidden",
        )


def test_shared_state_duplicate_registration_fails_fast(runtime_client_pair) -> None:
    _, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="flow",
        recovery_policy="best_effort",
        binding_metadata={"slot": "primary"},
    )

    client.start_shared_state_service(CounterStateService, descriptor=descriptor)

    with pytest.raises(ValueError, match="shared_state_descriptor_already_registered"):
        client.start_shared_state_service(CounterStateService, descriptor=descriptor)


def test_flow_can_bind_and_read_shared_state_service(runtime_client_pair) -> None:
    _, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="cross_flow",
        recovery_policy="best_effort",
        binding_metadata={"role": "counter"},
    )
    client.start_shared_state_service(CounterStateService, descriptor=descriptor)

    endpoint = shared_state_flow.use_shared_state("counter", descriptor).bind(
        "shared-state-input-a",
        "shared-state-output-a",
    ).endpoint(client=client, reuse_existing=False)

    assert endpoint.call({"delta": 1}, timeout=5.0) == [1]
    assert endpoint.flow_instance.bindings["shared_state_bindings"][0]["alias"] == "counter"
    assert (
        endpoint.flow_instance.bindings["shared_state_bindings"][0]["descriptor"]["service_name"]
        == "counter"
    )


def test_private_shared_state_visibility_denies_different_owner(runtime_client_pair) -> None:
    _, client, foreign_client = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="private-counter",
        namespace="team.alpha",
        owner="alice",
        visibility="private",
        reuse_policy="cross_flow",
        recovery_policy="restart",
    )
    client.start_shared_state_service(CounterStateService, descriptor=descriptor)

    with pytest.raises(PermissionError, match="shared_state_descriptor_not_visible"):
        shared_state_flow.use_shared_state("counter", descriptor).bind(
            "shared-state-private-input",
            "shared-state-private-output",
        ).endpoint(client=foreign_client, reuse_existing=False)


def test_public_shared_state_visibility_allows_different_owner(runtime_client_pair) -> None:
    _, client, foreign_client = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="public-counter",
        namespace="team.alpha",
        owner="alice",
        visibility="public",
        reuse_policy="cross_flow",
        recovery_policy="best_effort",
    )
    client.start_shared_state_service(CounterStateService, descriptor=descriptor)

    endpoint = gamma_namespace_flow.use_shared_state("counter", descriptor).bind(
        "shared-state-public-input",
        "shared-state-public-output",
    ).endpoint(client=foreign_client, reuse_existing=False)

    assert endpoint.call({"delta": 2}, timeout=5.0) == [2]


def test_namespace_shared_state_visibility_denies_foreign_namespace(runtime_client_pair) -> None:
    _, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="namespace-counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="cross_flow",
        recovery_policy="best_effort",
    )
    client.start_shared_state_service(CounterStateService, descriptor=descriptor)

    with pytest.raises(PermissionError, match="shared_state_descriptor_not_visible"):
        beta_namespace_flow.use_shared_state("counter", descriptor).bind(
            "shared-state-beta-input",
            "shared-state-beta-output",
        ).endpoint(client=client, reuse_existing=False)


def test_shared_state_cross_flow_reuse_succeeds_when_explicit(runtime_client_pair) -> None:
    _, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="cross_flow",
        recovery_policy="best_effort",
    )
    client.start_shared_state_service(CounterStateService, descriptor=descriptor)

    flow_decl = shared_state_flow.use_shared_state("counter", descriptor)

    endpoint_one = flow_decl.bind(
        "shared-state-cross-flow-input-1",
        "shared-state-cross-flow-output-1",
    ).endpoint(client=client, reuse_existing=False)
    endpoint_two = flow_decl.bind(
        "shared-state-cross-flow-input-2",
        "shared-state-cross-flow-output-2",
    ).endpoint(client=client, reuse_existing=False)

    assert endpoint_one.call({"delta": 1}, timeout=5.0) == [1]
    assert endpoint_two.call({"delta": 1}, timeout=5.0) == [2]


def test_shared_state_cross_flow_reuse_fails_without_explicit_contract(runtime_client_pair) -> None:
    _, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="flow",
        recovery_policy="best_effort",
    )
    client.start_shared_state_service(CounterStateService, descriptor=descriptor)

    flow_decl = shared_state_flow.use_shared_state("counter", descriptor)
    first_endpoint = flow_decl.bind(
        "shared-state-flow-only-input-1",
        "shared-state-flow-only-output-1",
    ).endpoint(client=client, reuse_existing=False)

    assert first_endpoint.call({"delta": 1}, timeout=5.0) == [1]

    with pytest.raises(RuntimeError, match="shared_state_cross_flow_reuse_not_allowed"):
        flow_decl.bind(
            "shared-state-flow-only-input-2",
            "shared-state-flow-only-output-2",
        ).endpoint(client=client, reuse_existing=False)


def test_runtime_inspector_lists_shared_state_services(runtime_client_pair) -> None:
    bootstrap, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="inspected-counter",
        namespace="team.alpha",
        owner="alice",
        visibility="public",
        reuse_policy="cross_flow",
        recovery_policy="checkpoint_restore",
        binding_metadata={"role": "inspected"},
    )
    client.start_shared_state_service(CounterStateService, descriptor=descriptor)

    node_runtime = V1NodeRuntimeService(
        runtime_host=bootstrap.runtime_host,
        node_id="node-shared-state",
        node_address="127.0.0.1:18887",
    )
    inspector = build_runtime_inspector(
        runtime_host=bootstrap.runtime_host,
        node_control_call=node_runtime.node_control_call,
        default_node_address=node_runtime.node_address,
    )

    rows = inspector.list_shared_state_services()

    assert rows[0]["service_name"] == "inspected-counter"
    assert rows[0]["namespace"] == "team.alpha"
    assert rows[0]["visibility"] == "public"
    assert rows[0]["reuse_policy"] == "cross_flow"
    assert rows[0]["recovery_policy"] == "checkpoint_restore"
    assert rows[0]["recovery_summary"]["status"] == "not_attempted"
    assert rows[0]["binding_metadata"] == {"role": "inspected"}
    assert rows[0]["object_type"] == "CounterStateService"


def test_shared_state_checkpoint_restore_preserves_state(runtime_client_pair) -> None:
    _, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="checkpoint-counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="cross_flow",
        recovery_policy="checkpoint_restore",
    )
    record = client.start_shared_state_service(CounterStateService, descriptor=descriptor)
    original_object = record.service_object
    original_object.increment(3)

    recovered = client.recover_shared_state_service(descriptor, reason="test-checkpoint-restore")

    assert recovered.service_object is not original_object
    assert recovered.service_object.read() == 3
    assert recovered.service_revision == 2
    assert recovered.recovery_summary.status == "checkpoint_restored"
    assert recovered.recovery_summary.last_action == "checkpoint_restore"


def test_shared_state_restart_recreates_service_without_restoring_state(runtime_client_pair) -> None:
    _, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="restart-counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="cross_flow",
        recovery_policy="restart",
    )
    record = client.start_shared_state_service(CounterStateService, descriptor=descriptor)
    original_object = record.service_object
    original_object.increment(4)

    recovered = client.recover_shared_state_service(descriptor, reason="test-restart")

    assert recovered.service_object is not original_object
    assert recovered.service_object.read() == 0
    assert recovered.service_revision == 2
    assert recovered.recovery_summary.status == "restarted"
    assert recovered.recovery_summary.last_action == "restart"


def test_shared_state_checkpoint_restore_requires_snapshot_methods(runtime_client_pair) -> None:
    _, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="unsupported-checkpoint-counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="cross_flow",
        recovery_policy="checkpoint_restore",
    )
    client.start_shared_state_service(NonCheckpointCounterStateService, descriptor=descriptor)

    with pytest.raises(RuntimeError, match="shared_state_checkpoint_restore_not_supported:.*missing_methods=snapshot_state,restore_state"):
        client.recover_shared_state_service(descriptor, reason="test-unsupported")

    rows = client.list_shared_state_services()
    assert rows[0]["recovery_summary"]["status"] == "failed"
    assert rows[0]["recovery_summary"]["last_action"] == "checkpoint_restore"


def test_shared_state_claim_quota_success_updates_governance_metrics(runtime_client_pair) -> None:
    bootstrap, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="governed-counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="cross_flow",
        recovery_policy="best_effort",
        admission_policy={"quota": {"max_concurrent_claims": 1}},
    )
    client.start_shared_state_service(CounterStateService, descriptor=descriptor)

    endpoint = shared_state_flow.use_shared_state("counter", descriptor).bind(
        "shared-state-governance-input-ok",
        "shared-state-governance-output-ok",
    ).endpoint(client=client, reuse_existing=False)

    assert endpoint.call({"delta": 1}, timeout=5.0) == [1]

    governance_audit = bootstrap.runtime_host.governance.audit_snapshot()
    shared_state_ok = next(
        record
        for record in governance_audit
        if record["resource_kind"] == "shared_state" and record["reason_code"] == "ok"
    )
    assert shared_state_ok["allowed"] is True
    assert shared_state_ok["contract_id"] == descriptor.contract_id

    inspector = _build_scheduler_inspector(bootstrap)
    governance = inspector.scheduler_stats()["governance"]
    assert governance["active_claims"] == 1
    assert governance["deny_total"] == 0


def test_shared_state_namespace_forbidden_is_recorded_in_governance_audit(runtime_client_pair) -> None:
    bootstrap, client, _ = runtime_client_pair
    descriptor = SharedStateServiceDescriptor(
        service_name="namespace-guarded-counter",
        namespace="team.alpha",
        owner="alice",
        visibility="namespace",
        reuse_policy="cross_flow",
        recovery_policy="best_effort",
    )
    client.start_shared_state_service(CounterStateService, descriptor=descriptor)

    with pytest.raises(PermissionError, match="shared_state_descriptor_not_visible:namespace_forbidden"):
        beta_namespace_flow.use_shared_state("counter", descriptor).bind(
            "shared-state-governance-input-ns-deny",
            "shared-state-governance-output-ns-deny",
        ).endpoint(client=client, reuse_existing=False)

    last_audit = bootstrap.runtime_host.governance.audit_snapshot()[-1]
    assert last_audit["resource_kind"] == "shared_state"
    assert last_audit["allowed"] is False
    assert last_audit["reason_code"] == "namespace_forbidden"


def test_flow_endpoint_quota_exceeded_updates_governance_summary(runtime_client_pair) -> None:
    bootstrap, client, _ = runtime_client_pair

    endpoint = echo_flow.bind(
        "flow-endpoint-governance-input-quota",
        "flow-endpoint-governance-output-quota",
    ).endpoint(
        client=client,
        reuse_existing=False,
        policies={
            "admission": {
                "quota": {
                    "max_requests_per_window": 1,
                    "window_ms": 60_000,
                }
            }
        },
    )

    assert endpoint.call({"value": 7}, timeout=5.0) == [{"value": 7}]

    with pytest.raises(RuntimeError, match="flow_endpoint_admission_denied:quota_exceeded"):
        endpoint.call({"value": 8}, timeout=5.0)

    last_audit = bootstrap.runtime_host.governance.audit_snapshot()[-1]
    assert last_audit["resource_kind"] == "endpoint"
    assert last_audit["allowed"] is False
    assert last_audit["reason_code"] == "quota_exceeded"
    assert last_audit["quota_name"] == "max_requests_per_window"

    inspector = _build_scheduler_inspector(bootstrap)
    governance = inspector.scheduler_stats()["governance"]
    assert governance["deny_total"] >= 1
    assert governance["quota_hit_total"] == 1


def test_flow_endpoint_tenant_mismatch_fails_fast_with_reason_code(runtime_client_pair) -> None:
    bootstrap, client, _ = runtime_client_pair

    endpoint = echo_flow.bind(
        "flow-endpoint-governance-input-tenant",
        "flow-endpoint-governance-output-tenant",
    ).endpoint(
        client=client,
        reuse_existing=False,
        policies={"admission": {"tenant": "tenant-a"}},
    )

    with pytest.raises(PermissionError, match="flow_endpoint_admission_denied:tenant_mismatch") as exc_info:
        endpoint.call({"value": 3}, timeout=5.0, tags={"tenant": "tenant-b"})

    assert getattr(exc_info.value, "reason_code", None) == "tenant_mismatch"
    last_audit = bootstrap.runtime_host.governance.audit_snapshot()[-1]
    assert last_audit["resource_kind"] == "endpoint"
    assert last_audit["allowed"] is False
    assert last_audit["reason_code"] == "tenant_mismatch"