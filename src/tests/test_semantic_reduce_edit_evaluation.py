from __future__ import annotations

from sage.workloads.semantic_reduce_edit_evaluation import evaluate_workload
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
