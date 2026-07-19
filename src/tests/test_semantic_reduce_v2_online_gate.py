from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools/benchmark_carrier"
sys.path.insert(0, str(TOOLS))

import finalize_semantic_reduce_v2_execution_closure as closure_finalizer  # noqa: E402
import preflight_semantic_reduce_v2_online as physical_preflight  # noqa: E402
import run_semantic_reduce_edit_v2_online_matrix as online_runner  # noqa: E402
import verify_semantic_reduce_v2_online_run as online_verifier  # noqa: E402
from orchestrate_semantic_reduce_v2_authorized_run import (  # noqa: E402
    _require_unchanged,
    _scan_and_redact_log,
)
from run_semantic_reduce_edit_v2_online_matrix import (  # noqa: E402
    _expected_rows,
    _secret_hits,
    _validate_authorization,
)


def _envelopes() -> tuple[dict, dict, dict]:
    service = {
        "physical_npu": 3,
        "npu_count": 1,
        "topology": "single-device-tp1",
        "base_url": "http://127.0.0.1:18383",
        "port": 18383,
        "managed_unit": "sage-smr-v2-npu3.service",
        "container": "sage-smr-v2-npu3",
        "manager": "external/vllm-hust-dev-hub",
        "served_model_name": "qwen25-7b-semantic-reduce-v2",
        "model_path": "/models/qwen",
        "model_config_sha256": "a" * 64,
        "generation_config_sha256": "b" * 64,
    }
    protocol = {
        "repository": {"execution_commit": "c" * 40},
        "service": service,
        "reservation_shape": {
            "requested_duration_minutes": 210,
            "minimum_remaining_at_admission_minutes": 180,
        },
        "experiment": {
            "families": ["one", "two"],
            "development_seeds": [1, 2],
            "development_repeats": 2,
        },
    }
    grant = {
        "status": "GRANTED",
        "protocol_sha256": "d" * 64,
        "repository_commit": "c" * 40,
        "authorized_splits": ["development"],
        "run_ids": {"development": "run-1"},
        "issued_at_utc": (
            datetime.now(UTC) - timedelta(hours=4)
        ).isoformat(),
        "expires_utc": (
            datetime.now(UTC) + timedelta(hours=4)
        ).isoformat(),
        "allocation_start_utc": (
            datetime.now(UTC) - timedelta(hours=3)
        ).isoformat(),
        "resources": {
            "physical_npus": [3],
            "npu_count": 1,
            "topology": "single-device-tp1",
        },
        "service": {
            "base_url": service["base_url"],
            "port": service["port"],
            "managed_unit": service["managed_unit"],
            "container": service["container"],
            "manager": service["manager"],
        },
        "model": {
            "served_model_name": service["served_model_name"],
            "path": service["model_path"],
            "config_sha256": service["model_config_sha256"],
            "generation_config_sha256": service["generation_config_sha256"],
        },
    }
    preflight = {
        "status": "PASS",
        "protocol_sha256": "d" * 64,
        "repository_commit": "c" * 40,
        "grant_sha256": "e" * 64,
        "split": "development",
        "run_id": "run-1",
        "service": {
            "base_url": service["base_url"],
            "managed_unit": service["managed_unit"],
            "container": service["container"],
        },
        "checks": {
            "port_owner": "exact-grant-service",
            "port_owner_process_lineage": True,
            "device_owner": "exact-grant-container",
            "models_endpoint": "frozen-served-name-present",
            "structured_output_smoke": "strict-proposal-ids-pass",
            "raw_secret_scan": "PASS",
            "repository_clean": True,
            "submodules_clean": True,
            "conda_environment": "esage-vllm-hust-dev",
            "model_hashes_match": True,
            "frozen_source_hashes_match": True,
            "namespace_fresh": True,
            "free_space_gib": 5,
            "cleanup_armed": True,
        },
        "prelaunch_sha256": "f" * 64,
    }
    return protocol, grant, preflight


def test_exact_grant_and_preflight_bindings_pass() -> None:
    protocol, grant, preflight = _envelopes()
    _validate_authorization(
        protocol=protocol,
        protocol_sha="d" * 64,
        grant=grant,
        preflight=preflight,
        grant_sha="e" * 64,
        split="development",
        run_id="run-1",
    )


@pytest.mark.parametrize(
    ("section", "key", "bad_value"),
    [
        ("service", "base_url", "http://127.0.0.1:9999"),
        ("service", "container", "foreign-container"),
        ("model", "config_sha256", "f" * 64),
    ],
)
def test_grant_identity_drift_fails_closed(
    section: str, key: str, bad_value: object
) -> None:
    protocol, grant, preflight = _envelopes()
    changed = deepcopy(grant)
    changed[section][key] = bad_value
    with pytest.raises(ValueError, match="authorization/preflight rejected"):
        _validate_authorization(
            protocol=protocol,
            protocol_sha="d" * 64,
            grant=changed,
            preflight=preflight,
            grant_sha="e" * 64,
            split="development",
            run_id="run-1",
        )


def test_raw_secret_scanner_detects_exact_and_generic_credentials() -> None:
    assert _secret_hits({"value": "live-secret-value"}, api_key="live-secret-value")
    assert _secret_hits(
        {"Authorization": "Bearer abcdefghijklmnop"}, api_key="not-present"
    )
    assert not _secret_hits(
        {"api_key_env": "VLLM_HUST_API_KEY", "authorization": "REDACTED"},
        api_key="not-present",
    )


def test_expected_row_count_is_frozen_cartesian_product() -> None:
    protocol, _, _ = _envelopes()
    assert _expected_rows(protocol, "development") == 8


@pytest.mark.parametrize("bad_issued", [None, "2026-07-19T12:00:00"])
def test_grant_issuance_missing_or_naive_fails_closed(bad_issued: object) -> None:
    protocol, grant, preflight = _envelopes()
    grant["issued_at_utc"] = bad_issued
    with pytest.raises((ValueError, TypeError)):
        _validate_authorization(
            protocol=protocol, protocol_sha="d" * 64, grant=grant,
            preflight=preflight, grant_sha="e" * 64,
            split="development", run_id="run-1",
        )


def test_future_dated_grant_fails_closed() -> None:
    protocol, grant, preflight = _envelopes()
    grant["issued_at_utc"] = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    with pytest.raises(ValueError, match="grant-issued"):
        _validate_authorization(
            protocol=protocol, protocol_sha="d" * 64, grant=grant,
            preflight=preflight, grant_sha="e" * 64,
            split="development", run_id="run-1",
        )


def test_heldout_closure_is_rejected_before_launch_when_grant_is_early(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protocol_sha = "d" * 64
    run_id = "dev-run"
    raw = (
        tmp_path / ".sage/benchmarks/semantic_reduce_edit_v2_real_online"
        / protocol_sha / f"development-{run_id}"
    )
    raw.mkdir(parents=True)
    digests = {}
    for name in ("manifest.json", "row-ledger.json", "summary.json"):
        path = raw / name
        path.write_text("{}\n", encoding="utf-8")
        digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    closure = {
        "status": "PASS", "paper_admissible": True, "split": "development",
        "protocol_sha256": protocol_sha, "repository_commit": "c" * 40,
        "run_id": run_id, "verified_row_count": 80, "raw_root": str(raw),
        "manifest_sha256": digests["manifest.json"],
        "ledger_sha256": digests["row-ledger.json"],
        "summary_sha256": digests["summary.json"],
        "completed_utc": "2026-07-19T12:00:00Z",
    }
    closure_path = tmp_path / "development-closure.json"
    closure_path.write_text(json.dumps(closure) + "\n", encoding="utf-8")
    closure_sha = hashlib.sha256(closure_path.read_bytes()).hexdigest()
    grant = {
        "development_closure_sha256": closure_sha,
        "development_raw_root": str(raw),
        "issued_at_utc": "2026-07-19T11:59:59Z",
    }
    monkeypatch.setattr(physical_preflight, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="rejected before launch"):
        physical_preflight._validate_heldout_development_closure(
            closure_path, protocol_sha=protocol_sha, commit="c" * 40, grant=grant
        )


def test_control_log_secret_scanner_redacts_and_fails_closed(tmp_path: Path) -> None:
    log = tmp_path / "service.log"
    log.write_text(
        "header Authorization: Bearer live-secret-value footer\n", encoding="utf-8"
    )
    results: list[dict] = []
    with pytest.raises(RuntimeError, match="detected and redacted"):
        _scan_and_redact_log(log, api_key="live-secret-value", results=results)
    assert "live-secret-value" not in log.read_text(encoding="utf-8")
    assert results[0]["status"] == "FAIL_REDACTED"


def test_control_log_secret_scanner_records_clean_checksum(tmp_path: Path) -> None:
    log = tmp_path / "clean.log"
    log.write_text("service ready\n", encoding="utf-8")
    results: list[dict] = []
    _scan_and_redact_log(log, api_key="not-present", results=results)
    assert results[0]["status"] == "PASS"
    assert len(results[0]["sha256"]) == 64


def test_external_grant_mutation_fails_closed(tmp_path: Path) -> None:
    grant = tmp_path / "grant.json"
    grant.write_text('{"status":"GRANTED"}\n', encoding="utf-8")
    expected = hashlib.sha256(grant.read_bytes()).hexdigest()
    grant.write_text('{"status":"GRANTED","mutated":true}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="immutable input drift"):
        _require_unchanged(grant, expected)


def test_verifier_statistics_do_not_reuse_runner_implementation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = {
        "experiment": {"heldout_repeats": 1},
        "statistics": {"bootstrap_draws": 100, "bootstrap_seed": 9},
        "stopping_rules": {"development_max_failure_rate": 0.05},
    }
    rows = []
    for index, (family, model_f1, baseline_f1) in enumerate(
        (("family-a", 0.8, 0.5), ("family-b", 0.4, 0.6))
    ):
        model = {
            "f1": model_f1,
            "accepted_edit_count": 1,
            "merge_count": 1,
            "split_count": 1,
            "validator_outcome": "committed",
            "evidence_conserved": True,
        }
        rows.append(
            {
                "family": family,
                "seed": index,
                "selector_trace": {"outcome": "parsed"},
                "evaluation": {
                    "shared_catalog_digest_match": True,
                    "policies": {
                        "online_model_selector": model,
                        "deterministic_selector": {"f1": baseline_f1},
                    },
                },
            }
        )
    independent = online_verifier._independent_summary(rows, protocol, "heldout")
    assert independent == online_runner._summarize(rows, protocol, "heldout")
    monkeypatch.setattr(online_runner, "_clustered_ci", lambda *args, **kwargs: [9, 9])
    assert online_runner._summarize(rows, protocol, "heldout") != independent
    assert online_verifier._independent_summary(rows, protocol, "heldout") == independent


def test_final_closure_requires_and_binds_central_release_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def write(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    protocol_path = tmp_path / "protocol.json"
    queue = tmp_path / "queue"
    control = tmp_path / "control"
    raw = tmp_path / "raw"
    queue_commit = "q" * 40
    protocol = {
        "repository": {"execution_commit": "c" * 40, "path": str(tmp_path)},
        "service": {
            "physical_npu": 3, "port": 18383,
            "managed_unit": "unit.service", "container": "container",
        },
        "raw_evidence": {
            "final_closure_root": ".closures/$PROTOCOL_SHA256/$SPLIT-$RUN_ID/final-closure.json"
        },
        "central_release_ack_contract": {
            "ack_path_template": "acks/$PROTOCOL_SHA256/$SPLIT-$RUN_ID.json",
            "queue_base_commit": "b" * 40,
            "queue_authority_source_sha256": "a" * 64,
            "allowed_central_writer_ids": ["queue-writer"],
            "queue_branch": "main",
            "queue_origin_url": "git@example.org:queue.git",
        },
    }
    write(protocol_path, protocol)
    protocol_sha = digest(protocol_path)
    grant_sha = "g" * 64
    for name in ("manifest.json", "row-ledger.json", "summary.json"):
        write(raw / name, {"name": name})
    raw_inventory = {path.name: digest(path) for path in sorted(raw.iterdir())}
    write(
        control / "raw-secret-scan.json",
        {
            "status": "PASS",
            "scanned_files": [
                {"path": str(path.resolve()), "sha256": digest(path), "status": "PASS"}
                for path in sorted(raw.iterdir())
            ],
        },
    )
    write(
        control / "cleanup-observation.json",
        {
            "status": "PASS",
            "ownership_basis": {
                "unit_and_container_absent_prelaunch": True,
                "postlaunch_process_lineage_verified": True,
                "cleanup_used_only_exact_systemd_unit_and_container": True,
                "manage_sh_stop_used": False,
            },
            "observed_clear": {
                "npu": True, "port": True,
                "managed_unit_active": False, "container_present": False,
            },
        },
    )
    prelaunch = {
        "protocol_sha256": protocol_sha, "repository_commit": "c" * 40,
        "grant_sha256": grant_sha, "split": "heldout", "run_id": "run",
    }
    write(control / "prelaunch.json", prelaunch)
    write(
        control / "postlaunch.json",
        {**prelaunch, "prelaunch_sha256": digest(control / "prelaunch.json"),
         "checks": {"port_owner_process_lineage": True}},
    )
    verification = {
        "status": "PASS", "raw_root": str(raw),
        "protocol_sha256": protocol_sha, "repository_commit": "c" * 40,
        "grant_sha256": grant_sha, "split": "heldout", "verified_row_count": 200,
        "manifest_sha256": digest(raw / "manifest.json"),
        "ledger_sha256": digest(raw / "row-ledger.json"),
        "summary_sha256": digest(raw / "summary.json"),
        "secret_scan": "PASS", "summary_recomputed": True,
    }
    write(control / "verification.json", verification)
    release = {
        "status": "REQUEST_ONLY_CENTRAL_ACK_REQUIRED",
        "protocol_sha256": protocol_sha, "repository_commit": "c" * 40,
        "grant_sha256": grant_sha, "split": "heldout", "run_id": "run",
        "queue_mutation_performed": False, "cleanup": {"status": "PASS"},
        "control_secret_scan": {"status": "PENDING_FINAL_COVERAGE"},
        "release_requested_utc": "2026-07-19T12:00:00Z",
    }
    write(control / "release-request.json", release)
    inventory = {
        str(path.relative_to(control)): digest(path)
        for path in sorted(control.iterdir()) if path.name != "control-secret-scan.json"
    }
    handoff_path = control / "execution-handoff.json"
    handoff = {
        "status": "LOCAL_GATES_PASS_PENDING_CENTRAL_RELEASE_ACK",
        "paper_admissible": False, "protocol_sha256": protocol_sha,
        "repository_commit": "c" * 40, "grant_sha256": grant_sha,
        "split": "heldout", "run_id": "run", "raw_root": str(raw),
        "raw_manifest_sha256": digest(raw / "manifest.json"),
        "raw_ledger_sha256": digest(raw / "row-ledger.json"),
        "raw_summary_sha256": digest(raw / "summary.json"),
        "raw_inventory": raw_inventory, "verified_row_count": 200,
        "control_inventory": inventory,
        "release_request_sha256": digest(control / "release-request.json"),
    }
    write(handoff_path, handoff)
    coverage = {
        str(path.relative_to(control)): digest(path)
        for path in sorted(control.iterdir()) if path.name != "control-secret-scan.json"
    }
    write(
        control / "control-secret-scan.json",
        {"status": "PASS", "coverage": coverage, "expected_coverage": coverage,
         "self_exclusion": "control-secret-scan.json"},
    )
    ack_relative = f"acks/{protocol_sha}/heldout-run.json"
    ack_path = queue / ack_relative
    ack = {
        "status": "RELEASE_ACKNOWLEDGED", "protocol_sha256": protocol_sha,
        "repository_commit": "c" * 40, "grant_sha256": grant_sha,
        "release_request_sha256": digest(control / "release-request.json"),
        "split": "heldout", "run_id": "run",
        "released_resources": {"physical_npus": [3], "port": 18383,
                               "managed_unit": "unit.service", "container": "container"},
        "acknowledged_utc": "2026-07-19T12:01:00Z",
        "central_writer_id": "queue-writer", "queue_base_commit": "b" * 40,
        "queue_authority_source_sha256": "a" * 64, "queue_ack_commit": queue_commit,
    }
    write(ack_path, ack)
    output = tmp_path / ".closures" / protocol_sha / "heldout-run" / "final-closure.json"
    monkeypatch.setattr(
        closure_finalizer, "_git",
        lambda _repo, *args: (
            queue_commit if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "@{upstream}")}
            else "main" if args == ("branch", "--show-current")
            else "git@example.org:queue.git" if args == ("remote", "get-url", "origin")
            else ""
        ),
    )
    monkeypatch.setattr(
        closure_finalizer.subprocess, "check_output",
        lambda *args, **kwargs: ack_path.read_bytes(),
    )
    monkeypatch.setattr(
        sys, "argv",
        ["finalize", "--protocol", str(protocol_path),
         "--expected-protocol-sha256", protocol_sha,
         "--execution-handoff", str(handoff_path),
         "--central-release-ack", str(ack_path),
         "--central-queue-repo", str(queue), "--output", str(output)],
    )
    broken_scan = json.loads((control / "control-secret-scan.json").read_text())
    broken_scan["coverage"].pop("release-request.json")
    write(control / "control-secret-scan.json", broken_scan)
    with pytest.raises(SystemExit, match="control-secret-scan-coverage"):
        closure_finalizer.main()
    write(
        control / "control-secret-scan.json",
        {"status": "PASS", "coverage": coverage, "expected_coverage": coverage,
         "self_exclusion": "control-secret-scan.json"},
    )
    assert closure_finalizer.main() == 0
    assert json.loads(output.read_text())["paper_admissible"] is True


def test_verifier_rejects_timezone_naive_timestamps() -> None:
    with pytest.raises(SystemExit, match="timezone-aware"):
        online_verifier._timestamp("2026-07-19T12:00:00")
    assert online_verifier._timestamp("2026-07-19T12:00:00Z").utcoffset() is not None
