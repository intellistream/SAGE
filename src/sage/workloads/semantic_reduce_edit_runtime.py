"""Mechanism-complete bounded Edit runtime for Semantic MapReduce.

This module is intentionally separate from the legacy pairwise-action reducer.
The legacy reducer produced the frozen 2026-07-18 online artifacts and treated
SPLIT as a keep-like token.  Runtime v2 constructs finite system-owned proposal
catalogs and lets policies select proposal IDs only.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from sage.workloads.semantic_merge_analysis import (
    DEPENDENCIES,
    EvidenceObject,
    MergeReducer,
    _hypothesis_from_evidence_group,
)

CONTRACT_VERSION = "semantic-reduce/v2"
ACTION_ORDER = {"KEEP": 0, "MERGE": 1, "SPLIT": 2, "ABSTAIN": 3}


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def stable_digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def observable_evidence_dict(item: EvidenceObject) -> dict[str, Any]:
    """Return fields available to H0/catalog/policies, excluding hidden labels."""

    return {
        "evidence_id": item.evidence_id,
        "service": item.service,
        "region": item.region,
        "start_minute": item.start_minute,
        "end_minute": item.end_minute,
        "signals": sorted(item.signals),
        "score": item.score,
        "p95_latency_ms": item.p95_latency_ms,
        "error_rate": item.error_rate,
        "queue_depth": item.queue_depth,
        "npu_util": item.npu_util,
        "upstream_hint": item.upstream_hint,
    }


def _canonical_hypothesis(item: dict[str, Any]) -> dict[str, Any]:
    """Remove runtime annotations and normalize unordered hypothesis fields."""

    return {
        "root_service": str(item.get("root_service", "")),
        "region": str(item.get("region", "")),
        "start_minute": int(item.get("start_minute", 0)),
        "end_minute": int(item.get("end_minute", 0)),
        "affected_services": sorted({str(value) for value in item.get("affected_services", [])}),
        "signals": sorted({str(value) for value in item.get("signals", [])}),
        "score": round(float(item.get("score", 0.0)), 4),
        "evidence_ids": sorted({str(value) for value in item.get("evidence_ids", [])}),
        "summary": str(item.get("summary", "")),
    }


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    hypothesis: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "hypothesis": _canonical_hypothesis(self.hypothesis),
        }

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(_canonical_hypothesis(self.hypothesis)["evidence_ids"])


@dataclass(frozen=True)
class CandidateState:
    base_reducer: str
    candidates: tuple[Candidate, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_reducer": self.base_reducer,
            "candidates": [item.to_dict() for item in self.candidates],
        }

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class EditProposal:
    proposal_id: str
    action: str
    candidate_ids: tuple[str, ...] = ()
    parts: tuple[tuple[str, ...], ...] = ()
    generator: str = "system"
    metadata: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "proposal_id": self.proposal_id,
            "action": self.action,
            "candidate_ids": list(self.candidate_ids),
            "generator": self.generator,
        }
        if self.parts:
            payload["parts"] = [list(part) for part in self.parts]
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class ProposalCatalog:
    proposals: tuple[EditProposal, ...]
    proposal_budget: int
    state_changing_total: int
    state_changing_retained: int
    truncation_by_action: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "proposal_budget": self.proposal_budget,
            "state_changing_total": self.state_changing_total,
            "state_changing_retained": self.state_changing_retained,
            "truncation_by_action": dict(self.truncation_by_action),
            "proposals": [proposal.to_dict() for proposal in self.proposals],
        }

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def by_id(self) -> dict[str, EditProposal]:
        return {proposal.proposal_id: proposal for proposal in self.proposals}


@dataclass(frozen=True)
class EditRuntimeResult:
    h0: CandidateState
    h1: CandidateState
    catalog: ProposalCatalog
    selected_proposal_ids: tuple[str, ...]
    trace: dict[str, Any]

    @property
    def hypotheses(self) -> list[dict[str, Any]]:
        return [deepcopy(candidate.hypothesis) for candidate in self.h1.candidates]


class ProposalSelector(Protocol):
    name: str

    def select(
        self,
        *,
        h0: CandidateState,
        catalog: ProposalCatalog,
        evidence: Sequence[EvidenceObject],
    ) -> Sequence[str] | str | None: ...


class CallbackProposalSelector:
    """Policy adapter used by deterministic mocks and future model endpoints."""

    def __init__(
        self,
        callback: Callable[
            [CandidateState, ProposalCatalog, Sequence[EvidenceObject]],
            Sequence[str] | str | None,
        ],
        *,
        name: str,
    ) -> None:
        self.callback = callback
        self.name = name

    def select(
        self,
        *,
        h0: CandidateState,
        catalog: ProposalCatalog,
        evidence: Sequence[EvidenceObject],
    ) -> Sequence[str] | str | None:
        return self.callback(h0, catalog, evidence)


class DeterministicProposalSelector:
    """Observable-field policy over the same catalog exposed to model policies."""

    name = "deterministic-proposal-selector"

    def select(
        self,
        *,
        h0: CandidateState,
        catalog: ProposalCatalog,
        evidence: Sequence[EvidenceObject],
    ) -> Sequence[str]:
        del evidence
        selected: list[str] = []
        consumed: set[str] = set()
        # Prefer explicit ambiguity repairs. Generator priority is stable and
        # does not use scenario names, labels, or scorer callbacks.
        split_priority = {
            "conflicting-upstream-hints": 0,
            "temporal-gap": 1,
            "topology-disconnected": 2,
        }
        splits = sorted(
            (p for p in catalog.proposals if p.action == "SPLIT"),
            key=lambda p: (split_priority.get(p.generator, 99), p.proposal_id),
        )
        for proposal in splits:
            candidate_id = proposal.candidate_ids[0]
            if candidate_id not in consumed:
                selected.append(proposal.proposal_id)
                consumed.add(candidate_id)

        # Merge only when the system-computed observable relation is strong.
        merges = sorted(
            (p for p in catalog.proposals if p.action == "MERGE"),
            key=lambda p: p.proposal_id,
        )
        for proposal in merges:
            metadata = dict(proposal.metadata)
            if not bool(metadata.get("same_non_null_hint")):
                continue
            if any(candidate_id in consumed for candidate_id in proposal.candidate_ids):
                continue
            selected.append(proposal.proposal_id)
            consumed.update(proposal.candidate_ids)
        return selected


def _candidate_sort_key(hypothesis: dict[str, Any]) -> bytes:
    return _canonical_bytes(_canonical_hypothesis(hypothesis))


def _state_from_hypotheses(
    hypotheses: Iterable[dict[str, Any]], *, base_reducer: str
) -> CandidateState:
    canonical = sorted(
        (_canonical_hypothesis(item) for item in hypotheses),
        key=_candidate_sort_key,
    )
    candidates = tuple(
        Candidate(candidate_id=f"C{index}", hypothesis=item) for index, item in enumerate(canonical)
    )
    return CandidateState(base_reducer=base_reducer, candidates=candidates)


def _evidence_index(evidence: Sequence[EvidenceObject]) -> dict[str, EvidenceObject]:
    result: dict[str, EvidenceObject] = {}
    for item in evidence:
        if item.evidence_id in result:
            raise ValueError(f"duplicate evidence ID: {item.evidence_id}")
        result[item.evidence_id] = item
    return result


def _validate_state_ownership(
    state: CandidateState, evidence_by_id: dict[str, EvidenceObject]
) -> None:
    owned: set[str] = set()
    for candidate in state.candidates:
        if not candidate.evidence_ids:
            raise ValueError(f"candidate {candidate.candidate_id} has no evidence")
        for evidence_id in candidate.evidence_ids:
            if evidence_id not in evidence_by_id:
                raise ValueError(
                    f"candidate {candidate.candidate_id} has foreign evidence {evidence_id}"
                )
            if evidence_id in owned:
                raise ValueError(f"duplicate H0 evidence ownership: {evidence_id}")
            owned.add(evidence_id)


def _candidate_evidence(
    candidate: Candidate, evidence_by_id: dict[str, EvidenceObject]
) -> list[EvidenceObject]:
    return [evidence_by_id[evidence_id] for evidence_id in candidate.evidence_ids]


def _partition_key(parts: Iterable[Iterable[str]]) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted(tuple(sorted(part)) for part in parts))


def _conflicting_hint_partition(
    items: Sequence[EvidenceObject],
) -> tuple[tuple[str, ...], ...] | None:
    hints = sorted({item.upstream_hint for item in items if item.upstream_hint})
    if len(hints) < 2:
        return None
    groups: dict[str, list[str]] = {hint: [] for hint in hints}
    residual: list[str] = []
    for item in sorted(items, key=lambda value: value.evidence_id):
        if item.upstream_hint in groups:
            groups[str(item.upstream_hint)].append(item.evidence_id)
        else:
            residual.append(item.evidence_id)
    parts = [tuple(values) for _, values in sorted(groups.items()) if values]
    if residual:
        parts.append(tuple(residual))
    return _partition_key(parts) if len(parts) >= 2 else None


def _temporal_gap_partition(
    items: Sequence[EvidenceObject], *, gap_minutes: int
) -> tuple[tuple[str, ...], ...] | None:
    ordered = sorted(
        items,
        key=lambda item: (
            item.start_minute,
            item.end_minute,
            item.service,
            item.evidence_id,
        ),
    )
    if len(ordered) < 2:
        return None
    best: tuple[int, int] | None = None
    running_end = ordered[0].end_minute
    for index in range(1, len(ordered)):
        gap = ordered[index].start_minute - running_end
        if gap >= gap_minutes and (best is None or (gap, -index) > best):
            best = (gap, -index)
        running_end = max(running_end, ordered[index].end_minute)
    if best is None:
        return None
    split_index = -best[1]
    return _partition_key(
        (
            (item.evidence_id for item in ordered[:split_index]),
            (item.evidence_id for item in ordered[split_index:]),
        )
    )


def _topology_partition(
    items: Sequence[EvidenceObject],
    *,
    topology: dict[str, tuple[str, ...]],
) -> tuple[tuple[str, ...], ...] | None:
    observed = {item.service for item in items}
    adjacency: dict[str, set[str]] = {service: set() for service in observed}
    for left, rights in topology.items():
        for right in rights:
            if left in observed and right in observed:
                adjacency[left].add(right)
                adjacency[right].add(left)
    components: list[set[str]] = []
    remaining = set(observed)
    while remaining:
        start = min(remaining)
        stack = [start]
        component: set[str] = set()
        while stack:
            service = stack.pop()
            if service in component:
                continue
            component.add(service)
            stack.extend(sorted(adjacency[service] - component, reverse=True))
        remaining -= component
        components.append(component)
    if len(components) < 2:
        return None
    parts = [
        tuple(sorted(item.evidence_id for item in items if item.service in component))
        for component in sorted(components, key=lambda value: tuple(sorted(value)))
    ]
    return _partition_key(part for part in parts if part)


def _proposal_sort_key(proposal: EditProposal) -> tuple[Any, ...]:
    return (
        ACTION_ORDER[proposal.action],
        proposal.candidate_ids,
        proposal.parts,
        proposal.generator,
        proposal.metadata,
    )


def _with_ids(proposals: Sequence[EditProposal]) -> tuple[EditProposal, ...]:
    return tuple(
        EditProposal(
            proposal_id=f"A{index}",
            action=proposal.action,
            candidate_ids=proposal.candidate_ids,
            parts=proposal.parts,
            generator=proposal.generator,
            metadata=proposal.metadata,
        )
        for index, proposal in enumerate(sorted(proposals, key=_proposal_sort_key))
    )


class BoundedEditRuntime:
    """System-owned H0 -> catalog -> select -> validate -> atomic commit runtime."""

    def __init__(
        self,
        *,
        base_reducer: MergeReducer,
        proposal_budget: int = 64,
        temporal_gap_minutes: int = 20,
        service_topology: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        if proposal_budget < 0:
            raise ValueError("proposal_budget must be non-negative")
        if temporal_gap_minutes <= 0:
            raise ValueError("temporal_gap_minutes must be positive")
        self.base_reducer = base_reducer
        self.proposal_budget = proposal_budget
        self.temporal_gap_minutes = temporal_gap_minutes
        self.service_topology = {
            str(service): tuple(sorted(str(value) for value in dependents))
            for service, dependents in (service_topology or DEPENDENCIES).items()
        }

    def build_h0(self, evidence: Sequence[EvidenceObject]) -> CandidateState:
        evidence_list = sorted(evidence, key=lambda item: item.evidence_id)
        evidence_by_id = _evidence_index(evidence_list)
        hypotheses = self.base_reducer.reduce(evidence_list)
        state = _state_from_hypotheses(
            hypotheses,
            base_reducer=str(self.base_reducer.name),
        )
        _validate_state_ownership(state, evidence_by_id)
        return state

    def build_catalog(
        self,
        h0: CandidateState,
        evidence: Sequence[EvidenceObject],
    ) -> ProposalCatalog:
        evidence_by_id = _evidence_index(evidence)
        _validate_state_ownership(h0, evidence_by_id)
        passive = [
            EditProposal(
                proposal_id="",
                action="KEEP",
                candidate_ids=(candidate.candidate_id,),
                generator="system-keep",
            )
            for candidate in h0.candidates
        ]
        state_changing: list[EditProposal] = []

        for left_index, left in enumerate(h0.candidates):
            left_items = _candidate_evidence(left, evidence_by_id)
            left_regions = {item.region for item in left_items}
            left_hints = {item.upstream_hint for item in left_items if item.upstream_hint}
            for right in h0.candidates[left_index + 1 :]:
                right_items = _candidate_evidence(right, evidence_by_id)
                right_regions = {item.region for item in right_items}
                if len(left_regions | right_regions) != 1:
                    continue
                right_hints = {item.upstream_hint for item in right_items if item.upstream_hint}
                same_hint = bool(left_hints and right_hints and left_hints & right_hints)
                state_changing.append(
                    EditProposal(
                        proposal_id="",
                        action="MERGE",
                        candidate_ids=(left.candidate_id, right.candidate_id),
                        generator="candidate-pair",
                        metadata=(("same_non_null_hint", same_hint),),
                    )
                )

        generators = (
            ("conflicting-upstream-hints", _conflicting_hint_partition),
            (
                "temporal-gap",
                lambda items: _temporal_gap_partition(items, gap_minutes=self.temporal_gap_minutes),
            ),
            (
                "topology-disconnected",
                lambda items: _topology_partition(items, topology=self.service_topology),
            ),
        )
        for candidate in h0.candidates:
            items = _candidate_evidence(candidate, evidence_by_id)
            seen_partitions: set[tuple[tuple[str, ...], ...]] = set()
            for generator, build_partition in generators:
                parts = build_partition(items)
                if parts is None or len(parts) < 2 or parts in seen_partitions:
                    continue
                seen_partitions.add(parts)
                state_changing.append(
                    EditProposal(
                        proposal_id="",
                        action="SPLIT",
                        candidate_ids=(candidate.candidate_id,),
                        parts=parts,
                        generator=generator,
                    )
                )

        state_changing.sort(key=_proposal_sort_key)
        retained = state_changing[: self.proposal_budget]
        removed = state_changing[self.proposal_budget :]
        truncation = {
            action: sum(proposal.action == action for proposal in removed)
            for action in ("MERGE", "SPLIT")
        }
        all_proposals = _with_ids(
            [
                *passive,
                *retained,
                EditProposal(
                    proposal_id="",
                    action="ABSTAIN",
                    generator="system-abstain",
                ),
            ]
        )
        return ProposalCatalog(
            proposals=all_proposals,
            proposal_budget=self.proposal_budget,
            state_changing_total=len(state_changing),
            state_changing_retained=len(retained),
            truncation_by_action=tuple(sorted(truncation.items())),
        )

    def execute(
        self,
        evidence: Sequence[EvidenceObject],
        selector: ProposalSelector,
    ) -> EditRuntimeResult:
        h0 = self.build_h0(evidence)
        catalog = self.build_catalog(h0, evidence)
        try:
            raw_selection = selector.select(h0=h0, catalog=catalog, evidence=evidence)
        except Exception as exc:
            return self._preserved_result(
                h0=h0,
                catalog=catalog,
                selected=(),
                selector_name=selector.name,
                outcome="preserved-request-failure",
                reason_code="selector_request_failure",
                error_type=type(exc).__name__,
            )
        return self.commit_selection(
            evidence=evidence,
            h0=h0,
            catalog=catalog,
            raw_selection=raw_selection,
            selector_name=selector.name,
        )

    def commit_selection(
        self,
        *,
        evidence: Sequence[EvidenceObject],
        h0: CandidateState,
        catalog: ProposalCatalog,
        raw_selection: Sequence[str] | str | None,
        selector_name: str,
    ) -> EditRuntimeResult:
        if raw_selection is None:
            selected: tuple[str, ...] = ()
        elif isinstance(raw_selection, str):
            selected = (raw_selection.strip(),)
        elif isinstance(raw_selection, Sequence):
            selected = tuple(str(value).strip() for value in raw_selection)
        else:
            return self._preserved_result(
                h0=h0,
                catalog=catalog,
                selected=(),
                selector_name=selector_name,
                outcome="rolled-back-invalid-selection",
                reason_code="malformed_selection",
            )
        if not selected:
            return self._preserved_result(
                h0=h0,
                catalog=catalog,
                selected=selected,
                selector_name=selector_name,
                outcome="preserved-no-proposal",
                reason_code="no_proposal_selected",
            )
        if any(not proposal_id for proposal_id in selected):
            return self._preserved_result(
                h0=h0,
                catalog=catalog,
                selected=selected,
                selector_name=selector_name,
                outcome="rolled-back-invalid-selection",
                reason_code="malformed_selection",
            )
        if len(selected) != len(set(selected)):
            return self._preserved_result(
                h0=h0,
                catalog=catalog,
                selected=selected,
                selector_name=selector_name,
                outcome="rolled-back-invalid-selection",
                reason_code="duplicate_proposal_selection",
            )
        proposal_by_id = catalog.by_id()
        unknown = sorted(set(selected) - set(proposal_by_id))
        if unknown:
            return self._preserved_result(
                h0=h0,
                catalog=catalog,
                selected=selected,
                selector_name=selector_name,
                outcome="rolled-back-invalid-selection",
                reason_code="unknown_proposal_id",
                details={"unknown_proposal_ids": unknown},
            )
        proposals = [proposal_by_id[proposal_id] for proposal_id in selected]
        if any(proposal.action == "ABSTAIN" for proposal in proposals):
            if len(proposals) != 1:
                return self._preserved_result(
                    h0=h0,
                    catalog=catalog,
                    selected=selected,
                    selector_name=selector_name,
                    outcome="rolled-back-invalid-selection",
                    reason_code="abstain_conflict",
                )
            return self._preserved_result(
                h0=h0,
                catalog=catalog,
                selected=selected,
                selector_name=selector_name,
                outcome="preserved-abstain",
                reason_code="explicit_abstain",
                abstain_count=1,
            )

        consumed: set[str] = set()
        for proposal in proposals:
            overlap = consumed & set(proposal.candidate_ids)
            if overlap:
                return self._preserved_result(
                    h0=h0,
                    catalog=catalog,
                    selected=selected,
                    selector_name=selector_name,
                    outcome="rolled-back-invalid-selection",
                    reason_code="conflicting_candidate_consumption",
                    details={"conflicting_candidate_ids": sorted(overlap)},
                )
            consumed.update(proposal.candidate_ids)

        evidence_by_id = _evidence_index(evidence)
        candidate_by_id = {candidate.candidate_id: candidate for candidate in h0.candidates}
        try:
            output: list[dict[str, Any]] = []
            mutated: set[str] = set()
            keep_count = 0
            merge_count = 0
            split_count = 0
            for proposal in proposals:
                if any(
                    candidate_id not in candidate_by_id for candidate_id in proposal.candidate_ids
                ):
                    raise _ValidationFailure("unknown_candidate_id")
                if proposal.action == "KEEP":
                    keep_count += 1
                    continue
                if proposal.action == "MERGE":
                    if len(proposal.candidate_ids) != 2:
                        raise _ValidationFailure("invalid_merge_arity")
                    source_ids = set()
                    for candidate_id in proposal.candidate_ids:
                        source_ids.update(candidate_by_id[candidate_id].evidence_ids)
                    if not source_ids:
                        raise _ValidationFailure("merge_without_evidence")
                    output.append(
                        self._hypothesis_for_ids(source_ids, evidence_by_id, action="merge")
                    )
                    mutated.update(proposal.candidate_ids)
                    merge_count += 1
                    continue
                if proposal.action == "SPLIT":
                    if len(proposal.candidate_ids) != 1:
                        raise _ValidationFailure("invalid_split_arity")
                    candidate = candidate_by_id[proposal.candidate_ids[0]]
                    source_ids = set(candidate.evidence_ids)
                    if len(proposal.parts) < 2 or any(not part for part in proposal.parts):
                        raise _ValidationFailure("split_requires_two_nonempty_parts")
                    flattened = [evidence_id for part in proposal.parts for evidence_id in part]
                    if len(flattened) != len(set(flattened)):
                        raise _ValidationFailure("duplicate_split_evidence")
                    part_union = set(flattened)
                    if part_union - source_ids:
                        raise _ValidationFailure("foreign_split_evidence")
                    if source_ids - part_union:
                        raise _ValidationFailure("missing_split_evidence")
                    for part in proposal.parts:
                        output.append(
                            self._hypothesis_for_ids(set(part), evidence_by_id, action="split")
                        )
                    mutated.add(candidate.candidate_id)
                    split_count += 1
                    continue
                raise _ValidationFailure("unsupported_action")

            for candidate in h0.candidates:
                if candidate.candidate_id not in mutated:
                    output.append(deepcopy(candidate.hypothesis))
            h1 = _state_from_hypotheses(output, base_reducer=h0.base_reducer)
            self._validate_transition(h0, h1, evidence_by_id)
        except _ValidationFailure as exc:
            return self._preserved_result(
                h0=h0,
                catalog=catalog,
                selected=selected,
                selector_name=selector_name,
                outcome="rolled-back-validation",
                reason_code=exc.reason_code,
            )

        state_change_count = merge_count + split_count
        outcome = "committed-edits" if state_change_count else "committed-keep"
        trace = self._trace(
            h0=h0,
            h1=h1,
            catalog=catalog,
            selected=selected,
            selector_name=selector_name,
            outcome=outcome,
            validator_outcome="accepted",
            reason_code=None,
            keep_count=keep_count,
            merge_count=merge_count,
            split_count=split_count,
            abstain_count=0,
            accepted_edit_count=state_change_count,
        )
        return EditRuntimeResult(h0, h1, catalog, selected, trace)

    @staticmethod
    def _hypothesis_for_ids(
        evidence_ids: set[str],
        evidence_by_id: dict[str, EvidenceObject],
        *,
        action: str,
    ) -> dict[str, Any]:
        try:
            items = [evidence_by_id[evidence_id] for evidence_id in sorted(evidence_ids)]
        except KeyError as exc:
            raise _ValidationFailure("foreign_evidence") from exc
        if not items:
            raise _ValidationFailure("hypothesis_without_evidence")
        hypothesis = _hypothesis_from_evidence_group(
            items,
            reducer="bounded-edit-v2",
            include_root_hint_in_affected=True,
        )
        hypothesis["bounded_edit_action"] = action
        return _canonical_hypothesis(hypothesis)

    @staticmethod
    def _validate_transition(
        h0: CandidateState,
        h1: CandidateState,
        evidence_by_id: dict[str, EvidenceObject],
    ) -> None:
        _validate_state_ownership(h1, evidence_by_id)
        h0_ids = [
            evidence_id for candidate in h0.candidates for evidence_id in candidate.evidence_ids
        ]
        h1_ids = [
            evidence_id for candidate in h1.candidates for evidence_id in candidate.evidence_ids
        ]
        if len(h1_ids) != len(set(h1_ids)):
            raise _ValidationFailure("duplicate_evidence_ownership")
        if set(h1_ids) - set(h0_ids):
            raise _ValidationFailure("foreign_evidence")
        if set(h0_ids) - set(h1_ids):
            raise _ValidationFailure("missing_evidence")
        if len(h0_ids) != len(h1_ids):
            raise _ValidationFailure("evidence_multiplicity_changed")
        for candidate in h1.candidates:
            items = _candidate_evidence(candidate, evidence_by_id)
            allowed = {item.service for item in items} | {
                str(item.upstream_hint) for item in items if item.upstream_hint
            }
            hypothesis = _canonical_hypothesis(candidate.hypothesis)
            root = hypothesis["root_service"]
            affected = set(hypothesis["affected_services"])
            if root not in allowed:
                raise _ValidationFailure("invalid_root_service")
            # The workload schema represents root_service separately from
            # affected_services; legacy legal H0 candidates do not necessarily
            # repeat the root in the affected list. Both fields must remain
            # evidence-eligible, but duplication across them is not required.
            if not affected or not affected <= allowed:
                raise _ValidationFailure("invalid_affected_services")

    def _preserved_result(
        self,
        *,
        h0: CandidateState,
        catalog: ProposalCatalog,
        selected: tuple[str, ...],
        selector_name: str,
        outcome: str,
        reason_code: str,
        error_type: str | None = None,
        details: dict[str, Any] | None = None,
        abstain_count: int = 0,
    ) -> EditRuntimeResult:
        trace = self._trace(
            h0=h0,
            h1=h0,
            catalog=catalog,
            selected=selected,
            selector_name=selector_name,
            outcome=outcome,
            validator_outcome=(
                "not-invoked"
                if outcome
                in {"preserved-abstain", "preserved-no-proposal", "preserved-request-failure"}
                else "rejected"
            ),
            reason_code=reason_code,
            keep_count=0,
            merge_count=0,
            split_count=0,
            abstain_count=abstain_count,
            accepted_edit_count=0,
            error_type=error_type,
            details=details,
        )
        return EditRuntimeResult(h0, h0, catalog, selected, trace)

    @staticmethod
    def _trace(
        *,
        h0: CandidateState,
        h1: CandidateState,
        catalog: ProposalCatalog,
        selected: tuple[str, ...],
        selector_name: str,
        outcome: str,
        validator_outcome: str,
        reason_code: str | None,
        keep_count: int,
        merge_count: int,
        split_count: int,
        abstain_count: int,
        accepted_edit_count: int,
        error_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        selection_digest = stable_digest(list(selected))
        replay_id = stable_digest(
            {
                "contract_version": CONTRACT_VERSION,
                "h0_digest": h0.digest,
                "proposal_catalog_digest": catalog.digest,
                "selection_digest": selection_digest,
            }
        )
        trace: dict[str, Any] = {
            "contract_version": CONTRACT_VERSION,
            "base_reducer": h0.base_reducer,
            "bounded_actions": ["KEEP", "MERGE", "SPLIT", "ABSTAIN"],
            "selector": selector_name,
            "h0_digest": h0.digest,
            "candidate_state_digest": h0.digest,
            "proposal_catalog_digest": catalog.digest,
            "selection_digest": selection_digest,
            "selected_proposal_ids": list(selected),
            "h1_digest": h1.digest,
            "committed_state_digest": h1.digest,
            "commit_outcome": outcome,
            "validator_outcome": validator_outcome,
            "validator_reason_code": reason_code,
            "fallback_reason": reason_code if h1.digest == h0.digest else None,
            "keep_count": keep_count,
            "merge_count": merge_count,
            "split_count": split_count,
            "abstain_count": abstain_count,
            "no_proposal_count": int(outcome == "preserved-no-proposal"),
            "invalid_selection_count": int(outcome == "rolled-back-invalid-selection"),
            "validator_rejection_count": int(outcome == "rolled-back-validation"),
            "accepted_edit_count": accepted_edit_count,
            "state_change_count": accepted_edit_count,
            "catalog_state_changing_total": catalog.state_changing_total,
            "catalog_state_changing_retained": catalog.state_changing_retained,
            "catalog_truncation_by_action": dict(catalog.truncation_by_action),
            "checkpoint_id": stable_digest(
                {"contract_version": CONTRACT_VERSION, "h0": h0.to_dict()}
            ),
            "replay_id": replay_id,
        }
        if error_type:
            trace["error_type"] = error_type
        if details:
            trace["validator_details"] = details
        return trace

    @staticmethod
    def checkpoint(result: EditRuntimeResult) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "h0": result.h0.to_dict(),
            "catalog": result.catalog.to_dict(),
            "selected_proposal_ids": list(result.selected_proposal_ids),
            "trace": deepcopy(result.trace),
        }

    @staticmethod
    def restore_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
        if checkpoint.get("contract_version") != CONTRACT_VERSION:
            raise ValueError("unsupported checkpoint contract version")
        h0 = checkpoint.get("h0")
        catalog = checkpoint.get("catalog")
        selected = checkpoint.get("selected_proposal_ids")
        if (
            not isinstance(h0, dict)
            or not isinstance(catalog, dict)
            or not isinstance(selected, list)
        ):
            raise ValueError("malformed bounded-edit checkpoint")
        return {
            "contract_version": CONTRACT_VERSION,
            "h0_digest": stable_digest(h0),
            "proposal_catalog_digest": stable_digest(catalog),
            "selection_digest": stable_digest(selected),
            "trace_h0_digest": checkpoint.get("trace", {}).get("h0_digest"),
            "trace_h1_digest": checkpoint.get("trace", {}).get("h1_digest"),
            "replay_id": checkpoint.get("trace", {}).get("replay_id"),
        }


class _ValidationFailure(Exception):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


def structural_signature(
    state: CandidateState,
    evidence: Sequence[EvidenceObject],
) -> str:
    """ID-agnostic signature for legal evidence/candidate renaming tests."""

    evidence_by_id = _evidence_index(evidence)
    groups = []
    for candidate in state.candidates:
        items = [
            {
                key: value
                for key, value in observable_evidence_dict(evidence_by_id[evidence_id]).items()
                if key != "evidence_id"
            }
            for evidence_id in candidate.evidence_ids
        ]
        groups.append(sorted(items, key=_canonical_bytes))
    return stable_digest(sorted(groups, key=_canonical_bytes))
