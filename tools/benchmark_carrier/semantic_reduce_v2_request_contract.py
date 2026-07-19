#!/usr/bin/env python3
"""Pure validation contract for a v2 request-only reservation envelope."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REQUIRED_REVIEW_ROLES = {
    "systems-novelty",
    "experiment-statistics-provenance",
    "artifact-fail-closed",
}

CLEANUP_RELEASE_CHAIN = [
    "arm scoped cleanup trap before service launch",
    "stop only the grant-named repo-owned unit/container/service",
    "verify granted NPU process table and port clear",
    "retain failure/cleanup observations in raw root",
    "send release request to the central single writer",
    "wait for central queue release acknowledgement",
    "run the SHA-bound final closure verifier over raw verification, secret scans, cleanup, release request, and central acknowledgement",
    "admit heldout only from a heldout-only grant issued after and bound to the final development closure SHA",
]

TOP_LEVEL_KEYS = {
    "schema_version", "request_id", "status", "requested_at_utc",
    "request_expires_utc", "authorization", "resources", "repository",
    "protocol", "review_envelopes", "physical_preflight_logic_gate",
    "queue_base", "raw_roots", "cleanup_release_chain", "non_substitution",
}


def _timestamp(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("request timestamp must be timezone-aware")
    return parsed


def canonical_review_envelope_bytes(envelope: dict[str, Any]) -> bytes:
    """Return the one serialization whose digest is carried by a request."""
    return json.dumps(
        envelope, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def review_envelope_sha256(envelope: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_review_envelope_bytes(envelope)).hexdigest()


def validate_request(
    protocol: dict[str, Any],
    protocol_sha256: str,
    request: dict[str, Any],
    *,
    grant_issued_at_utc: object | None = None,
) -> list[str]:
    failures: list[str] = []

    def expect(condition: bool, name: str) -> None:
        if not condition:
            failures.append(name)

    expect(set(request) == TOP_LEVEL_KEYS, "top-level-schema")
    expect(request.get("schema_version") == "semantic-reduce-v2-reservation-request/1", "schema-version")
    expect(request.get("request_id") == f"semantic-reduce-v2-{protocol_sha256[:12]}", "request-id")
    expect(request.get("status") == "REQUEST_ONLY_NOT_AUTHORIZED", "status")
    requested: datetime | None = None
    try:
        requested = _timestamp(request.get("requested_at_utc"))
        expires = _timestamp(request.get("request_expires_utc"))
        expect(expires - requested == timedelta(minutes=protocol["reservation_shape"]["request_ttl_minutes"]), "request-ttl")
        if grant_issued_at_utc is not None:
            issued = _timestamp(grant_issued_at_utc)
            expect(requested <= issued < expires, "request-grant-chronology")
    except (TypeError, ValueError, OverflowError):
        failures.append("request-timestamps")
    expect(
        request.get("authorization") == {
            "central_grant_present": False,
            "may_modify_queue": False,
            "may_reserve_or_occupy_npu": False,
            "may_start_service": False,
        },
        "authorization-denials",
    )
    service = protocol["service"]
    shape = protocol["reservation_shape"]
    expect(
        request.get("resources") == {
            "npu_count": shape["requested_npu_count"],
            "preferred_physical_npu": shape["requested_physical_npu"],
            "topology": shape["topology"],
            "duration_minutes": shape["requested_duration_minutes"],
            "port": service["port"],
            "model_path": service["model_path"],
            "served_model_name": service["served_model_name"],
        },
        "resources",
    )
    repository = request.get("repository", {})
    expect(set(repository) == {"request_commit", "execution_commit", "branch", "clean", "upstream_equal"}, "repository-schema")
    expect(bool(re.fullmatch(r"[0-9a-f]{40}", str(repository.get("request_commit", "")))), "request-commit")
    expect(repository.get("execution_commit") == protocol["repository"]["execution_commit"], "execution-commit")
    expect(repository.get("branch") == protocol["repository"]["branch"], "branch")
    expect(repository.get("clean") is True and repository.get("upstream_equal") is True, "repository-state")
    request_protocol = request.get("protocol", {})
    expect(set(request_protocol) == {"path", "sha256", "status"}, "protocol-schema")
    expect(request_protocol.get("sha256") == protocol_sha256, "protocol-sha")
    expect(request_protocol.get("status") == protocol["status"], "protocol-status")
    expect(Path(str(request_protocol.get("path", ""))).name == "v2_real_online_protocol.json", "protocol-path")

    reviews = request.get("review_envelopes")
    expect(isinstance(reviews, list) and len(reviews) == 3, "review-count")
    roles: set[object] = set()
    reviewer_ids: set[object] = set()
    review_digests: set[object] = set()
    if isinstance(reviews, list):
        for item in reviews:
            if not isinstance(item, dict) or set(item) != {"sha256", "envelope"}:
                failures.append("review-entry-schema")
                continue
            envelope = item.get("envelope")
            if not isinstance(envelope, dict):
                failures.append("review-envelope")
                continue
            declared_digest = item.get("sha256")
            review_digests.add(declared_digest)
            expect(
                bool(re.fullmatch(r"[0-9a-f]{64}", str(declared_digest or "")))
                and declared_digest == review_envelope_sha256(envelope),
                "review-sha",
            )
            roles.add(envelope.get("role"))
            reviewer_id = envelope.get("reviewer_id")
            reviewer_ids.add(reviewer_id)
            expect(envelope.get("decision") == "SIGN", "review-decision")
            expect(envelope.get("protocol_sha256") == protocol_sha256, "review-protocol")
            expect(envelope.get("execution_commit") == protocol["repository"]["execution_commit"], "review-commit")
            expect(envelope.get("reviewed_frozen_sources") is True, "review-frozen-sources")
            expect(envelope.get("blocking_findings") == [], "review-blockers")
            expect(isinstance(reviewer_id, str) and bool(reviewer_id.strip()), "review-identity")
            try:
                reviewed = _timestamp(envelope.get("reviewed_at_utc"))
                expect(requested is not None and reviewed <= requested, "review-request-chronology")
            except (TypeError, ValueError, OverflowError):
                failures.append("review-timestamp")
    expect(roles == REQUIRED_REVIEW_ROLES, "review-roles")
    expect(len(reviewer_ids) == 3, "reviewer-independence")
    expect(len(review_digests) == 3, "review-digest-independence")
    expect(
        request.get("physical_preflight_logic_gate") == {
            "status": "PASS_STATIC_LOGIC_ONLY",
            "hardware_observed": False,
            "post_grant_checks_required_before_launch": protocol["physical_preflight_logic"]["must_pass_after_central_grant_before_launch"],
        },
        "physical-preflight-logic",
    )
    expect(
        request.get("queue_base") == {
            **protocol["queue_base_observation"],
            "mutation_performed": False,
        },
        "queue-base",
    )
    expect(request.get("raw_roots") == protocol["raw_evidence"], "raw-roots")
    expect(request.get("cleanup_release_chain") == CLEANUP_RELEASE_CHAIN, "cleanup-release-chain")
    expect(request.get("non_substitution") == protocol["non_substitution"], "non-substitution")
    return failures
