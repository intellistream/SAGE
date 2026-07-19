from __future__ import annotations

import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools/benchmark_carrier"
sys.path.insert(0, str(TOOLS))

from orchestrate_semantic_reduce_v2_authorized_run import (  # noqa: E402
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
        "expires_utc": (
            datetime.now(UTC) + timedelta(hours=1)
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
