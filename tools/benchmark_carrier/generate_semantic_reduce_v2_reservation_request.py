#!/usr/bin/env python3
"""Generate a request-only reservation envelope after protocol review gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from semantic_reduce_v2_request_contract import (
    CLEANUP_RELEASE_CHAIN,
    review_envelope_sha256,
    validate_request,
)

REQUIRED_REVIEW_ROLES = {
    "systems-novelty",
    "experiment-statistics-provenance",
    "artifact-fail-closed",
}
REQUIRED_PHYSICAL_LOGIC = (
    "reservation request passes the exact frozen schema, three distinct content-digest-bound SIGN envelopes with independent reviewer identities and review timestamps no later than the request, resources, clean upstream repository state, queue base, static physical gate, raw roots, cleanup chain, and non-substitution contract; grant binds its request ID and SHA, protocol SHA, execution commit, NPU3, model, service, and requested_at_utc <= issued_at_utc < request_expires_utc",
    "NPU3 has no foreign process and no conflicting container/device owner",
    "port 18383 is free before launch and owned by the exact managed service after launch",
    "repo and required submodules are clean at frozen commits and esage-vllm-hust-dev is active",
    "model config hashes match and /v1/models returns the frozen served name",
    "structured-output smoke returns strict proposal_ids JSON without a benchmark unit",
    "the exact grant-authorized split and run target root does not exist; heldout additionally requires the bound canonical development raw root and final development closure to exist and match",
    "at least 5 GiB free space and raw-log secret scanner enabled",
    "cleanup trap and central release path are armed",
    "heldout grant binds a final development closure issued before any service launch",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object: {path}")
    return payload


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _validate_source_at_commit(
    repo: Path, commit: str, path: str, expected_sha: str
) -> None:
    data = subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"])
    observed = hashlib.sha256(data).hexdigest()
    if observed != expected_sha:
        raise SystemExit(f"frozen source mismatch for {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--expected-protocol-sha256", required=True)
    parser.add_argument(
        "--review-envelope", type=Path, action="append", required=True
    )
    parser.add_argument("--queue-repo", type=Path, required=True)
    parser.add_argument("--queue-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    protocol_sha = _sha256(args.protocol)
    if protocol_sha != args.expected_protocol_sha256:
        raise SystemExit("protocol SHA mismatch")
    protocol = _load(args.protocol)
    repo = Path(protocol["repository"]["path"])
    execution_commit = protocol["repository"]["execution_commit"]
    if _git(repo, "status", "--porcelain"):
        raise SystemExit("request generation requires a clean repository")
    if _git(repo, "merge-base", "--is-ancestor", execution_commit, "HEAD"):
        raise SystemExit("execution commit is not an ancestor of the clean request commit")
    if _git(repo, "rev-list", "--left-right", "--count", "HEAD...@{upstream}") != "0\t0":
        raise SystemExit("request repository is not synchronized with upstream")
    for source in protocol["repository"]["frozen_sources"].values():
        _validate_source_at_commit(
            repo, execution_commit, source["path"], source["sha256"]
        )

    reviews = [_load(path) for path in args.review_envelope]
    roles = {review.get("role") for review in reviews}
    if len(reviews) != 3 or roles != REQUIRED_REVIEW_ROLES:
        raise SystemExit("exactly three distinct required review roles must sign")
    for review in reviews:
        if (
            review.get("decision") != "SIGN"
            or review.get("protocol_sha256") != protocol_sha
            or review.get("execution_commit") != execution_commit
            or not review.get("reviewer_id")
            or not review.get("reviewed_at_utc")
            or review.get("reviewed_frozen_sources") is not True
            or review.get("blocking_findings") != []
        ):
            raise SystemExit("review envelope rejected or SHA/commit mismatched")
    physical_logic = protocol["physical_preflight_logic"][
        "must_pass_after_central_grant_before_launch"
    ]
    if tuple(physical_logic) != REQUIRED_PHYSICAL_LOGIC:
        raise SystemExit("physical preflight logic is incomplete or drifted")
    if protocol["reservation_shape"]["no_queue_write_by_protocol_owner"] is not True:
        raise SystemExit("protocol does not forbid queue writes")

    queue_commit = _git(args.queue_repo, "rev-parse", "HEAD")
    queue_sha = _sha256(args.queue_file)
    queue_relative = str(args.queue_file.resolve().relative_to(args.queue_repo.resolve()))
    queue_tracked = bool(_git(args.queue_repo, "ls-files", queue_relative))
    expected_queue = protocol["queue_base_observation"]
    if {
        "repository": str(args.queue_repo.resolve()),
        "commit": queue_commit,
        "source_path": queue_relative,
        "source_sha256": queue_sha,
        "source_tracked_at_base_commit": queue_tracked,
    } != expected_queue:
        raise SystemExit("central queue base drifted after protocol review")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    expires = now + timedelta(
        minutes=int(protocol["reservation_shape"]["request_ttl_minutes"])
    )
    review_envelopes = [
        {"sha256": review_envelope_sha256(review), "envelope": review}
        for review in reviews
    ]
    request = {
        "schema_version": "semantic-reduce-v2-reservation-request/1",
        "request_id": f"semantic-reduce-v2-{protocol_sha[:12]}",
        "status": "REQUEST_ONLY_NOT_AUTHORIZED",
        "requested_at_utc": now.isoformat().replace("+00:00", "Z"),
        "request_expires_utc": expires.isoformat().replace("+00:00", "Z"),
        "authorization": {
            "central_grant_present": False,
            "may_modify_queue": False,
            "may_reserve_or_occupy_npu": False,
            "may_start_service": False,
        },
        "resources": {
            "npu_count": protocol["reservation_shape"]["requested_npu_count"],
            "preferred_physical_npu": protocol["reservation_shape"][
                "requested_physical_npu"
            ],
            "topology": protocol["reservation_shape"]["topology"],
            "duration_minutes": protocol["reservation_shape"][
                "requested_duration_minutes"
            ],
            "port": protocol["service"]["port"],
            "model_path": protocol["service"]["model_path"],
            "served_model_name": protocol["service"]["served_model_name"],
        },
        "repository": {
            "request_commit": _git(repo, "rev-parse", "HEAD"),
            "execution_commit": execution_commit,
            "branch": protocol["repository"]["branch"],
            "clean": True,
            "upstream_equal": True,
        },
        "protocol": {
            "path": str(args.protocol.resolve()),
            "sha256": protocol_sha,
            "status": protocol["status"],
        },
        "review_envelopes": review_envelopes,
        "physical_preflight_logic_gate": {
            "status": "PASS_STATIC_LOGIC_ONLY",
            "hardware_observed": False,
            "post_grant_checks_required_before_launch": physical_logic,
        },
        "queue_base": {
            "repository": str(args.queue_repo.resolve()),
            "commit": queue_commit,
            "source_path": queue_relative,
            "source_sha256": queue_sha,
            "source_tracked_at_base_commit": queue_tracked,
            "mutation_performed": False,
        },
        "raw_roots": protocol["raw_evidence"],
        "cleanup_release_chain": CLEANUP_RELEASE_CHAIN,
        "non_substitution": protocol["non_substitution"],
    }
    if failures := validate_request(protocol, protocol_sha, request):
        raise SystemExit("generated reservation request violates its contract: " + ",".join(failures))
    if args.output.exists():
        raise SystemExit("refusing to overwrite reservation request")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(request, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
