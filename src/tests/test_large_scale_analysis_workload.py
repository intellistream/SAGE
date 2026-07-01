from __future__ import annotations

from sage.workloads.large_scale_analysis import (
    LLMStubIncidentReducer,
    MapOnlyIncidentReducer,
    STANDARD_OPERATORS,
    WindowAggregateIncidentReducer,
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
    assert report.seed == 7
    assert report.top_k == 16
    assert report.injected_incident_count >= 1
    assert report.reducer_name == "deterministic"
    assert report.recall >= 0.75
    assert report.f1 >= 0.45
    assert report.throughput_events_per_s > 0
    assert len(report.injected_incidents) == report.injected_incident_count
    assert report.missed_incidents == []
    assert report.detected_incidents
    assert all("matched_incident_id" in item for item in report.detected_incidents)
    assert set(report.to_dict()["operator_duration_ms"]) == set(STANDARD_OPERATORS)
    assert report.to_dict()["operator_duration_ms"]["MapEvidence"] > 0


def test_large_scale_workload_accepts_llm_stub_reducer() -> None:
    report = run_large_scale_analysis_workload(
        event_count=20_000,
        shard_count=8,
        seed=7,
        top_k=16,
        reducer="llm-stub",
    )

    assert report.reducer_name == "llm-stub"
    assert report.recall >= 0.75
    assert report.f1 >= 0.45
    assert report.detected_incidents
    assert report.detected_incidents[0]["reducer"] == "llm-stub"
    assert report.detected_incidents[0]["summary"].startswith("[LLM reducer stub")
    assert all("matched_incident_id" in item for item in report.detected_incidents)


def test_large_scale_workload_accepts_diagnostic_baselines() -> None:
    map_only_report = run_large_scale_analysis_workload(
        event_count=20_000,
        shard_count=8,
        seed=7,
        top_k=16,
        reducer="map-only",
    )
    window_report = run_large_scale_analysis_workload(
        event_count=20_000,
        shard_count=8,
        seed=7,
        top_k=16,
        reducer="window-aggregate",
    )

    assert map_only_report.reducer_name == "map-only"
    assert window_report.reducer_name == "window-aggregate"
    assert map_only_report.detected_incidents
    assert window_report.detected_incidents
    assert map_only_report.precision <= window_report.precision
    assert all("matched_incident_id" in item for item in map_only_report.detected_incidents)
    assert all("matched_incident_id" in item for item in window_report.detected_incidents)


def test_large_scale_workload_accepts_reducer_instance() -> None:
    report = run_large_scale_analysis_workload(
        event_count=1200,
        shard_count=4,
        seed=11,
        top_k=8,
        reducer=LLMStubIncidentReducer(),
    )

    assert report.reducer_name == "llm-stub"
    assert len(report.injected_incidents) == report.injected_incident_count

    map_only = run_large_scale_analysis_workload(
        event_count=1200,
        shard_count=4,
        seed=11,
        top_k=8,
        reducer=MapOnlyIncidentReducer(),
    )
    window = run_large_scale_analysis_workload(
        event_count=1200,
        shard_count=4,
        seed=11,
        top_k=8,
        reducer=WindowAggregateIncidentReducer(),
    )
    assert map_only.reducer_name == "map-only"
    assert window.reducer_name == "window-aggregate"
