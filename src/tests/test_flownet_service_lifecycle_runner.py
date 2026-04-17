from __future__ import annotations

import time

from sage.runtime.flownet import ServiceDeclaration, bootstrap_runtime, build_runtime_client


def _wait_for(predicate, *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition_not_met_before_timeout")


def test_service_runner_failure_records_failed_status_and_manual_restart_reexecutes_target() -> None:
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19448")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
        attempts: list[dict[str, object]] = []

        def flaky_service(config, options, instance) -> None:
            attempts.append(
                {
                    "instance_id": instance.instance_id,
                    "restart_count": options.get("restart_count", 0),
                }
            )
            if len(attempts) == 1:
                raise RuntimeError("service-crash")

        declaration = ServiceDeclaration(
            target=flaky_service,
            uri="service://tests/service-runner-restart",
            namespace="team.alpha",
            dsl_name="flaky_service_runner",
        )

        instance = client.services.start(
            declaration,
            in_topic="topic://tests/service-runner-restart",
            run_target=True,
        )

        def _service_failed() -> bool:
            snapshot = client.query_service(
                instance_id=instance.instance_id,
                include_stopped=True,
            )
            return isinstance(snapshot, dict) and snapshot["status"] == "failed"

        _wait_for(_service_failed)

        failed_snapshot = client.query_service(
            instance_id=instance.instance_id,
            include_stopped=True,
        )
        assert isinstance(failed_snapshot, dict)
        assert failed_snapshot["failure_reason"] == "service-crash"

        restarted = client.restart_service(instance)

        def _service_restarted_and_stopped() -> bool:
            snapshot = client.query_service(
                instance_id=restarted.instance_id,
                include_stopped=True,
            )
            return isinstance(snapshot, dict) and snapshot["status"] == "stopped"

        _wait_for(_service_restarted_and_stopped)

        restarted_snapshot = client.query_service(
            instance_id=restarted.instance_id,
            include_stopped=True,
        )
        assert isinstance(restarted_snapshot, dict)
        assert attempts == [
            {
                "instance_id": instance.instance_id,
                "restart_count": 0,
            },
            {
                "instance_id": restarted.instance_id,
                "restart_count": 1,
            },
        ]
        assert restarted_snapshot["failure_reason"] is None
        assert restarted_snapshot["options"]["recovered_from_instance_id"] == instance.instance_id
        assert restarted_snapshot["options"]["previous_failure_reason"] == "service-crash"
        assert restarted_snapshot["options"]["recovery_reason"] == "manual_restart"
        assert restarted_snapshot["recovery_summary"]["status"] == "restarted"
    finally:
        bootstrap.shutdown()


def test_handle_service_failure_marks_running_service_failed() -> None:
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19449")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)

        declaration = ServiceDeclaration(
            target=lambda: None,
            uri="service://tests/manual-service-failure",
            namespace="team.alpha",
            dsl_name="manual_service_failure",
        )

        instance = client.services.start(
            declaration,
            in_topic="topic://tests/manual-service-failure",
        )
        result = client.handle_service_failure(instance, error="manual-service-crash")

        assert result is None
        snapshot = client.query_service(
            instance_id=instance.instance_id,
            include_stopped=True,
        )
        assert isinstance(snapshot, dict)
        assert snapshot["status"] == "failed"
        assert snapshot["failure_reason"] == "manual-service-crash"
    finally:
        bootstrap.shutdown()