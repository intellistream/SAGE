"""Frozen difficult controlled workloads for bounded SemanticReduce v2.

Generation may retain hidden incident labels for scoring. Reducers, catalog
generators, and selectors receive only EvidenceObject observable fields; the v2
runtime explicitly excludes ``source_incident_id`` from policy inputs/digests.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, replace
from typing import Any

from sage.workloads.semantic_merge_analysis import (
    DEPENDENCIES,
    EvidenceObject,
    MergeDataset,
    generate_semantic_merge_dataset,
)

HELDOUT_FAMILIES = (
    "hint-missing",
    "hint-error-conflict",
    "shared-hint",
    "score-overlap",
    "related-concurrent",
    "topology-missing-stale",
    "unseen-service-topology",
    "mixed-split-merge",
    "catalog-budget-truncation",
    "fragmentation-shard-variance",
)


@dataclass(frozen=True)
class HeldoutWorkload:
    family: str
    seed: int
    split: str
    dataset: MergeDataset
    service_topology: dict[str, tuple[str, ...]]
    proposal_budget: int
    axis_metadata: dict[str, Any]


def _unit(seed: int, key: str) -> float:
    digest = hashlib.sha256(f"{seed}:{key}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64 - 1)


def _wrong_service(current: str | None, *, seed: int, key: str) -> str:
    services = ("router", "scheduler", "prefill", "decode", "kv-cache", "embedding")
    choices = [service for service in services if service != current]
    return choices[int(_unit(seed, key) * len(choices)) % len(choices)]


def _source_root(dataset: MergeDataset) -> dict[str, str]:
    return {incident.incident_id: incident.root_service for incident in dataset.incidents}


def _transform_hints(
    dataset: MergeDataset,
    *,
    seed: int,
    missing_rate: float = 0.0,
    error_rate: float = 0.0,
    shared_hint: str | None = None,
) -> MergeDataset:
    ordered_ids = sorted(item.evidence_id for item in dataset.evidence)
    missing_count = round(len(ordered_ids) * missing_rate)
    missing_ids = set(
        sorted(ordered_ids, key=lambda value: (_unit(seed, f"missing:{value}"), value))[
            :missing_count
        ]
    )
    error_candidates = [value for value in ordered_ids if value not in missing_ids]
    error_count = round(len(error_candidates) * error_rate)
    error_ids = set(
        sorted(
            error_candidates,
            key=lambda value: (_unit(seed, f"error:{value}"), value),
        )[:error_count]
    )
    evidence: list[EvidenceObject] = []
    for item in dataset.evidence:
        hint = item.upstream_hint
        if shared_hint is not None:
            hint = shared_hint
        elif item.evidence_id in missing_ids:
            hint = None
        elif item.evidence_id in error_ids:
            hint = _wrong_service(hint, seed=seed, key=item.evidence_id)
        evidence.append(replace(item, upstream_hint=hint))
    return replace(dataset, evidence=evidence)


def _score_overlap(dataset: MergeDataset, *, seed: int) -> MergeDataset:
    evidence = []
    for item in dataset.evidence:
        low, high = (0.38, 0.72) if item.source_incident_id else (0.36, 0.70)
        score = round(low + (high - low) * _unit(seed, f"score:{item.evidence_id}"), 4)
        evidence.append(replace(item, score=score))
    return replace(dataset, evidence=evidence)


def _related_concurrent(dataset: MergeDataset) -> MergeDataset:
    incident_times: dict[str, tuple[int, int]] = {}
    incidents = []
    for index, incident in enumerate(dataset.incidents):
        start = 120 + index % 2
        end = start + 42
        incident_times[incident.incident_id] = (start, end)
        incidents.append(replace(incident, region="npu-a", start_minute=start, end_minute=end))
    evidence = []
    for index, item in enumerate(dataset.evidence):
        if item.source_incident_id in incident_times:
            start, end = incident_times[str(item.source_incident_id)]
            width = max(2, min(8, end - start))
            offset = index % 3
            evidence.append(
                replace(
                    item,
                    region="npu-a",
                    start_minute=start + offset,
                    end_minute=start + offset + width,
                )
            )
        else:
            evidence.append(replace(item, region="npu-a", start_minute=124, end_minute=132))
    return replace(dataset, evidence=evidence, incidents=incidents)


def _unseen_service(dataset: MergeDataset) -> tuple[MergeDataset, dict[str, tuple[str, ...]]]:
    old = "embedding"
    new = "reranker"

    def rename_service(value: str) -> str:
        return new if value == old else value

    incidents = [
        replace(
            incident,
            root_service=rename_service(incident.root_service),
            affected_services=tuple(rename_service(value) for value in incident.affected_services),
        )
        for incident in dataset.incidents
    ]
    evidence = [
        replace(
            item,
            service=rename_service(item.service),
            upstream_hint=(rename_service(item.upstream_hint) if item.upstream_hint else None),
        )
        for item in dataset.evidence
    ]
    topology = {
        rename_service(service): tuple(rename_service(value) for value in dependents)
        for service, dependents in DEPENDENCIES.items()
    }
    topology[new] = ("router",)
    return replace(dataset, evidence=evidence, incidents=incidents), topology


def _prefixed(
    dataset: MergeDataset, *, prefix: str, region: str, minute_offset: int
) -> MergeDataset:
    incident_ids = {
        incident.incident_id: f"{prefix}-{incident.incident_id}" for incident in dataset.incidents
    }
    incidents = [
        replace(
            incident,
            incident_id=incident_ids[incident.incident_id],
            region=region,
            start_minute=incident.start_minute + minute_offset,
            end_minute=incident.end_minute + minute_offset,
        )
        for incident in dataset.incidents
    ]
    evidence = [
        replace(
            item,
            evidence_id=f"{prefix}-{item.evidence_id}",
            region=region,
            start_minute=item.start_minute + minute_offset,
            end_minute=item.end_minute + minute_offset,
            source_incident_id=(
                incident_ids.get(item.source_incident_id) if item.source_incident_id else None
            ),
        )
        for item in dataset.evidence
    ]
    return MergeDataset(evidence=evidence, incidents=incidents, scenario="mixed-split-merge")


def _mixed(seed: int, shard_count: int, incident_count: int) -> MergeDataset:
    split = _prefixed(
        generate_semantic_merge_dataset(
            seed=seed,
            shard_count=shard_count,
            incident_count=incident_count,
            scenario="ambiguous-overmerge",
        ),
        prefix="split",
        region="npu-a",
        minute_offset=0,
    )
    merge = _prefixed(
        generate_semantic_merge_dataset(
            seed=seed,
            shard_count=shard_count,
            incident_count=incident_count,
            scenario="ambiguous-disconnected-merge",
        ),
        prefix="merge",
        region="npu-c",
        minute_offset=600,
    )
    return MergeDataset(
        evidence=[*split.evidence, *merge.evidence],
        incidents=[*split.incidents, *merge.incidents],
        scenario="mixed-split-merge",
    )


def _fragment(dataset: MergeDataset, *, shard_count: int) -> MergeDataset:
    evidence: list[EvidenceObject] = []
    for index, item in enumerate(dataset.evidence):
        midpoint = (item.start_minute + item.end_minute) // 2
        evidence.extend(
            [
                replace(
                    item,
                    evidence_id=f"{item.evidence_id}-a",
                    shard_id=(index * 2) % shard_count,
                    end_minute=max(item.start_minute, midpoint),
                ),
                replace(
                    item,
                    evidence_id=f"{item.evidence_id}-b",
                    shard_id=(index * 2 + 1) % shard_count,
                    start_minute=min(item.end_minute, midpoint + 1),
                ),
            ]
        )
    random.Random(0).shuffle(evidence)
    return replace(dataset, evidence=evidence)


def generate_heldout_workload(
    family: str,
    *,
    seed: int,
    split: str,
    incident_count: int = 4,
    shard_count: int = 8,
) -> HeldoutWorkload:
    if family not in HELDOUT_FAMILIES:
        raise ValueError(f"unknown heldout family: {family}")
    topology = {key: tuple(value) for key, value in DEPENDENCIES.items()}
    proposal_budget = 64
    metadata: dict[str, Any] = {"observable_axis": family}

    if family == "mixed-split-merge":
        dataset = _mixed(seed, shard_count, incident_count)
    else:
        source_scenario = {
            "hint-missing": "cascade",
            "hint-error-conflict": "ambiguous-overmerge",
            "shared-hint": "concurrent",
            "score-overlap": "false-correlation",
            "related-concurrent": "cascade",
            "topology-missing-stale": "ambiguous-overmerge",
            "unseen-service-topology": "cascade",
            "catalog-budget-truncation": "mixed-split-merge",
            "fragmentation-shard-variance": "ambiguous-disconnected-merge",
        }[family]
        if source_scenario == "mixed-split-merge":
            dataset = _mixed(seed, shard_count, incident_count)
        else:
            dataset = generate_semantic_merge_dataset(
                seed=seed,
                shard_count=shard_count,
                incident_count=incident_count,
                scenario=source_scenario,
            )

    if family == "hint-missing":
        dataset = _transform_hints(dataset, seed=seed, missing_rate=0.65)
        metadata["hint_missing_rate"] = 0.65
    elif family == "hint-error-conflict":
        dataset = _transform_hints(dataset, seed=seed, error_rate=0.5)
        metadata["hint_error_rate"] = 0.5
    elif family == "shared-hint":
        dataset = _transform_hints(dataset, seed=seed, shared_hint="router")
        metadata["shared_hint"] = "router"
    elif family == "score-overlap":
        dataset = _score_overlap(dataset, seed=seed)
        metadata.update({"true_score_range": [0.38, 0.72], "noise_score_range": [0.36, 0.7]})
    elif family == "related-concurrent":
        dataset = _related_concurrent(dataset)
        metadata["same_region_overlapping_windows"] = True
    elif family == "topology-missing-stale":
        topology = {key: tuple(value) for key, value in DEPENDENCIES.items()}
        topology["scheduler"] = tuple(
            value for value in topology.get("scheduler", ()) if value != "decode"
        )
        topology["embedding"] = tuple(sorted({*topology.get("embedding", ()), "kv-cache"}))
        metadata.update(
            {"missing_edge": ["scheduler", "decode"], "stale_edge": ["embedding", "kv-cache"]}
        )
    elif family == "unseen-service-topology":
        dataset, topology = _unseen_service(dataset)
        metadata["unseen_service"] = "reranker"
    elif family == "catalog-budget-truncation":
        proposal_budget = 2
        metadata["proposal_budget"] = 2
    elif family == "fragmentation-shard-variance":
        dataset = _fragment(dataset, shard_count=shard_count * 2)
        metadata.update({"shard_count": shard_count * 2, "fragments_per_evidence": 2})

    # Cross the overlapping score distribution into every held-out family.
    # This adjustment was frozen after the development-only seed-7 smoke run
    # and before any held-out seed was evaluated. Hidden labels are used only
    # here in workload generation, never by H0, catalog, or selectors.
    dataset = _score_overlap(dataset, seed=seed)
    metadata["crossed_score_overlap"] = True
    dataset = replace(dataset, scenario=family)
    return HeldoutWorkload(
        family=family,
        seed=seed,
        split=split,
        dataset=dataset,
        service_topology=topology,
        proposal_budget=proposal_budget,
        axis_metadata=metadata,
    )


def field_separability(
    workload: HeldoutWorkload, *, score_threshold: float = 0.5
) -> dict[str, Any]:
    roots = _source_root(workload.dataset)
    true_items = [item for item in workload.dataset.evidence if item.source_incident_id]
    noise_items = [item for item in workload.dataset.evidence if not item.source_incident_id]
    hint_items = [item for item in true_items if item.upstream_hint]
    correct_hints = sum(
        item.upstream_hint == roots.get(str(item.source_incident_id)) for item in hint_items
    )
    true_retention = sum(item.score >= score_threshold for item in true_items) / max(
        1, len(true_items)
    )
    noise_rejection = sum(item.score < score_threshold for item in noise_items) / max(
        1, len(noise_items)
    )
    return {
        "true_evidence_count": len(true_items),
        "noise_evidence_count": len(noise_items),
        "score_threshold": score_threshold,
        "score_true_retention": round(true_retention, 6),
        "score_noise_rejection": round(noise_rejection, 6),
        "score_balanced_accuracy": round((true_retention + noise_rejection) / 2, 6),
        "hint_coverage": round(len(hint_items) / max(1, len(true_items)), 6),
        "hint_correctness": round(correct_hints / max(1, len(hint_items)), 6),
        "hint_coverage_times_correctness": round(correct_hints / max(1, len(true_items)), 6),
    }
