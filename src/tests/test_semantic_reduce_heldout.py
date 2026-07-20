from __future__ import annotations

from sage.workloads.semantic_reduce_heldout import (
    HELDOUT_FAMILIES,
    field_separability,
    generate_heldout_workload,
)


def test_all_frozen_heldout_families_are_deterministic_and_retain_labels_for_scorer() -> None:
    for family in HELDOUT_FAMILIES:
        first = generate_heldout_workload(family, seed=101, split="heldout")
        second = generate_heldout_workload(family, seed=101, split="heldout")
        assert first == second
        assert first.dataset.scenario == family
        assert first.dataset.incidents
        assert any(item.source_incident_id for item in first.dataset.evidence)
        assert field_separability(first)["true_evidence_count"] > 0


def test_difficult_axes_break_hint_or_score_label_proxy() -> None:
    missing = field_separability(
        generate_heldout_workload("hint-missing", seed=101, split="heldout")
    )
    errors = field_separability(
        generate_heldout_workload("hint-error-conflict", seed=101, split="heldout")
    )
    overlap = field_separability(
        generate_heldout_workload("score-overlap", seed=101, split="heldout")
    )
    assert missing["hint_coverage"] < 0.8
    assert errors["hint_correctness"] < 0.8
    assert overlap["score_balanced_accuracy"] < 0.8


def test_unseen_topology_mixed_budget_and_fragmentation_axes_are_explicit() -> None:
    unseen = generate_heldout_workload("unseen-service-topology", seed=103, split="heldout")
    mixed = generate_heldout_workload("mixed-split-merge", seed=103, split="heldout")
    budget = generate_heldout_workload("catalog-budget-truncation", seed=103, split="heldout")
    fragmented = generate_heldout_workload(
        "fragmentation-shard-variance", seed=103, split="heldout"
    )
    assert "reranker" in unseen.service_topology
    assert any(item.service == "reranker" for item in unseen.dataset.evidence)
    assert mixed.dataset.scenario == "mixed-split-merge"
    assert len(mixed.dataset.incidents) == 8
    assert budget.proposal_budget == 2
    assert fragmented.axis_metadata["fragments_per_evidence"] == 2
