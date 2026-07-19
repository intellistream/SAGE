from __future__ import annotations

import json

from sage.workloads.semantic_reduce_edit_evaluation import (
    OpenAIProposalSelector,
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
    assert row["policies"]["proposal_oracle"]["f1"] >= row["policies"][
        "deterministic_selector"
    ]["f1"]
    assert row["policies"]["proposal_oracle"]["f1"] >= row["policies"][
        "mock_model_selector"
    ]["f1"]
    assert row["policies"]["constrained_reference"]["permission"].startswith(
        "full-evidence"
    )
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
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(
            {
                "choices": [{"message": {"content": '{"proposal_ids":[]}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            }
        ),
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
    assert selector.last_trace["credentials_retained"] is False
    assert "do-not-retain" not in json.dumps(selector.last_trace)


def test_real_online_selector_fails_closed_on_malformed_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(
            {"choices": [{"message": {"content": "not-json"}}]}
        ),
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
