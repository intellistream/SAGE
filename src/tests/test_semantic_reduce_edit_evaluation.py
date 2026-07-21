from __future__ import annotations

import hashlib
import json

from jsonschema import Draft202012Validator

from sage.workloads.semantic_reduce_edit_evaluation import (
    BoundedEditRuntime,
    OpenAIProposalSelector,
    SemanticGraphMergeReducer,
    evaluate_workload,
)
from sage.workloads.semantic_reduce_heldout import generate_heldout_workload


def test_fair_harness_shares_h0_and_catalog_and_reports_all_policy_layers() -> None:
    row = evaluate_workload(
        generate_heldout_workload("mixed-split-merge", seed=7, split="development")
    )
    assert row["shared_catalog_digest_match"] is True
    assert set(row["policies"]) == {
        "h0",
        "proposal_oracle",
        "deterministic_selector",
        "mock_model_selector",
        "constrained_reference",
    }
    assert row["policies"]["proposal_oracle"]["f1"] >= row["policies"]["h0"]["f1"]
    assert (
        row["policies"]["proposal_oracle"]["f1"] >= row["policies"]["deterministic_selector"]["f1"]
    )
    assert len(row["policies"]["proposal_oracle"]["selected_proposal_ids"]) <= 2
    assert row["policies"]["constrained_reference"]["permission"].startswith("full-evidence")
    assert row["policies"]["mock_model_selector"]["permission"].startswith("offline")
    assert row["proposal_coverage"]["gold_merge_pair_count"] > 0
    assert row["proposal_coverage"]["gold_split_candidate_count"] > 0


def test_policy_rows_keep_actions_validation_conservation_and_conditioned_delta() -> None:
    row = evaluate_workload(
        generate_heldout_workload("hint-error-conflict", seed=11, split="development")
    )
    for name in ("h0", "proposal_oracle", "deterministic_selector", "mock_model_selector"):
        policy = row["policies"][name]
        assert "selected_actions" in policy
        assert "accepted_edit_count" in policy
        assert "validator_outcome" in policy
        assert "evidence_conserved" in policy
        assert "f1_delta_from_h0" in policy
    assert row["proposal_coverage"]["merge_proposal_recall"] >= 0
    assert row["proposal_coverage"]["split_proposal_recall"] >= 0


class _OverBudgetSelector:
    name = "over-budget-adversarial-selector"

    def select(self, *, h0, catalog, evidence):
        del h0, evidence
        return [proposal.proposal_id for proposal in catalog.proposals[:3]]


def test_oracle_is_frozen_before_model_and_never_admits_over_budget_selection() -> None:
    row = evaluate_workload(
        generate_heldout_workload("mixed-split-merge", seed=7, split="development"),
        oracle_max_edits=2,
        model_selector=_OverBudgetSelector(),
    )
    assert len(row["policies"]["online_model_selector"]["selected_proposal_ids"]) == 3
    assert len(row["policies"]["proposal_oracle"]["selected_proposal_ids"]) <= 2
    assert row["policies"]["online_model_selector"]["selector_exact_oracle_match"] is False


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def test_real_online_selector_returns_ids_and_retains_secret_free_raw_trace(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def respond(request, timeout):
        del timeout
        captured["request"] = json.loads(request.data)
        return _Response(
            {
                "choices": [{"message": {"content": '{"proposal_ids":[]}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            }
        )

    monkeypatch.setattr(
        "urllib.request.urlopen",
        respond,
    )
    selector = OpenAIProposalSelector(
        base_url="http://127.0.0.1:18383",
        model="review-model",
        api_key="do-not-retain",
        sampling_seed=101,
    )
    row = evaluate_workload(
        generate_heldout_workload("hint-missing", seed=7, split="development"),
        model_selector=selector,
        evidence_label="real-online",
    )

    assert row["evidence_label"] == "real-online"
    assert "online_model_selector" in row["policies"]
    assert selector.last_trace["outcome"] == "parsed"
    assert "do-not-retain" not in json.dumps(selector.last_trace)
    response_format = captured["request"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["required"] == ["proposal_ids"]
    assert schema["additionalProperties"] is False
    proposal_ids = schema["properties"]["proposal_ids"]
    assert proposal_ids["type"] == "array"
    assert proposal_ids["uniqueItems"] is True
    assert proposal_ids["maxItems"] > 0
    assert proposal_ids["items"]["type"] == "string"
    assert proposal_ids["items"]["enum"]


def test_real_online_selector_emits_digest_stable_strict_selection_schema() -> None:
    workload = generate_heldout_workload("hint-missing", seed=7, split="development")
    runtime = BoundedEditRuntime(
        base_reducer=SemanticGraphMergeReducer(),
        proposal_budget=workload.proposal_budget,
        service_topology=workload.service_topology,
    )
    h0 = runtime.build_h0(workload.dataset.evidence)
    catalog = runtime.build_catalog(h0, workload.dataset.evidence)
    selector = OpenAIProposalSelector(
        base_url="http://127.0.0.1.invalid",
        model="offline",
        api_key="offline",
        sampling_seed=0,
    )

    response_format = selector.response_format(catalog)
    schema = response_format["json_schema"]["schema"]
    canonical = json.dumps(
        response_format, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    visible_ids = schema["properties"]["proposal_ids"]["items"]["enum"]
    expected_max_items = len(
        {
            candidate_id
            for proposal in catalog.proposals
            if proposal.action in {"MERGE", "SPLIT"}
            for candidate_id in proposal.candidate_ids
        }
    )

    assert (
        hashlib.sha256(canonical).hexdigest()
        == "c6c6f48e9ed07ae17a4001f07f6d11b00755df38ed3eced67fc0fb1f34e52251"
    )
    assert schema["properties"]["proposal_ids"]["maxItems"] == expected_max_items
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate({"proposal_ids": []})
    validator.validate({"proposal_ids": [visible_ids[0]]})

    rejected = (
        {},
        {"proposal_ids": [], "explanation": "not allowed"},
        {"proposal_ids": [visible_ids[0], visible_ids[0]]},
        {"proposal_ids": ["not-a-visible-proposal"]},
    )
    for payload in rejected:
        assert list(validator.iter_errors(payload)), payload


def test_strict_wire_schema_does_not_replace_conflict_validation() -> None:
    workload = generate_heldout_workload("catalog-budget-truncation", seed=7, split="development")
    runtime = BoundedEditRuntime(
        base_reducer=SemanticGraphMergeReducer(),
        proposal_budget=workload.proposal_budget,
        service_topology=workload.service_topology,
    )
    h0 = runtime.build_h0(workload.dataset.evidence)
    catalog = runtime.build_catalog(h0, workload.dataset.evidence)
    conflicting = next(
        (left.proposal_id, right.proposal_id)
        for left in catalog.proposals
        for right in catalog.proposals
        if left.proposal_id < right.proposal_id
        and left.action in {"MERGE", "SPLIT"}
        and right.action in {"MERGE", "SPLIT"}
        and set(left.candidate_ids) & set(right.candidate_ids)
    )
    schema = OpenAIProposalSelector(
        base_url="http://127.0.0.1.invalid",
        model="offline",
        api_key="offline",
        sampling_seed=0,
    ).response_format(catalog)["json_schema"]["schema"]

    # Both IDs are wire-valid. The system-owned validator, not JSON Schema,
    # must continue to reject their conflicting candidate consumption.
    Draft202012Validator(schema).validate({"proposal_ids": list(conflicting)})
    result = runtime.commit_selection(
        evidence=workload.dataset.evidence,
        h0=h0,
        catalog=catalog,
        raw_selection=conflicting,
        selector_name="schema-valid-conflict-fixture",
    )
    assert result.trace["commit_outcome"] == "rolled-back-invalid-selection"
    assert result.trace["validator_reason_code"] == "conflicting_candidate_consumption"


def test_real_online_selector_fails_closed_on_malformed_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response({"choices": [{"message": {"content": "not-json"}}]}),
    )
    selector = OpenAIProposalSelector(
        base_url="http://127.0.0.1:18383",
        model="review-model",
        api_key="secret",
        sampling_seed=103,
    )
    row = evaluate_workload(
        generate_heldout_workload("hint-missing", seed=7, split="development"),
        model_selector=selector,
        evidence_label="real-online",
    )

    assert selector.last_trace["outcome"] == "fail-closed-empty-selection"
    assert row["policies"]["online_model_selector"]["selected_proposal_ids"] == []
    assert row["policies"]["online_model_selector"]["f1_delta_from_h0"] == 0


def test_compact_prompt_keeps_complete_evidence_for_visible_proposals() -> None:
    workload = generate_heldout_workload("mixed-split-merge", seed=7, split="development")
    captured: dict[str, object] = {}

    class _CaptureSelector:
        name = "capture-selector"

        def select(self, *, h0, catalog, evidence):
            proposal = next(item for item in catalog.proposals if item.action == "SPLIT")
            selector = OpenAIProposalSelector(
                base_url="http://127.0.0.1.invalid",
                model="offline",
                api_key="offline",
                sampling_seed=0,
                visible_proposal_ids=[proposal.proposal_id],
            )
            prompt = selector.build_messages(h0=h0, catalog=catalog, evidence=evidence)[1][
                "content"
            ]
            candidate = next(
                item for item in h0.candidates if item.candidate_id in proposal.candidate_ids
            )
            captured["prompt"] = prompt
            captured["evidence_ids"] = candidate.evidence_ids
            return []

    evaluate_workload(workload, model_selector=_CaptureSelector())
    prompt = str(captured["prompt"])
    for evidence_id in captured["evidence_ids"]:
        assert f"E|{evidence_id}|" in prompt
    assert "no field or row is truncated" in prompt
