from __future__ import annotations

import json

import sage.workloads.large_scale_analysis as lsa
from sage.workloads.large_scale_analysis import (
    LLMStubIncidentReducer,
    MapOnlyIncidentReducer,
    OpenAICompletionIncidentReducer,
    STANDARD_OPERATORS,
    WindowAggregateIncidentReducer,
    generate_synthetic_events,
    map_shard,
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
    assert report.reducer_trace["reducer"] == "deterministic"
    assert report.workflow_trace["matched_incident_ids"]
    assert report.workflow_trace["missed_incident_ids"] == []
    assert report.workflow_trace["evidence_trace"]["candidate_count"] > 0
    assert report.cost_accounting["token_source"] == "offline-no-llm-call"


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


def test_baseline_aware_map_policy_recovers_low_baseline_latency_spike() -> None:
    tail_report = run_large_scale_analysis_workload(
        event_count=50_000,
        shard_count=16,
        seed=23,
        top_k=12,
        map_policy="tail-aware",
    )
    baseline_report = run_large_scale_analysis_workload(
        event_count=50_000,
        shard_count=16,
        seed=23,
        top_k=12,
        map_policy="baseline-aware",
    )

    assert tail_report.recall == 0.75
    assert tail_report.missed_incidents[0]["failure_type"] == "no_overlapping_map_evidence"
    assert baseline_report.recall == 1.0
    assert baseline_report.missed_incidents == []
    assert any(
        item["service"] == "router" and item["matched_incident_id"] == "incident-3"
        for item in baseline_report.detected_incidents
    )


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


def test_cli_llm_openai_reducer_writes_report(monkeypatch, tmp_path) -> None:
    class FakeOpenAIReducer(LLMStubIncidentReducer):
        name = "llm-openai"

        def __init__(self, **_kwargs: object) -> None:
            super().__init__()

    monkeypatch.setattr(lsa, "OpenAICompletionIncidentReducer", FakeOpenAIReducer)
    monkeypatch.setattr(lsa, "_api_key_from_env_or_file", lambda *_args: "unit-key")
    output = tmp_path / "report.json"

    assert (
        lsa.main(
            [
                "--events",
                "1200",
                "--shards",
                "4",
                "--seed",
                "11",
                "--top-k",
                "8",
                "--reducer",
                "llm-openai",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["reducer_name"] == "llm-openai"
    assert payload["event_count"] == 1200
    assert "detected_incidents" in payload
    assert payload["workflow_trace"]["evidence_trace"]["shard_count"] == 4
    assert payload["cost_accounting"]["total_tokens"] == 0


def test_openai_completion_reducer_parses_json_incidents() -> None:
    dataset = generate_synthetic_events(event_count=20_000, seed=7)
    summaries = [
        map_shard(shard_id, shard)
        for shard_id, shard in enumerate(partition_events(dataset.events, shard_count=8))
    ]
    reducer = OpenAICompletionIncidentReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion = lambda _prompt: """{
      "incidents": [
        {
          "service": "decode",
          "region": "npu-a",
          "start_minute": 120,
          "end_minute": 159,
          "score": 0.8,
          "signals": ["latency", "queue"],
          "evidence_ids": [0],
          "summary": "decode queue and latency evidence point to one incident"
        }
      ]
    }"""

    incidents = reducer.reduce(summaries)

    assert incidents
    assert incidents[0]["reducer"] == "llm-openai"
    assert incidents[0]["llm_model"] == "unit-test-model"
    assert incidents[0]["service"] == "decode"
    assert incidents[0]["region"] == "npu-a"
    assert reducer.trace()["model"] == "unit-test-model"
    assert reducer.cost_accounting()["token_source"] == "estimated_chars_div4"


def test_openai_completion_reducer_uses_evidence_as_source_of_truth() -> None:
    dataset = generate_synthetic_events(event_count=20_000, seed=7)
    summaries = [
        map_shard(shard_id, shard)
        for shard_id, shard in enumerate(partition_events(dataset.events, shard_count=8))
    ]
    reducer = OpenAICompletionIncidentReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion = lambda _prompt: """{
      "incidents": [
        {
          "service": "scheduler",
          "region": "npu-c",
          "start_minute": 0,
          "end_minute": 0,
          "score": 0.0,
          "signals": ["error"],
          "evidence_ids": [0, 0, 0]
        },
        {
          "service": "scheduler",
          "region": "npu-c",
          "start_minute": 0,
          "end_minute": 0,
          "score": 0.0,
          "signals": ["error"],
          "evidence_ids": [0]
        }
      ]
    }"""

    incidents = reducer.reduce(summaries)

    llm_incident = next(item for item in incidents if item["evidence_ids"] == [0, 1])
    assert llm_incident["service"] == "decode"
    assert llm_incident["region"] == "npu-a"
    assert llm_incident["start_minute"] == 120
    assert llm_incident["end_minute"] == 159
    assert set(llm_incident["signals"]) == {"error", "latency", "queue"}

    repaired_ids = {
        evidence_id
        for item in incidents
        if item.get("reducer_repair") == "coverage"
        for evidence_id in item["evidence_ids"]
    }
    assert {0, 1, 2, 3, 4}.issubset(repaired_ids)


def test_openai_completion_reducer_can_request_json_schema(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class DummyResponse:
        def __enter__(self) -> "DummyResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [{"message": {"content": "{\"incidents\": []}"}}],
                    "usage": {
                        "prompt_tokens": 11,
                        "completion_tokens": 6,
                        "total_tokens": 17,
                    },
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return DummyResponse()

    monkeypatch.setattr(lsa.urllib.request, "urlopen", fake_urlopen)
    reducer = OpenAICompletionIncidentReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
        structured_output=True,
    )

    assert reducer._completion("return json") == "{\"incidents\": []}"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["schema"]["required"] == [
        "incidents"
    ]
    assert reducer._last_response_usage["total_tokens"] == 17
