#!/usr/bin/env python3
"""Replay public AIOpsArena injection groups at the reducer boundary.

This is deliberately a reducer-only, label-conditioned replay.  The public
ground-truth rows are converted into one evidence object per injected instance,
without exposing the episode identifier to the reducer.  Rows sharing the
dataset's timestamp, service, failure type, and duration define one incident
episode for scoring.  The runner does not claim end-to-end anomaly detection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import zipfile
from pathlib import Path
from typing import Any

from sage.workloads.semantic_merge_analysis import (
    EvidenceObject,
    MergeIncident,
    evidence_to_dict,
    incident_to_dict,
    resolve_merge_reducer,
    score_merge_hypotheses,
)


DEFAULT_REDUCERS = "map-only,service-local,window-aggregate,hybrid-hint"


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _groundtruth_member(archive: zipfile.ZipFile) -> str:
    members = [
        name
        for name in archive.namelist()
        if name.endswith("/groundtruth/groundtruth.json")
        and not name.startswith("__MACOSX/")
    ]
    if len(members) != 1:
        raise ValueError(f"expected one groundtruth member, found {members}")
    return members[0]


def load_label_conditioned_dataset(
    archive_path: Path,
) -> tuple[list[EvidenceObject], list[MergeIncident], dict[str, Any]]:
    with zipfile.ZipFile(archive_path) as archive:
        member = _groundtruth_member(archive)
        raw = archive.read(member)
    payload = json.loads(raw)
    required = ("timestamp", "service", "cmdb_id", "failure_type", "duration")
    lengths = {name: len(payload[name]) for name in required}
    if len(set(lengths.values())) != 1:
        raise ValueError(f"groundtruth columns have inconsistent lengths: {lengths}")

    rows = [dict(zip(required, values, strict=True)) for values in zip(
        *(payload[name] for name in required), strict=True
    )]
    grouped: dict[tuple[int, str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            int(row["timestamp"]),
            str(row["service"]),
            str(row["failure_type"]),
            int(row["duration"]),
        )
        grouped.setdefault(key, []).append(row)

    incidents: list[MergeIncident] = []
    evidence: list[EvidenceObject] = []
    for episode_index, (key, episode_rows) in enumerate(sorted(grouped.items())):
        timestamp, service, failure_type, duration = key
        start_minute = timestamp // 60
        end_minute = (timestamp + duration + 59) // 60
        incidents.append(
            MergeIncident(
                incident_id=f"public-episode-{episode_index:03d}",
                root_service=service,
                region="aiopsarena-public",
                start_minute=start_minute,
                end_minute=end_minute,
                kind=failure_type,
                affected_services=(service,),
            )
        )
        for row_index, row in enumerate(sorted(episode_rows, key=lambda item: item["cmdb_id"])):
            cmdb_id = str(row["cmdb_id"])
            evidence.append(
                EvidenceObject(
                    evidence_id=f"public-e{len(evidence):03d}",
                    shard_id=int(hashlib.sha256(cmdb_id.encode()).hexdigest()[:8], 16) % 8,
                    service=service,
                    region="aiopsarena-public",
                    start_minute=start_minute,
                    end_minute=end_minute,
                    signals=(failure_type,),
                    score=1.0,
                    p95_latency_ms=0.0,
                    error_rate=0.0,
                    queue_depth=0.0,
                    npu_util=0.0,
                    upstream_hint=None,
                    source_incident_id=None,
                )
            )
    provenance = {
        "archive_sha256": _sha256(archive_path),
        "groundtruth_member": member,
        "groundtruth_sha256": hashlib.sha256(raw).hexdigest(),
        "groundtruth_rows": len(rows),
        "incident_episode_count": len(incidents),
        "grouping_key": ["timestamp", "service", "failure_type", "duration"],
    }
    return evidence, incidents, provenance


def run(archive_path: Path, reducers: list[str]) -> dict[str, Any]:
    evidence, incidents, source = load_label_conditioned_dataset(archive_path)
    results = []
    for reducer_name in reducers:
        reducer = resolve_merge_reducer(reducer_name)
        started = time.perf_counter()
        hypotheses = reducer.reduce(evidence)
        elapsed_ms = (time.perf_counter() - started) * 1000
        matched, matched_hypotheses, annotated = score_merge_hypotheses(
            hypotheses, incidents
        )
        precision = matched_hypotheses / len(hypotheses) if hypotheses else 0.0
        recall = len(matched) / len(incidents) if incidents else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        results.append(
            {
                "reducer": reducer.name,
                "hypothesis_count": len(hypotheses),
                "matched_episode_count": len(matched),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "reduce_duration_ms": round(elapsed_ms, 4),
                "hypotheses": annotated,
            }
        )
    evidence_payload = [evidence_to_dict(item) for item in evidence]
    incident_payload = [incident_to_dict(item) for item in incidents]
    return {
        "evidence_label": "replay",
        "validation_scope": "reducer-only-label-conditioned",
        "end_to_end_detection_claim": False,
        "native_incident_group_groundtruth": True,
        "label_leakage_boundary": (
            "Ground-truth rows instantiate evidence units and the scorer; "
            "episode IDs are not supplied to reducers."
        ),
        "source": source,
        "evidence": evidence_payload,
        "incident_episodes": incident_payload,
        "results": results,
        "replay": {
            "evidence_digest": _digest(evidence_payload),
            "incident_digest": _digest(incident_payload),
            "result_digest": _digest(results),
        },
        "limitations": [
            "MapEvidence is oracle/label-conditioned; this is not anomaly detection.",
            "The replay tests grouping of injected instance rows into incident episodes.",
            "It does not establish production or model-backed reducer generality.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--reducers", default=DEFAULT_REDUCERS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        args.archive,
        [item.strip() for item in args.reducers.split(",") if item.strip()],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "evidence_label": result["evidence_label"],
        "scope": result["validation_scope"],
        "episodes": result["source"]["incident_episode_count"],
        "results": result["results"],
        "output": str(args.output),
    }, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
