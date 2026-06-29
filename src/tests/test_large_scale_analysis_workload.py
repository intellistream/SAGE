from __future__ import annotations

from sage.workloads.large_scale_analysis import (
    generate_synthetic_events,
    partition_events,
    run_large_scale_analysis_workload,
)


def test_synthetic_workload_generation_injects_incidents() -> None:
    dataset = generate_synthetic_events(event_count=1200, seed=11, incident_count=3)

    assert len(dataset.events) == 1200
    assert len(dataset.incidents) == 3
    assert {incident.service for incident in dataset.incidents}


def test_partition_events_preserves_all_events() -> None:
    dataset = generate_synthetic_events(event_count=1024, seed=13)
    shards = partition_events(dataset.events, shard_count=8)

    assert len(shards) == 8
    assert sum(len(shard) for shard in shards) == 1024
    assert max(len(shard) for shard in shards) - min(len(shard) for shard in shards) <= 1


def test_large_scale_workload_recovers_injected_incidents() -> None:
    report = run_large_scale_analysis_workload(
        event_count=20_000,
        shard_count=8,
        seed=7,
        top_k=16,
    )

    assert report.event_count == 20_000
    assert report.shard_count == 8
    assert report.injected_incident_count >= 1
    assert report.recall >= 0.75
    assert report.f1 >= 0.45
    assert report.throughput_events_per_s > 0
    assert report.detected_incidents
