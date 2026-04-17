from __future__ import annotations

import json
import time

import pytest

from sage.runtime.flownet import (
    SharedStateServiceDescriptor,
    SourceDeclaration,
    bootstrap_runtime,
    build_dataset_job,
    build_runtime_client,
    submit_dataset_job,
)
from sage.runtime.flownet.data.connectors import (
    ConnectorCheckpoint,
    ConnectorCheckpointStore,
    build_connector_checkpoint_handler,
    build_connector_checkpoint_scope,
    clear_connector_checkpoint,
    iter_jsonl,
    load_connector_checkpoint,
    resolve_connector_resume_offset,
    save_connector_checkpoint,
)


def _wait_for(predicate, *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition_not_met_before_timeout")


def test_shared_state_checkpoint_store_restores_jsonl_resume_offset(tmp_path) -> None:
    dataset_path = tmp_path / "orders.jsonl"
    dataset_path.write_text(
        "\n".join(
            json.dumps({"id": idx, "value": f"order-{idx}"}) for idx in range(1, 6)
        )
        + "\n",
        encoding="utf-8",
    )

    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19441")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
        descriptor = SharedStateServiceDescriptor(
            service_name="connector-checkpoints",
            namespace="team.alpha",
            owner="alice",
            visibility="private",
            reuse_policy="cross_flow",
            recovery_policy="checkpoint_restore",
        )
        client.start_shared_state_service(ConnectorCheckpointStore, descriptor=descriptor)
        store_record = client.shared_state.resolve(descriptor)
        assert store_record is not None

        scope = build_connector_checkpoint_scope(
            connector="jsonl",
            path=str(dataset_path),
            source="source://tests/orders-jsonl",
            namespace="team.alpha",
        )
        checkpoint_handler = build_connector_checkpoint_handler(
            store_record,
            scope,
            metadata={"flow": "orders"},
        )

        iterator = iter_jsonl(
            dataset_path,
            checkpoint_every=2,
            on_checkpoint=checkpoint_handler,
        )
        emitted_before_failure = [next(iterator), next(iterator), next(iterator)]
        iterator.close()

        stored_after_failure = load_connector_checkpoint(store_record, scope)
        assert stored_after_failure is not None
        assert [row["id"] for row in emitted_before_failure] == [1, 2, 3]
        assert stored_after_failure.checkpoint.cursor == 3
        assert stored_after_failure.checkpoint.rows_emitted == 3
        assert stored_after_failure.metadata == {"flow": "orders"}

        emitted_after_restart = list(
            iter_jsonl(
                dataset_path,
                resume_offset=resolve_connector_resume_offset(store_record, scope),
                checkpoint_every=2,
                on_checkpoint=checkpoint_handler,
            )
        )

        assert [row["id"] for row in emitted_after_restart] == [4, 5]

        stored_after_recovery = load_connector_checkpoint(store_record, scope)
        assert stored_after_recovery is not None
        assert stored_after_recovery.checkpoint.cursor == 5
        assert stored_after_recovery.checkpoint.rows_emitted == 2
        assert stored_after_recovery.revision >= 2
    finally:
        bootstrap.shutdown()


def test_shared_state_checkpoint_store_clear_resets_resume_offset(tmp_path) -> None:
    dataset_path = tmp_path / "events.jsonl"
    dataset_path.write_text('{"id": 1}\n', encoding="utf-8")

    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19442")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
        descriptor = SharedStateServiceDescriptor(
            service_name="connector-checkpoints-clear",
            namespace="team.alpha",
            owner="alice",
            visibility="private",
            reuse_policy="cross_flow",
            recovery_policy="checkpoint_restore",
        )
        client.start_shared_state_service(ConnectorCheckpointStore, descriptor=descriptor)
        store_record = client.shared_state.resolve(descriptor)
        assert store_record is not None

        scope = build_connector_checkpoint_scope(connector="jsonl", path=str(dataset_path))
        list(
            iter_jsonl(
                dataset_path,
                checkpoint_every=1,
                on_checkpoint=build_connector_checkpoint_handler(store_record, scope),
            )
        )

        assert resolve_connector_resume_offset(store_record, scope) == 1
        assert clear_connector_checkpoint(store_record, scope) is True
        assert resolve_connector_resume_offset(store_record, scope) == 0
    finally:
        bootstrap.shutdown()


def test_start_source_auto_injects_checkpoint_runtime_options(tmp_path) -> None:
    dataset_path = tmp_path / "auto-bind.jsonl"
    dataset_path.write_text('{"id": 1}\n', encoding="utf-8")

    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19443")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
        descriptor = SharedStateServiceDescriptor(
            service_name="connector-checkpoints-source-auto",
            namespace="team.alpha",
            owner="alice",
            visibility="private",
            reuse_policy="cross_flow",
            recovery_policy="checkpoint_restore",
        )
        client.start_shared_state_service(ConnectorCheckpointStore, descriptor=descriptor)
        store_record = client.shared_state.resolve(descriptor)
        assert store_record is not None

        source_declaration = SourceDeclaration(
            target=lambda: None,
            uri="source://tests/auto-bind",
            namespace="team.alpha",
            policies={
                "fault_tolerance": {
                    "strategy": "checkpoint",
                    "checkpoint_store_alias": "checkpoint_store",
                    "checkpoint_every": 4,
                }
            },
            dsl_name="auto_bind_source",
        ).use_shared_state("checkpoint_store", descriptor)

        checkpoint_scope = build_connector_checkpoint_scope(
            connector="source",
            path=str(dataset_path),
            source=source_declaration.uri,
            namespace="team.alpha",
        )
        save_connector_checkpoint(
            store_record,
            checkpoint_scope,
            ConnectorCheckpoint(
                connector="source",
                path=str(dataset_path),
                cursor=3,
                rows_seen=3,
                rows_emitted=3,
            ),
        )

        instance = client.sources.start(
            source_declaration,
            config={"path": str(dataset_path)},
        )

        assert instance.options["resume_offset"] == 3
        assert instance.options["checkpoint_every"] == 4
        assert instance.options["checkpoint_scope"] == checkpoint_scope
        assert callable(instance.options["on_checkpoint"])

        instance.options["on_checkpoint"](
            ConnectorCheckpoint(
                connector="source",
                path=str(dataset_path),
                cursor=4,
                rows_seen=4,
                rows_emitted=1,
            )
        )
        assert resolve_connector_resume_offset(store_record, checkpoint_scope) == 4
    finally:
        bootstrap.shutdown()


def test_dataset_job_source_auto_injects_checkpoint_resume_offset(tmp_path) -> None:
    dataset_path = tmp_path / "dataset-job.jsonl"
    dataset_path.write_text('{"id": 1}\n', encoding="utf-8")

    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19444")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
        descriptor = SharedStateServiceDescriptor(
            service_name="connector-checkpoints-dataset-job",
            namespace="team.alpha",
            owner="alice",
            visibility="private",
            reuse_policy="cross_flow",
            recovery_policy="checkpoint_restore",
        )
        client.start_shared_state_service(ConnectorCheckpointStore, descriptor=descriptor)
        store_record = client.shared_state.resolve(descriptor)
        assert store_record is not None

        source_declaration = SourceDeclaration(
            target=lambda init=None: init,
            uri="source://tests/dataset-job-auto-bind",
            namespace="team.alpha",
            policies={
                "fault_tolerance": {
                    "strategy": "checkpoint",
                    "checkpoint_store_alias": "checkpoint_store",
                }
            },
            dsl_name="dataset_job_auto_bind_source",
        ).use_shared_state("checkpoint_store", descriptor)

        plan = build_dataset_job(
            {
                "dataset": {"uri": str(dataset_path)},
                "flow": lambda init_stream: init_stream,
                "source": {"declaration": source_declaration},
                "output": {"mode": "sink", "kind": "none"},
            },
            id_factory=lambda: "dataset-job-plan",
        )
        checkpoint_scope = build_connector_checkpoint_scope(
            connector="source",
            path=str(dataset_path),
            source=plan.source["uri"],
            namespace="team.alpha",
        )
        save_connector_checkpoint(
            store_record,
            checkpoint_scope,
            ConnectorCheckpoint(
                connector="source",
                path=str(dataset_path),
                cursor=2,
                rows_seen=2,
                rows_emitted=2,
            ),
        )

        handle = submit_dataset_job(plan, client=client)
        assert handle.source_instance.options["resume_offset"] == 2
        assert handle.source_instance.options["checkpoint_scope"] == checkpoint_scope
        assert callable(handle.source_instance.options["on_checkpoint"])
    finally:
        bootstrap.shutdown()


def test_source_failure_auto_restart_reuses_checkpoint_resume_offset(tmp_path) -> None:
    dataset_path = tmp_path / "restart.jsonl"
    dataset_path.write_text('{"id": 1}\n', encoding="utf-8")

    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19445")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
        descriptor = SharedStateServiceDescriptor(
            service_name="connector-checkpoints-auto-restart",
            namespace="team.alpha",
            owner="alice",
            visibility="private",
            reuse_policy="cross_flow",
            recovery_policy="checkpoint_restore",
        )
        client.start_shared_state_service(ConnectorCheckpointStore, descriptor=descriptor)
        store_record = client.shared_state.resolve(descriptor)
        assert store_record is not None

        source_declaration = SourceDeclaration(
            target=lambda: None,
            uri="source://tests/auto-restart",
            namespace="team.alpha",
            policies={
                "fault_tolerance": {
                    "strategy": "checkpoint",
                    "checkpoint_store_alias": "checkpoint_store",
                    "auto_restart": True,
                }
            },
            dsl_name="auto_restart_source",
        ).use_shared_state("checkpoint_store", descriptor)

        checkpoint_scope = build_connector_checkpoint_scope(
            connector="source",
            path=str(dataset_path),
            source=source_declaration.uri,
            namespace="team.alpha",
        )
        save_connector_checkpoint(
            store_record,
            checkpoint_scope,
            ConnectorCheckpoint(
                connector="source",
                path=str(dataset_path),
                cursor=7,
                rows_seen=7,
                rows_emitted=7,
            ),
        )

        instance = client.sources.start(
            source_declaration,
            config={"path": str(dataset_path)},
        )
        restarted = client.handle_source_failure(instance, error="simulated-crash")

        assert restarted is not None
        assert restarted.instance_id != instance.instance_id
        assert restarted.uri == instance.uri
        assert restarted.options["resume_offset"] == 7
        assert restarted.options["restart_count"] == 1
        assert restarted.options["recovered_from_instance_id"] == instance.instance_id
        assert restarted.options["recovery_reason"] == "auto_restart"
        assert restarted.options["previous_failure_reason"] == "simulated-crash"

        failed_snapshot = client.query_source(instance_id=instance.instance_id, include_stopped=True)
        assert isinstance(failed_snapshot, dict)
        assert failed_snapshot["status"] == "failed"
        assert failed_snapshot["failure_reason"] == "simulated-crash"

        running_snapshot = client.query_source(instance_id=restarted.instance_id)
        assert isinstance(running_snapshot, dict)
        assert running_snapshot["status"] == "running"
        assert running_snapshot["failure_reason"] is None
        assert running_snapshot["recovery_policy"] == "checkpoint_restore"
        assert running_snapshot["recovery_summary"]["status"] == "checkpoint_restored"
        assert running_snapshot["recovery_summary"]["last_action"] == "checkpoint_restore"
        assert (
            running_snapshot["recovery_summary"]["metadata"]["recovered_from_instance_id"]
            == instance.instance_id
        )
    finally:
        bootstrap.shutdown()


def test_source_runner_failure_auto_restart_without_manual_hook(tmp_path) -> None:
    dataset_path = tmp_path / "runner-restart.jsonl"
    dataset_path.write_text('{"id": 1}\n', encoding="utf-8")

    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19446")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)
        descriptor = SharedStateServiceDescriptor(
            service_name="connector-checkpoints-runner-auto-restart",
            namespace="team.alpha",
            owner="alice",
            visibility="private",
            reuse_policy="cross_flow",
            recovery_policy="checkpoint_restore",
        )
        client.start_shared_state_service(ConnectorCheckpointStore, descriptor=descriptor)
        store_record = client.shared_state.resolve(descriptor)
        assert store_record is not None

        attempts: list[dict[str, object]] = []

        def flaky_source(config, options, instance) -> None:
            attempts.append(
                {
                    "instance_id": instance.instance_id,
                    "resume_offset": options.get("resume_offset"),
                    "restart_count": options.get("restart_count", 0),
                }
            )
            if len(attempts) == 1:
                raise RuntimeError("runner-crash")
            options["on_checkpoint"](
                ConnectorCheckpoint(
                    connector="source",
                    path=str(config["path"]),
                    cursor=8,
                    rows_seen=8,
                    rows_emitted=1,
                )
            )

        source_declaration = SourceDeclaration(
            target=flaky_source,
            uri="source://tests/runner-auto-restart",
            namespace="team.alpha",
            policies={
                "fault_tolerance": {
                    "strategy": "checkpoint",
                    "checkpoint_store_alias": "checkpoint_store",
                    "auto_restart": True,
                }
            },
            dsl_name="runner_auto_restart_source",
        ).use_shared_state("checkpoint_store", descriptor)

        checkpoint_scope = build_connector_checkpoint_scope(
            connector="source",
            path=str(dataset_path),
            source=source_declaration.uri,
            namespace="team.alpha",
        )
        save_connector_checkpoint(
            store_record,
            checkpoint_scope,
            ConnectorCheckpoint(
                connector="source",
                path=str(dataset_path),
                cursor=7,
                rows_seen=7,
                rows_emitted=7,
            ),
        )

        client.sources.start(
            source_declaration,
            config={"path": str(dataset_path)},
            out_topic="topic://tests/runner-auto-restart",
        )

        def _recovered() -> bool:
            records = client.query_source(uri=source_declaration.uri, include_stopped=True)
            return (
                isinstance(records, list)
                and len(records) == 2
                and records[0]["status"] == "failed"
                and records[1]["status"] == "stopped"
            )

        _wait_for(_recovered)

        records = client.query_source(uri=source_declaration.uri, include_stopped=True)
        assert isinstance(records, list)
        assert len(records) == 2
        assert attempts == [
            {
                "instance_id": records[0]["instance_id"],
                "resume_offset": 7,
                "restart_count": 0,
            },
            {
                "instance_id": records[1]["instance_id"],
                "resume_offset": 7,
                "restart_count": 1,
            },
        ]
        assert records[0]["failure_reason"] == "runner-crash"
        assert records[1]["failure_reason"] is None
        assert records[1]["options"]["recovered_from_instance_id"] == records[0]["instance_id"]
        assert records[1]["options"]["recovery_reason"] == "auto_restart"
        assert resolve_connector_resume_offset(store_record, checkpoint_scope) == 8
    finally:
        bootstrap.shutdown()


def test_source_failure_restart_policy_does_not_restore_checkpoint_state(tmp_path) -> None:
    dataset_path = tmp_path / "restart-only.jsonl"
    dataset_path.write_text('{"id": 1}\n', encoding="utf-8")

    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19446")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)

        source_declaration = SourceDeclaration(
            target=lambda: None,
            uri="source://tests/restart-only",
            namespace="team.alpha",
            policies={
                "fault_tolerance": {
                    "strategy": "restart",
                    "auto_restart": True,
                }
            },
            dsl_name="restart_only_source",
        )

        instance = client.sources.start(
            source_declaration,
            config={"path": str(dataset_path)},
        )
        restarted = client.handle_source_failure(instance, error="simulated-restart-only-crash")

        assert restarted is not None
        assert restarted.options.get("resume_offset") is None
        assert restarted.options.get("checkpoint_scope") is None
        assert restarted.options["restart_count"] == 1
        assert restarted.options["recovered_from_instance_id"] == instance.instance_id

        running_snapshot = client.query_source(instance_id=restarted.instance_id)
        assert isinstance(running_snapshot, dict)
        assert running_snapshot["recovery_policy"] == "restart"
        assert running_snapshot["recovery_summary"]["status"] == "restarted"
        assert running_snapshot["recovery_summary"]["last_action"] == "restart"
    finally:
        bootstrap.shutdown()


def test_source_checkpoint_restore_requires_checkpoint_capable_declaration(tmp_path) -> None:
    dataset_path = tmp_path / "checkpoint-required.jsonl"
    dataset_path.write_text('{"id": 1}\n', encoding="utf-8")

    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19447")
    try:
        client = build_runtime_client(owner="alice", runtime_host=bootstrap.runtime_host)

        source_declaration = SourceDeclaration(
            target=lambda: None,
            uri="source://tests/checkpoint-required-false",
            namespace="team.alpha",
            checkpoint_required=False,
            policies={"fault_tolerance": {"strategy": "checkpoint"}},
            dsl_name="checkpoint_required_false_source",
        )

        with pytest.raises(ValueError, match="source_checkpoint_restore_not_supported:.*checkpoint_required=false"):
            client.sources.start(
                source_declaration,
                config={"path": str(dataset_path)},
            )
    finally:
        bootstrap.shutdown()