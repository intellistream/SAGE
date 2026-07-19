from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from sage.workloads.semantic_merge_analysis import (
    SemanticGraphMergeReducer,
    _hypothesis_from_evidence_group,
    generate_semantic_merge_dataset,
)
from sage.workloads.semantic_reduce_edit_runtime import (
    BoundedEditRuntime,
    CallbackProposalSelector,
    DeterministicProposalSelector,
    EditProposal,
    ProposalCatalog,
    structural_signature,
)


def _runtime(**kwargs):
    return BoundedEditRuntime(base_reducer=SemanticGraphMergeReducer(), **kwargs)


def _selector(value, *, name="mock-proposal-selector"):
    return CallbackProposalSelector(lambda _h0, _catalog, _evidence: value, name=name)


def _proposal(catalog, action, generator=None):
    return next(
        item
        for item in catalog.proposals
        if item.action == action and (generator is None or item.generator == generator)
    )


def test_true_split_executes_catalog_partition_and_conserves_evidence() -> None:
    dataset = generate_semantic_merge_dataset(
        seed=7, scenario="ambiguous-overmerge", incident_count=4
    )
    runtime = _runtime()
    h0 = runtime.build_h0(dataset.evidence)
    catalog = runtime.build_catalog(h0, dataset.evidence)
    split = _proposal(catalog, "SPLIT", "conflicting-upstream-hints")

    result = runtime.commit_selection(
        evidence=dataset.evidence,
        h0=h0,
        catalog=catalog,
        raw_selection=[split.proposal_id],
        selector_name="mock",
    )

    assert result.trace["commit_outcome"] == "committed-edits"
    assert result.trace["split_count"] == 1
    assert result.trace["merge_count"] == 0
    assert result.trace["accepted_edit_count"] == 1
    source = set(next(c for c in h0.candidates if c.candidate_id == split.candidate_ids[0]).evidence_ids)
    produced = [
        set(candidate.evidence_ids)
        for candidate in result.h1.candidates
        if set(candidate.evidence_ids) <= source
    ]
    assert {frozenset(part) for part in produced} == {
        frozenset(part) for part in split.parts
    }
    assert set().union(*produced) == source
    assert sum(len(part) for part in produced) == len(source)


@pytest.mark.parametrize(
    ("parts", "reason"),
    [
        ((('duplicate',), ('duplicate',)), "duplicate_split_evidence"),
        (((), ('placeholder',)), "split_requires_two_nonempty_parts"),
    ],
)
def test_invalid_split_plan_rolls_back(parts, reason) -> None:
    dataset = generate_semantic_merge_dataset(seed=7, scenario="ambiguous-overmerge")
    runtime = _runtime()
    h0 = runtime.build_h0(dataset.evidence)
    catalog = runtime.build_catalog(h0, dataset.evidence)
    original = _proposal(catalog, "SPLIT")
    forged = EditProposal(
        proposal_id=original.proposal_id,
        action="SPLIT",
        candidate_ids=original.candidate_ids,
        parts=parts,
        generator="malicious-test",
    )
    forged_catalog = ProposalCatalog(
        proposals=tuple(forged if p.proposal_id == forged.proposal_id else p for p in catalog.proposals),
        proposal_budget=catalog.proposal_budget,
        state_changing_total=catalog.state_changing_total,
        state_changing_retained=catalog.state_changing_retained,
        truncation_by_action=catalog.truncation_by_action,
    )
    result = runtime.commit_selection(
        evidence=dataset.evidence,
        h0=h0,
        catalog=forged_catalog,
        raw_selection=[forged.proposal_id],
        selector_name="malicious",
    )
    assert result.h1.digest == h0.digest
    assert result.trace["commit_outcome"] == "rolled-back-validation"
    assert result.trace["validator_reason_code"] == reason
    assert result.trace["accepted_edit_count"] == 0


def test_duplicate_missing_and_foreign_split_evidence_are_rejected_atomically() -> None:
    dataset = generate_semantic_merge_dataset(seed=7, scenario="ambiguous-overmerge")
    runtime = _runtime()
    h0 = runtime.build_h0(dataset.evidence)
    catalog = runtime.build_catalog(h0, dataset.evidence)
    split = _proposal(catalog, "SPLIT")
    source = list(next(c for c in h0.candidates if c.candidate_id == split.candidate_ids[0]).evidence_ids)
    variants = [
        ((tuple(source[:-1]), (source[-1], source[-1])), "duplicate_split_evidence"),
        ((tuple(source[:-2]), (source[-1],)), "missing_split_evidence"),
        ((tuple(source), ("foreign-evidence",)), "foreign_split_evidence"),
        (((source[0],),), "split_requires_two_nonempty_parts"),
    ]
    for index, (parts, reason) in enumerate(variants):
        forged = replace(split, proposal_id=f"X{index}", parts=parts)
        forged_catalog = ProposalCatalog(
            proposals=(forged,),
            proposal_budget=1,
            state_changing_total=1,
            state_changing_retained=1,
            truncation_by_action=(("MERGE", 0), ("SPLIT", 0)),
        )
        result = runtime.commit_selection(
            evidence=dataset.evidence,
            h0=h0,
            catalog=forged_catalog,
            raw_selection=[forged.proposal_id],
            selector_name="malicious",
        )
        assert result.trace["validator_reason_code"] == reason
        assert result.h1.digest == h0.digest


def test_unknown_proposal_malformed_and_request_failure_have_distinct_outcomes() -> None:
    dataset = generate_semantic_merge_dataset(seed=7, scenario="cascade")
    runtime = _runtime()
    unknown = runtime.execute(dataset.evidence, _selector("DOES-NOT-EXIST"))
    malformed = runtime.commit_selection(
        evidence=dataset.evidence,
        h0=unknown.h0,
        catalog=unknown.catalog,
        raw_selection=123,  # type: ignore[arg-type]
        selector_name="malformed",
    )

    def fail(_h0, _catalog, _evidence):
        raise RuntimeError("controlled selector failure")

    failed = runtime.execute(
        dataset.evidence, CallbackProposalSelector(fail, name="failing-model")
    )
    assert unknown.trace["commit_outcome"] == "rolled-back-invalid-selection"
    assert unknown.trace["validator_reason_code"] == "unknown_proposal_id"
    assert malformed.trace["validator_reason_code"] == "malformed_selection"
    assert failed.trace["commit_outcome"] == "preserved-request-failure"
    assert failed.trace["error_type"] == "RuntimeError"
    assert all(result.h0.digest == result.h1.digest for result in (unknown, malformed, failed))


def test_abstain_keep_and_no_proposal_are_counted_separately() -> None:
    dataset = generate_semantic_merge_dataset(seed=11, scenario="cascade")
    runtime = _runtime()
    h0 = runtime.build_h0(dataset.evidence)
    catalog = runtime.build_catalog(h0, dataset.evidence)
    abstain = _proposal(catalog, "ABSTAIN")
    keep = _proposal(catalog, "KEEP")
    results = [
        runtime.commit_selection(
            evidence=dataset.evidence,
            h0=h0,
            catalog=catalog,
            raw_selection=[abstain.proposal_id],
            selector_name="mock",
        ),
        runtime.commit_selection(
            evidence=dataset.evidence,
            h0=h0,
            catalog=catalog,
            raw_selection=[keep.proposal_id],
            selector_name="mock",
        ),
        runtime.commit_selection(
            evidence=dataset.evidence,
            h0=h0,
            catalog=catalog,
            raw_selection=[],
            selector_name="mock",
        ),
    ]
    assert [result.trace["commit_outcome"] for result in results] == [
        "preserved-abstain",
        "committed-keep",
        "preserved-no-proposal",
    ]
    assert [result.trace["abstain_count"] for result in results] == [1, 0, 0]
    assert [result.trace["keep_count"] for result in results] == [0, 1, 0]
    assert [result.trace["no_proposal_count"] for result in results] == [0, 0, 1]
    assert all(result.trace["accepted_edit_count"] == 0 for result in results)


def test_merge_conserves_exact_union() -> None:
    dataset = generate_semantic_merge_dataset(
        seed=7, scenario="ambiguous-disconnected-merge"
    )
    runtime = _runtime()
    h0 = runtime.build_h0(dataset.evidence)
    catalog = runtime.build_catalog(h0, dataset.evidence)
    merge = _proposal(catalog, "MERGE")
    sources = {
        candidate.candidate_id: set(candidate.evidence_ids) for candidate in h0.candidates
    }
    result = runtime.commit_selection(
        evidence=dataset.evidence,
        h0=h0,
        catalog=catalog,
        raw_selection=[merge.proposal_id],
        selector_name="mock",
    )
    expected = set().union(*(sources[candidate_id] for candidate_id in merge.candidate_ids))
    assert any(set(candidate.evidence_ids) == expected for candidate in result.h1.candidates)
    assert result.trace["merge_count"] == 1
    assert result.trace["accepted_edit_count"] == 1


def test_conflicting_edits_and_any_invalid_edit_roll_back_whole_batch() -> None:
    dataset = generate_semantic_merge_dataset(seed=7, scenario="ambiguous-overmerge")
    runtime = _runtime()
    h0 = runtime.build_h0(dataset.evidence)
    catalog = runtime.build_catalog(h0, dataset.evidence)
    split = _proposal(catalog, "SPLIT")
    keep = next(
        proposal
        for proposal in catalog.proposals
        if proposal.action == "KEEP" and proposal.candidate_ids == split.candidate_ids
    )
    conflict = runtime.commit_selection(
        evidence=dataset.evidence,
        h0=h0,
        catalog=catalog,
        raw_selection=[split.proposal_id, keep.proposal_id],
        selector_name="mock",
    )
    mixed_invalid = runtime.commit_selection(
        evidence=dataset.evidence,
        h0=h0,
        catalog=catalog,
        raw_selection=[split.proposal_id, "UNKNOWN"],
        selector_name="mock",
    )
    assert conflict.trace["validator_reason_code"] == "conflicting_candidate_consumption"
    assert mixed_invalid.trace["validator_reason_code"] == "unknown_proposal_id"
    assert conflict.h1.digest == mixed_invalid.h1.digest == h0.digest
    assert conflict.trace["split_count"] == 0


def test_permutation_source_label_and_id_renaming_invariance() -> None:
    dataset = generate_semantic_merge_dataset(seed=13, scenario="ambiguous-overmerge")
    runtime = _runtime()
    forward = runtime.build_h0(dataset.evidence)
    reverse_evidence = list(reversed(dataset.evidence))
    reverse = runtime.build_h0(reverse_evidence)
    stripped = [replace(item, source_incident_id=None) for item in dataset.evidence]
    stripped_state = runtime.build_h0(stripped)
    assert forward.digest == reverse.digest == stripped_state.digest
    assert (
        runtime.build_catalog(forward, dataset.evidence).digest
        == runtime.build_catalog(reverse, reverse_evidence).digest
        == runtime.build_catalog(stripped_state, stripped).digest
    )

    renamed = [
        replace(item, evidence_id=f"renamed-{index:03d}", source_incident_id="permuted-label")
        for index, item in enumerate(dataset.evidence)
    ]
    renamed_state = runtime.build_h0(renamed)
    assert structural_signature(forward, dataset.evidence) == structural_signature(
        renamed_state, renamed
    )


def test_catalog_budget_is_deterministic_and_records_truncation() -> None:
    dataset = generate_semantic_merge_dataset(seed=7, scenario="cascade")
    runtime = _runtime(proposal_budget=1)
    h0 = runtime.build_h0(dataset.evidence)
    first = runtime.build_catalog(h0, dataset.evidence)
    second = runtime.build_catalog(h0, list(reversed(dataset.evidence)))
    assert first.to_dict() == second.to_dict()
    assert first.digest == second.digest
    assert first.state_changing_retained <= 1
    assert sum(dict(first.truncation_by_action).values()) == (
        first.state_changing_total - first.state_changing_retained
    )


def test_checkpoint_restore_preserves_h0_catalog_selection_and_trace_digests() -> None:
    dataset = generate_semantic_merge_dataset(seed=7, scenario="ambiguous-overmerge")
    runtime = _runtime()
    h0 = runtime.build_h0(dataset.evidence)
    catalog = runtime.build_catalog(h0, dataset.evidence)
    split = _proposal(catalog, "SPLIT")
    result = runtime.commit_selection(
        evidence=dataset.evidence,
        h0=h0,
        catalog=catalog,
        raw_selection=[split.proposal_id],
        selector_name="mock",
    )
    restored = runtime.restore_checkpoint(runtime.checkpoint(result))
    assert restored["h0_digest"] == result.trace["h0_digest"]
    assert restored["proposal_catalog_digest"] == result.trace["proposal_catalog_digest"]
    assert restored["selection_digest"] == result.trace["selection_digest"]
    assert restored["trace_h1_digest"] == result.trace["h1_digest"]
    assert restored["replay_id"] == result.trace["replay_id"]


def test_catalog_and_trace_claim_only_executable_bounded_actions() -> None:
    dataset = generate_semantic_merge_dataset(seed=7, scenario="ambiguous-overmerge")
    runtime = _runtime()
    result = runtime.execute(dataset.evidence, _selector([]))
    assert result.trace["contract_version"] == "semantic-reduce/v2"
    assert set(result.trace["bounded_actions"]) == {
        proposal.action for proposal in result.catalog.proposals
    } == {"KEEP", "MERGE", "SPLIT", "ABSTAIN"}


def test_each_oracle_free_split_generator_emits_a_real_partition() -> None:
    conflict_dataset = generate_semantic_merge_dataset(
        seed=7, scenario="ambiguous-overmerge"
    )

    class SingleCandidateReducer:
        name = "single-candidate-test"

        def reduce(self, evidence):
            return [_hypothesis_from_evidence_group(evidence, reducer=self.name)]

    assert any(
        proposal.generator == "conflicting-upstream-hints"
        for proposal in _runtime()
        .build_catalog(_runtime().build_h0(conflict_dataset.evidence), conflict_dataset.evidence)
        .proposals
    )
    temporal_items = [
        replace(
            conflict_dataset.evidence[0],
            evidence_id="temporal-a",
            service="decode",
            upstream_hint="scheduler",
            start_minute=0,
            end_minute=5,
        ),
        replace(
            conflict_dataset.evidence[1],
            evidence_id="temporal-b",
            service="decode",
            upstream_hint="scheduler",
            start_minute=100,
            end_minute=105,
        ),
    ]
    temporal_runtime = BoundedEditRuntime(base_reducer=SingleCandidateReducer())
    temporal_h0 = temporal_runtime.build_h0(temporal_items)
    assert any(
        proposal.generator == "temporal-gap"
        for proposal in temporal_runtime.build_catalog(temporal_h0, temporal_items).proposals
    )

    disconnected_items = [
        replace(conflict_dataset.evidence[0], evidence_id="topology-a", service="embedding", upstream_hint=None),
        replace(conflict_dataset.evidence[1], evidence_id="topology-b", service="kv-cache", upstream_hint=None),
    ]

    topology_runtime = BoundedEditRuntime(base_reducer=SingleCandidateReducer())
    topology_h0 = topology_runtime.build_h0(disconnected_items)
    topology_catalog = topology_runtime.build_catalog(topology_h0, disconnected_items)
    topology = next(
        proposal
        for proposal in topology_catalog.proposals
        if proposal.generator == "topology-disconnected"
    )
    result = topology_runtime.commit_selection(
        evidence=disconnected_items,
        h0=topology_h0,
        catalog=topology_catalog,
        raw_selection=[topology.proposal_id],
        selector_name="mock",
    )
    assert result.trace["split_count"] == 1
    assert result.trace["commit_outcome"] == "committed-edits"


def test_independent_process_rebuilds_catalog_selection_and_committed_digest() -> None:
    dataset = generate_semantic_merge_dataset(seed=7, scenario="ambiguous-overmerge")
    runtime = _runtime()
    result = runtime.execute(dataset.evidence, DeterministicProposalSelector())
    expected = {
        key: result.trace[key]
        for key in (
            "h0_digest",
            "proposal_catalog_digest",
            "selection_digest",
            "h1_digest",
            "replay_id",
        )
    }
    code = """
import json
from sage.workloads.semantic_merge_analysis import SemanticGraphMergeReducer, generate_semantic_merge_dataset
from sage.workloads.semantic_reduce_edit_runtime import BoundedEditRuntime, DeterministicProposalSelector
d = generate_semantic_merge_dataset(seed=7, scenario='ambiguous-overmerge')
r = BoundedEditRuntime(base_reducer=SemanticGraphMergeReducer()).execute(d.evidence, DeterministicProposalSelector())
print(json.dumps({k:r.trace[k] for k in ('h0_digest','proposal_catalog_digest','selection_digest','h1_digest','replay_id')}, sort_keys=True))
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    observed = json.loads(
        subprocess.check_output(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
            text=True,
        )
    )
    assert observed == expected
