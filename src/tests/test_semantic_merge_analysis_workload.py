from __future__ import annotations

import json

import sage.workloads.semantic_merge_analysis as sma
from sage.workloads.semantic_merge_analysis import (
    OpenAIHybridMergeReducer,
    OpenAIHybridValidatedMergeReducer,
    OpenAIPairwiseActionValidatedMergeReducer,
    OpenAIPairwiseValidatedMergeReducer,
    OpenAISemanticMergeReducer,
    SCENARIOS,
    generate_semantic_merge_dataset,
    run_semantic_merge_workload,
)


def test_semantic_merge_dataset_contains_cross_service_incidents() -> None:
    dataset = generate_semantic_merge_dataset(seed=7, shard_count=8, scenario="cascade")

    assert dataset.incidents
    assert dataset.evidence
    assert any(len(incident.affected_services) > 1 for incident in dataset.incidents)
    assert any(item.source_incident_id for item in dataset.evidence)


def test_semantic_merge_suite_covers_representative_scenarios() -> None:
    for scenario in SCENARIOS:
        dataset = generate_semantic_merge_dataset(
            seed=7, shard_count=8, scenario=scenario
        )
        assert dataset.scenario == scenario
        assert dataset.incidents
        assert dataset.evidence
        if scenario != "single-service":
            assert any(
                len(incident.affected_services) > 1 for incident in dataset.incidents
            )


def test_semantic_graph_reducer_beats_fragment_baselines_on_hard_scenarios() -> None:
    scenarios = [
        "cascade",
        "shared-bottleneck",
        "concurrent",
        "false-correlation",
        "partial-evidence",
    ]
    semantic_scores = []
    baseline_scores = []
    for scenario in scenarios:
        map_only = run_semantic_merge_workload(
            seed=7, reducer="map-only", scenario=scenario
        )
        service_local = run_semantic_merge_workload(
            seed=7, reducer="service-local", scenario=scenario
        )
        window = run_semantic_merge_workload(
            seed=7, reducer="window-aggregate", scenario=scenario
        )
        semantic = run_semantic_merge_workload(
            seed=7, reducer="semantic-graph", scenario=scenario
        )
        baseline_scores.extend([map_only.f1, service_local.f1, window.f1])
        semantic_scores.append(semantic.f1)
        assert all(item["evidence_ids"] for item in semantic.detected_incidents)

    assert min(semantic_scores) >= 0.5
    assert sum(semantic_scores) / len(semantic_scores) > (
        sum(baseline_scores) / len(baseline_scores)
    )


def test_hybrid_hint_reducer_repairs_partial_evidence_root_hints() -> None:
    semantic_scores = []
    hybrid_scores = []
    for seed in (7, 11, 13, 17, 19, 23, 29, 31, 37, 41):
        semantic = run_semantic_merge_workload(
            seed=seed, reducer="semantic-graph", scenario="partial-evidence"
        )
        hybrid = run_semantic_merge_workload(
            seed=seed, reducer="hybrid-hint", scenario="partial-evidence"
        )
        semantic_scores.append(semantic.f1)
        hybrid_scores.append(hybrid.f1)

    assert sum(hybrid_scores) / len(hybrid_scores) > (
        sum(semantic_scores) / len(semantic_scores)
    )
    assert min(hybrid_scores) >= min(semantic_scores)


def test_ambiguous_overmerge_stresses_candidate_splitting() -> None:
    semantic = run_semantic_merge_workload(
        seed=7, reducer="semantic-graph", scenario="ambiguous-overmerge"
    )
    hybrid = run_semantic_merge_workload(
        seed=7, reducer="hybrid-hint", scenario="ambiguous-overmerge"
    )

    assert semantic.evidence_coverage == 1.0
    assert hybrid.evidence_coverage == 1.0
    assert semantic.f1 < 1.0
    assert hybrid.f1 < 1.0
    assert any(
        item["failure_type"] in {"wrong_root", "incomplete_affected_services"}
        for item in hybrid.missed_incidents
    )


def test_ambiguous_candidate_stress_scenarios_have_covered_hybrid_blind_spots() -> None:
    for scenario in ("ambiguous-disconnected-merge", "ambiguous-temporal-split"):
        semantic = run_semantic_merge_workload(
            seed=7, reducer="semantic-graph", scenario=scenario
        )
        hybrid = run_semantic_merge_workload(
            seed=7, reducer="hybrid-hint", scenario=scenario
        )

        assert semantic.evidence_coverage == 1.0
        assert hybrid.evidence_coverage == 1.0
        assert semantic.f1 < 1.0
        assert hybrid.f1 < 1.0
        assert hybrid.missed_incidents or hybrid.false_positive_incidents


def test_semantic_merge_report_records_trace_cost_and_failure_taxonomy() -> None:
    report = run_semantic_merge_workload(
        seed=7, reducer="semantic-graph", scenario="partial-evidence"
    )
    payload = report.to_dict()

    assert payload["evidence_coverage"] == 1.0
    assert 0.0 < payload["root_evidence_coverage"] < payload["evidence_coverage"]
    assert 0.0 <= payload["support_evidence_recall"] <= 1.0
    assert payload["reducer_trace"]["input_evidence_count"] == payload["evidence_count"]
    assert payload["reducer_trace"]["output_hypothesis_count"] == len(
        payload["detected_incidents"]
    )
    assert payload["cost_accounting"]["provider"] == "offline"
    assert payload["cost_accounting"]["estimated_total_tokens"] == 0
    assert payload["missed_incidents"]
    assert all(item["failure_type"] for item in payload["missed_incidents"])
    assert all("source_evidence_ids" in item for item in payload["missed_incidents"])
    assert all(
        "failure_type" in item for item in payload["false_positive_incidents"]
    )


def test_semantic_merge_cli_writes_report(tmp_path) -> None:
    output = tmp_path / "semantic-merge.json"

    assert (
        sma.main(
            [
                "--seed",
                "7",
                "--scenario",
                "shared-bottleneck",
                "--reducer",
                "semantic-graph",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["reducer_name"] == "semantic-graph"
    assert payload["scenario"] == "shared-bottleneck"
    assert payload["workflow_trace"]["dependency_graph"]


def test_openai_semantic_merge_reducer_normalizes_evidence_rows() -> None:
    dataset = generate_semantic_merge_dataset(seed=7, shard_count=8, scenario="cascade")
    reducer = OpenAISemanticMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion = lambda _prompt: json.dumps(
        {
            "incidents": [
                {
                    "root_service": "scheduler",
                    "region": "npu-c",
                    "evidence_rows": [0, 1, 2],
                    "affected_services": ["scheduler", "prefill", "decode"],
                }
            ]
        }
    )

    hypotheses = reducer.reduce(dataset.evidence)

    assert hypotheses
    assert hypotheses[0]["reducer"] == "llm-openai"
    assert hypotheses[0]["llm_model"] == "unit-test-model"
    assert hypotheses[0]["evidence_ids"]
    assert reducer.last_call["input_evidence_count"] > 0


def test_openai_semantic_merge_reducer_records_schema_failure() -> None:
    dataset = generate_semantic_merge_dataset(seed=7, shard_count=8, scenario="cascade")
    reducer = OpenAISemanticMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion = lambda _prompt: json.dumps({"edits": []})

    hypotheses = reducer.reduce(dataset.evidence)

    assert hypotheses == []
    assert reducer.last_call["json_valid"] is False
    assert reducer.last_call["schema_valid"] is False
    assert reducer.last_call["error_type"] == "RuntimeError"


def test_openai_hybrid_merge_reducer_edits_graph_candidates_only() -> None:
    dataset = generate_semantic_merge_dataset(
        seed=7, shard_count=8, scenario="partial-evidence"
    )
    reducer = OpenAIHybridMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion = lambda _prompt: json.dumps(
        {
            "edits": [
                {
                    "candidate": 0,
                    "action": "keep",
                    "root_service": "scheduler",
                    "affected_services": ["scheduler", "prefill", "decode"],
                }
            ]
        }
    )

    hypotheses = reducer.reduce(dataset.evidence)

    assert hypotheses
    assert all(item["reducer"] == "llm-hybrid" for item in hypotheses)
    assert hypotheses[0]["llm_model"] == "unit-test-model"
    assert reducer.last_call["input_candidate_count"] < len(dataset.evidence)
    assert reducer.last_call["edit_trace"]
    assert reducer.last_call["estimated_total_tokens"] > 0


def test_openai_hybrid_validated_reducer_repairs_or_falls_back() -> None:
    dataset = generate_semantic_merge_dataset(
        seed=7, shard_count=8, scenario="partial-evidence"
    )
    reducer = OpenAIHybridValidatedMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion = lambda _prompt: json.dumps(
        {
            "edits": [
                {
                    "candidate": 0,
                    "action": "drop",
                    "reason": "bad model decision",
                },
                {
                    "candidate": 1,
                    "action": "keep",
                    "root_service": "embedding",
                    "affected_services": ["decode", "embedding"],
                },
            ]
        }
    )

    hypotheses = reducer.reduce(dataset.evidence)

    assert hypotheses
    assert all(item["reducer"] == "llm-hybrid-validated" for item in hypotheses)
    assert reducer.last_call["schema_valid"] is True
    assert reducer.last_call["validation_trace"]["enabled"] is True
    assert any(
        item["action"] == "drop-suppressed"
        for item in reducer.last_call["edit_trace"]
    )
    assert len(hypotheses) >= reducer.last_call["input_candidate_count"]
    assert reducer.last_call["fallback_count"] == 0


def test_openai_hybrid_validated_reducer_falls_back_on_bad_schema() -> None:
    dataset = generate_semantic_merge_dataset(
        seed=7, shard_count=8, scenario="partial-evidence"
    )
    reducer = OpenAIHybridValidatedMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion = lambda _prompt: json.dumps({"incidents": []})

    hypotheses = reducer.reduce(dataset.evidence)

    assert hypotheses
    assert all(item["reducer"] == "llm-hybrid-validated" for item in hypotheses)
    assert any(item.get("llm_fallback") for item in hypotheses)
    assert reducer.last_call["json_valid"] is False
    assert reducer.last_call["schema_valid"] is False
    assert reducer.last_call["fallback_count"] == 1


def test_openai_hybrid_validated_reducer_accepts_evidence_bounded_split() -> None:
    dataset = generate_semantic_merge_dataset(
        seed=7, shard_count=8, scenario="ambiguous-overmerge", incident_count=4
    )
    root_by_source: dict[str, str] = {}
    affected_by_source: dict[str, list[str]] = {}
    for incident in dataset.incidents:
        root_by_source[incident.incident_id] = incident.root_service
        affected_by_source[incident.incident_id] = list(incident.affected_services)
    evidence_by_id = {evidence.evidence_id: evidence for evidence in dataset.evidence}
    graph_candidates = sma.SemanticGraphMergeReducer().reduce(dataset.evidence)
    edits = []
    for candidate_index, candidate in enumerate(graph_candidates):
        by_source: dict[str, list[str]] = {}
        for evidence_id in candidate.get("evidence_ids", []):
            evidence = evidence_by_id[str(evidence_id)]
            if evidence.source_incident_id:
                by_source.setdefault(evidence.source_incident_id, []).append(
                    evidence.evidence_id
                )
        if len(by_source) <= 1:
            edits.append({"candidate": candidate_index, "action": "keep"})
            continue
        edits.append(
            {
                "candidate": candidate_index,
                "action": "split",
                "parts": [
                    {
                        "evidence_ids": sorted(evidence_ids),
                        "root_service": root_by_source[incident_id],
                        "affected_services": affected_by_source[incident_id],
                    }
                    for incident_id, evidence_ids in sorted(by_source.items())
                ],
            }
        )

    reducer = OpenAIHybridValidatedMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion = lambda _prompt: json.dumps({"edits": edits})

    report = sma.run_semantic_merge_workload(
        seed=7,
        shard_count=8,
        incident_count=4,
        scenario="ambiguous-overmerge",
        reducer=reducer,
    )

    assert report.f1 == 1.0
    assert report.support_evidence_recall == 1.0
    assert reducer.last_call["split_count"] == 1
    assert reducer.last_call["fallback_count"] == 0


def test_openai_hybrid_validated_reducer_accepts_evidence_preserving_merge() -> None:
    dataset = generate_semantic_merge_dataset(
        seed=7,
        shard_count=8,
        scenario="ambiguous-disconnected-merge",
        incident_count=4,
    )
    graph_candidates = sma.SemanticGraphMergeReducer().reduce(dataset.evidence)
    evidence_by_id = {evidence.evidence_id: evidence for evidence in dataset.evidence}
    source_by_candidate: list[str | None] = []
    for candidate in graph_candidates:
        source_ids = {
            evidence_by_id[str(evidence_id)].source_incident_id
            for evidence_id in candidate.get("evidence_ids", [])
            if str(evidence_id) in evidence_by_id
            and evidence_by_id[str(evidence_id)].source_incident_id
        }
        source_by_candidate.append(next(iter(source_ids)) if len(source_ids) == 1 else None)

    edits = []
    consumed: set[int] = set()
    incident_by_id = {incident.incident_id: incident for incident in dataset.incidents}
    for candidate_index, source_id in enumerate(source_by_candidate):
        if candidate_index in consumed:
            continue
        merge_indices = [
            idx for idx, other_source in enumerate(source_by_candidate)
            if other_source == source_id and source_id
        ]
        if len(merge_indices) > 1 and source_id:
            incident = incident_by_id[source_id]
            edits.append(
                {
                    "candidate": candidate_index,
                    "action": "merge",
                    "candidates": merge_indices,
                    "root_service": incident.root_service,
                    "affected_services": list(incident.affected_services),
                }
            )
            consumed.update(merge_indices)
        else:
            edits.append({"candidate": candidate_index, "action": "keep"})

    reducer = OpenAIHybridValidatedMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion = lambda _prompt: json.dumps({"edits": edits})

    hybrid = run_semantic_merge_workload(
        seed=7,
        shard_count=8,
        incident_count=4,
        scenario="ambiguous-disconnected-merge",
        reducer="hybrid-hint",
    )
    report = sma.run_semantic_merge_workload(
        seed=7,
        shard_count=8,
        incident_count=4,
        scenario="ambiguous-disconnected-merge",
        reducer=reducer,
    )

    assert report.f1 > hybrid.f1
    assert report.f1 == 1.0
    assert reducer.last_call["merge_count"] >= 1
    assert reducer.last_call["accepted_edit_count"] >= reducer.last_call["merge_count"]
    assert reducer.last_call["fallback_count"] == 0


def test_openai_pairwise_validated_reducer_accepts_constrained_merge() -> None:
    dataset = generate_semantic_merge_dataset(
        seed=7,
        shard_count=8,
        scenario="ambiguous-disconnected-merge",
        incident_count=4,
    )
    graph_candidates = sma.SemanticGraphMergeReducer().reduce(dataset.evidence)
    evidence_by_id = {evidence.evidence_id: evidence for evidence in dataset.evidence}
    source_by_candidate: list[str | None] = []
    for candidate in graph_candidates:
        source_ids = {
            evidence_by_id[str(evidence_id)].source_incident_id
            for evidence_id in candidate.get("evidence_ids", [])
            if str(evidence_id) in evidence_by_id
            and evidence_by_id[str(evidence_id)].source_incident_id
        }
        source_by_candidate.append(next(iter(source_ids)) if len(source_ids) == 1 else None)

    reducer = OpenAIPairwiseValidatedMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )

    def pairwise_completion(prompt: str) -> str:
        assert "\"Pairs\"" not in prompt
        payload = json.loads(prompt.split("Pairs: ", 1)[1])
        decisions = []
        for pair in payload:
            left, right = pair["candidates"]
            action = (
                "merge"
                if source_by_candidate[left]
                and source_by_candidate[left] == source_by_candidate[right]
                else "keep"
            )
            decisions.append(
                {
                    "pair": pair["pair"],
                    "action": action,
                    "evidence_ids": pair["evidence_ids"],
                    "reason": "same source hint" if action == "merge" else "separate",
                }
            )
        return json.dumps({"decisions": decisions})

    reducer._completion = pairwise_completion

    hybrid = run_semantic_merge_workload(
        seed=7,
        shard_count=8,
        incident_count=4,
        scenario="ambiguous-disconnected-merge",
        reducer="hybrid-hint",
    )
    report = sma.run_semantic_merge_workload(
        seed=7,
        shard_count=8,
        incident_count=4,
        scenario="ambiguous-disconnected-merge",
        reducer=reducer,
    )

    assert report.f1 > hybrid.f1
    assert report.f1 == 1.0
    assert reducer.last_call["input_pair_count"] > 0
    assert reducer.last_call["merge_count"] >= 1
    assert reducer.last_call["accepted_edit_count"] == reducer.last_call["merge_count"]
    assert reducer.last_call["fallback_count"] == 0


def test_openai_pairwise_action_validated_reducer_assembles_legal_edits() -> None:
    dataset = generate_semantic_merge_dataset(
        seed=7,
        shard_count=8,
        scenario="ambiguous-disconnected-merge",
        incident_count=4,
    )
    reducer = OpenAIPairwiseActionValidatedMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion_action = lambda prompt: (
        "MERGE" if '"same_upstream_hint": true' in prompt else "KEEP"
    )

    hybrid = run_semantic_merge_workload(
        seed=7,
        shard_count=8,
        incident_count=4,
        scenario="ambiguous-disconnected-merge",
        reducer="hybrid-hint",
    )
    report = sma.run_semantic_merge_workload(
        seed=7,
        shard_count=8,
        incident_count=4,
        scenario="ambiguous-disconnected-merge",
        reducer=reducer,
    )

    assert report.f1 > hybrid.f1
    assert report.f1 == 1.0
    assert reducer.last_call["json_valid"] is True
    assert reducer.last_call["schema_valid"] is True
    assert reducer.last_call["fallback_count"] == 0
    assert reducer.last_call["merge_count"] >= 1
    assert reducer.last_call["accepted_edit_count"] == reducer.last_call["merge_count"]
    assert reducer.last_call["action_trace"]
    assert reducer.last_call["raw_response_retained"] is True
    assert reducer.last_call["temperature"] == 0.0
    assert reducer.last_call["request_trace"]
    assert all(item["status"] == "ok" for item in reducer.last_call["request_trace"])
    assert all(item["response_text"] in {"KEEP", "MERGE"} for item in reducer.last_call["request_trace"])
    assert all(item["provider_response"] is None for item in reducer.last_call["request_trace"])
    assert reducer.last_call["provider_usage_available"] is False
    assert reducer.last_call["provider_total_tokens"] is None
    assert reducer.last_call["token_measurement_source"] == "char-estimate"


def test_provider_usage_is_summed_across_bounded_action_requests() -> None:
    usage = sma._provider_usage_from_request_trace(
        [
            {
                "provider_response": {
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 2,
                        "total_tokens": 12,
                    }
                }
            },
            {
                "provider_response": {
                    "usage": {
                        "prompt_tokens": 11,
                        "completion_tokens": 1,
                        "total_tokens": 12,
                    }
                }
            },
        ]
    )

    assert usage == {
        "provider_usage_available": True,
        "provider_prompt_tokens": 21,
        "provider_response_tokens": 3,
        "provider_total_tokens": 24,
        "token_measurement_source": "provider-usage",
    }


def test_openai_pairwise_action_invalid_output_abstains_without_fallback() -> None:
    reducer = OpenAIPairwiseActionValidatedMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )
    reducer._completion_action = lambda prompt: "I am not sure; maybe combine them?"

    report = sma.run_semantic_merge_workload(
        seed=7,
        shard_count=8,
        incident_count=4,
        scenario="ambiguous-disconnected-merge",
        reducer=reducer,
    )

    assert report.detected_incident_count > 0
    assert reducer.last_call["fallback_count"] == 0
    assert reducer.last_call["invalid_action_count"] == reducer.last_call[
        "input_pair_count"
    ]
    assert reducer.last_call["accepted_edit_count"] == 0
    assert all(
        item["action"] == "ABSTAIN" and item["valid"] is False
        for item in reducer.last_call["action_trace"]
    )


def test_openai_pairwise_action_request_failure_preserves_auditable_baseline() -> None:
    reducer = OpenAIPairwiseActionValidatedMergeReducer(
        base_url="http://example.invalid",
        model="unit-test-model",
        api_key="unit-test-key",
    )

    def fail(_prompt: str) -> str:
        raise RuntimeError("controlled endpoint failure")

    reducer._completion_action = fail
    report = sma.run_semantic_merge_workload(
        seed=7,
        shard_count=8,
        incident_count=4,
        scenario="ambiguous-disconnected-merge",
        reducer=reducer,
    )

    contract = reducer.last_call["contract_trace"]
    assert report.detected_incident_count > 0
    assert reducer.last_call["fallback_count"] == 1
    assert reducer.last_call["request_trace"][0]["status"] == "error"
    assert contract["validator_owned"] is True
    assert contract["commit_outcome"] == "preserved-baseline"
    assert contract["replay_id"]
