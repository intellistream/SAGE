"""Fair shared-catalog evaluation for bounded SemanticReduce Edit v2."""

from __future__ import annotations

import itertools
import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from sage.workloads.semantic_merge_analysis import (
    ConstrainedAgglomerativeMergeReducer,
    MergeIncident,
    SemanticGraphMergeReducer,
    score_merge_hypotheses,
)
from sage.workloads.semantic_reduce_edit_runtime import (
    BoundedEditRuntime,
    CandidateState,
    DeterministicProposalSelector,
    EditProposal,
    EditRuntimeResult,
    ProposalCatalog,
    ProposalSelector,
    observable_evidence_dict,
)
from sage.workloads.semantic_reduce_heldout import HeldoutWorkload, field_separability


@dataclass(frozen=True)
class ScoredState:
    precision: float
    recall: float
    f1: float
    detected_count: int
    matched_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "precision": round(self.precision, 6),
            "recall": round(self.recall, 6),
            "f1": round(self.f1, 6),
            "detected_count": self.detected_count,
            "matched_count": self.matched_count,
        }


def score_state(hypotheses: list[dict[str, Any]], incidents: list[MergeIncident]) -> ScoredState:
    matched_incidents, matched_hypotheses, _ = score_merge_hypotheses(hypotheses, incidents)
    precision = matched_hypotheses / max(1, len(hypotheses))
    recall = len(matched_incidents) / max(1, len(incidents))
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    return ScoredState(
        precision=precision,
        recall=recall,
        f1=f1,
        detected_count=len(hypotheses),
        matched_count=len(matched_incidents),
    )


class MockModelProposalSelector:
    """Offline single-token policy emulator; this is not an endpoint result."""

    name = "mock-model-proposal-selector"

    def select(
        self,
        *,
        h0: CandidateState,
        catalog: ProposalCatalog,
        evidence: Sequence[Any],
    ) -> Sequence[str]:
        del h0, evidence
        consumed: set[str] = set()
        selected: list[str] = []
        # Emulate a bounded policy returning A<n> tokens only. It prioritizes
        # conflicting-hint splits, then same-hint merges, and deliberately has
        # no scorer/label access.
        proposals = sorted(
            catalog.proposals,
            key=lambda proposal: (
                0
                if proposal.action == "SPLIT" and proposal.generator == "conflicting-upstream-hints"
                else 1
                if proposal.action == "MERGE" and dict(proposal.metadata).get("same_non_null_hint")
                else 2,
                proposal.proposal_id,
            ),
        )
        for proposal in proposals:
            eligible = (
                proposal.action == "SPLIT" and proposal.generator == "conflicting-upstream-hints"
            ) or (
                proposal.action == "MERGE"
                and bool(dict(proposal.metadata).get("same_non_null_hint"))
            )
            if not eligible or any(value in consumed for value in proposal.candidate_ids):
                continue
            selected.append(proposal.proposal_id)
            consumed.update(proposal.candidate_ids)
        return selected


class OpenAIProposalSelector:
    """Fail-closed real-online selector over system-owned proposal IDs only."""

    name = "openai-proposal-id-selector"
    system_message = "You are a bounded semantic-reduction proposal selector."

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        sampling_seed: int,
        temperature: float = 0.0,
        max_tokens: int = 256,
        timeout_sec: int = 180,
        visible_proposal_ids: Sequence[str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.sampling_seed = sampling_seed
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_sec = timeout_sec
        self.visible_proposal_ids = (
            tuple(visible_proposal_ids) if visible_proposal_ids is not None else None
        )
        self.last_trace: dict[str, Any] = {}

    @staticmethod
    def _field(value: Any) -> str:
        if value is None:
            return "-"
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, dict):
            return (
                ",".join(
                    f"{key}={OpenAIProposalSelector._field(item)}"
                    for key, item in sorted(value.items())
                )
                or "-"
            )
        if isinstance(value, (list, tuple)):
            return ",".join(OpenAIProposalSelector._field(item) for item in value) or "-"
        return str(value)

    @staticmethod
    def _prompt(
        *,
        h0: CandidateState,
        catalog: ProposalCatalog,
        evidence: Sequence[Any],
        visible_proposal_ids: Sequence[str] | None = None,
    ) -> str:
        by_id = catalog.by_id()
        if visible_proposal_ids is None:
            visible = [item for item in catalog.proposals if item.action in {"MERGE", "SPLIT"}]
        else:
            unknown = [value for value in visible_proposal_ids if value not in by_id]
            if unknown:
                raise ValueError(f"visible proposal IDs are not in catalog: {unknown}")
            visible = [by_id[value] for value in visible_proposal_ids]
            if any(item.action not in {"MERGE", "SPLIT"} for item in visible):
                raise ValueError("prompt view may contain only state-changing proposals")

        candidate_ids = {
            candidate_id for proposal in visible for candidate_id in proposal.candidate_ids
        }
        candidates = [
            candidate for candidate in h0.candidates if candidate.candidate_id in candidate_ids
        ]
        critical_evidence_ids = {
            evidence_id for candidate in candidates for evidence_id in candidate.evidence_ids
        }
        observable = {item.evidence_id: observable_evidence_dict(item) for item in evidence}
        missing = sorted(critical_evidence_ids - observable.keys())
        if missing:
            raise ValueError(f"candidate evidence is missing from prompt input: {missing}")

        lines = [
            "CONTRACT semantic-reduce/v2-compact-prompt/1",
            f"H0 {h0.digest}",
            f"CATALOG {catalog.digest}",
            "EVIDENCE_RULE every evidence row owned by a visible proposal candidate is complete; no field or row is truncated",
            "COLUMNS C:id|root|region|start-end|services|signals|score|evidence_ids",
            "COLUMNS P:id|action|candidate_ids|generator|metadata|parts",
            "COLUMNS E:id|service|region|start-end|signals|score|p95ms|error_rate|queue_depth|npu_util|upstream_hint",
        ]
        for candidate in candidates:
            hypothesis = candidate.hypothesis
            lines.append(
                "|".join(
                    [
                        "C",
                        candidate.candidate_id,
                        str(hypothesis["root_service"]),
                        str(hypothesis["region"]),
                        f"{hypothesis['start_minute']}-{hypothesis['end_minute']}",
                        OpenAIProposalSelector._field(hypothesis["affected_services"]),
                        OpenAIProposalSelector._field(hypothesis["signals"]),
                        str(hypothesis["score"]),
                        OpenAIProposalSelector._field(candidate.evidence_ids),
                    ]
                )
            )
        for proposal in visible:
            lines.append(
                "|".join(
                    [
                        "P",
                        proposal.proposal_id,
                        proposal.action,
                        OpenAIProposalSelector._field(proposal.candidate_ids),
                        proposal.generator,
                        OpenAIProposalSelector._field(dict(proposal.metadata)),
                        ";".join(OpenAIProposalSelector._field(part) for part in proposal.parts)
                        or "-",
                    ]
                )
            )
        evidence_fields = (
            "evidence_id",
            "service",
            "region",
            "start_minute",
            "end_minute",
            "signals",
            "score",
            "p95_latency_ms",
            "error_rate",
            "queue_depth",
            "npu_util",
            "upstream_hint",
        )
        for evidence_id in sorted(critical_evidence_ids):
            item = observable[evidence_id]
            values = [OpenAIProposalSelector._field(item[key]) for key in evidence_fields]
            values[3:5] = [f"{values[3]}-{values[4]}"]
            lines.append("|".join(["E", *values]))
        return (
            "Select zero or more nonconflicting MERGE/SPLIT proposal IDs shown below. "
            "Never invent an ID or payload. An empty list keeps H0. Return JSON only "
            'as {"proposal_ids":["A12"]}.\n' + "\n".join(lines)
        )

    def build_messages(
        self,
        *,
        h0: CandidateState,
        catalog: ProposalCatalog,
        evidence: Sequence[Any],
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_message},
            {
                "role": "user",
                "content": self._prompt(
                    h0=h0,
                    catalog=catalog,
                    evidence=evidence,
                    visible_proposal_ids=self.visible_proposal_ids,
                ),
            },
        ]

    def select(
        self,
        *,
        h0: CandidateState,
        catalog: ProposalCatalog,
        evidence: Sequence[Any],
    ) -> Sequence[str]:
        messages = self.build_messages(h0=h0, catalog=catalog, evidence=evidence)
        request_payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "seed": self.sampling_seed,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        started = time.perf_counter()
        body = ""
        response_payload: dict[str, Any] = {}
        selected: list[str] = []
        outcome = "request-failed"
        error_type: str | None = None
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                body = response.read().decode("utf-8")
            response_payload = json.loads(body)
            choices = response_payload.get("choices") or []
            content = str((choices[0].get("message") or {}).get("content") or "")
            parsed = json.loads(content)
            raw_ids = parsed.get("proposal_ids")
            if not isinstance(raw_ids, list) or not all(
                isinstance(value, str) for value in raw_ids
            ):
                raise ValueError("proposal_ids must be a list of strings")
            selected = list(raw_ids)
            outcome = "parsed"
        except (OSError, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
            error_type = type(exc).__name__
            selected = []
            outcome = "fail-closed-empty-selection"
            if isinstance(exc, urllib.error.HTTPError):
                body = exc.read().decode("utf-8", errors="replace")
        self.last_trace = {
            "evidence_label": "real-online",
            "selector": self.name,
            "model": self.model,
            "base_url": self.base_url,
            "sampling_seed": self.sampling_seed,
            "temperature": self.temperature,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "outcome": outcome,
            "error_type": error_type,
            "h0_digest": h0.digest,
            "catalog_digest": catalog.digest,
            "request_payload": request_payload,
            "raw_response_body": body,
            "provider_usage": response_payload.get("usage"),
            "selected_proposal_ids": selected,
        }
        return selected


def _selection_is_nonconflicting(proposals: Iterable[EditProposal]) -> bool:
    consumed: set[str] = set()
    for proposal in proposals:
        if consumed & set(proposal.candidate_ids):
            return False
        consumed.update(proposal.candidate_ids)
    return True


def proposal_oracle(
    *,
    runtime: BoundedEditRuntime,
    workload: HeldoutWorkload,
    h0: CandidateState,
    catalog: ProposalCatalog,
    max_edits: int,
) -> tuple[EditRuntimeResult, ScoredState, dict[str, bool]]:
    """Pre-model diagnostic oracle over bounded catalog-ID combinations."""

    baseline = runtime.commit_selection(
        evidence=workload.dataset.evidence,
        h0=h0,
        catalog=catalog,
        raw_selection=[],
        selector_name="proposal-oracle",
    )
    best_result = baseline
    best_score = score_state(baseline.hypotheses, workload.dataset.incidents)
    improving = {"MERGE": False, "SPLIT": False}
    edits = [proposal for proposal in catalog.proposals if proposal.action in improving]
    for proposal in edits:
        result = runtime.commit_selection(
            evidence=workload.dataset.evidence,
            h0=h0,
            catalog=catalog,
            raw_selection=[proposal.proposal_id],
            selector_name="proposal-oracle",
        )
        score = score_state(result.hypotheses, workload.dataset.incidents)
        if score.f1 > best_score.f1 + 1e-12:
            improving[proposal.action] = True

    selections: list[tuple[str, ...]] = []
    for size in range(1, max(1, max_edits) + 1):
        selections.extend(
            tuple(proposal.proposal_id for proposal in combination)
            for combination in itertools.combinations(edits, size)
            if _selection_is_nonconflicting(combination)
        )
    seen: set[tuple[str, ...]] = set()
    for selected in selections:
        selected = tuple(selected)
        if selected in seen:
            continue
        seen.add(selected)
        selected_proposals = [
            catalog.by_id()[value] for value in selected if value in catalog.by_id()
        ]
        if len(selected_proposals) != len(selected) or not _selection_is_nonconflicting(
            selected_proposals
        ):
            continue
        result = runtime.commit_selection(
            evidence=workload.dataset.evidence,
            h0=h0,
            catalog=catalog,
            raw_selection=selected,
            selector_name="proposal-oracle",
        )
        if result.trace["commit_outcome"] != "committed-edits":
            continue
        score = score_state(result.hypotheses, workload.dataset.incidents)
        rank = (score.f1, -len(selected), tuple(reversed(selected)))
        best_rank = (
            best_score.f1,
            -len(best_result.selected_proposal_ids),
            tuple(reversed(best_result.selected_proposal_ids)),
        )
        if rank > best_rank:
            best_result, best_score = result, score
    return best_result, best_score, improving


def _gold_proposal_coverage(
    h0: CandidateState,
    catalog: ProposalCatalog,
    evidence: Sequence[Any],
) -> dict[str, Any]:
    source_by_evidence = {item.evidence_id: item.source_incident_id for item in evidence}
    candidate_sources: dict[str, set[str]] = {}
    source_candidates: dict[str, set[str]] = {}
    for candidate in h0.candidates:
        sources = {
            str(source_by_evidence[evidence_id])
            for evidence_id in candidate.evidence_ids
            if source_by_evidence.get(evidence_id)
        }
        candidate_sources[candidate.candidate_id] = sources
        for source in sources:
            source_candidates.setdefault(source, set()).add(candidate.candidate_id)

    gold_merge_pairs = {
        tuple(sorted(pair))
        for candidates in source_candidates.values()
        for pair in itertools.combinations(sorted(candidates), 2)
    }
    catalog_merge_pairs = {
        tuple(sorted(proposal.candidate_ids))
        for proposal in catalog.proposals
        if proposal.action == "MERGE"
    }
    gold_split_candidates = {
        candidate_id for candidate_id, sources in candidate_sources.items() if len(sources) >= 2
    }
    covered_split_candidates: set[str] = set()
    for proposal in catalog.proposals:
        if proposal.action != "SPLIT":
            continue
        candidate_id = proposal.candidate_ids[0]
        if candidate_id not in gold_split_candidates:
            continue
        part_sources = [
            {
                str(source_by_evidence[evidence_id])
                for evidence_id in part
                if source_by_evidence.get(evidence_id)
            }
            for part in proposal.parts
        ]
        if part_sources and all(len(sources) <= 1 for sources in part_sources):
            covered_split_candidates.add(candidate_id)
    return {
        "gold_merge_pair_count": len(gold_merge_pairs),
        "covered_gold_merge_pair_count": len(gold_merge_pairs & catalog_merge_pairs),
        "merge_proposal_recall": round(
            len(gold_merge_pairs & catalog_merge_pairs) / max(1, len(gold_merge_pairs)),
            6,
        ),
        "gold_split_candidate_count": len(gold_split_candidates),
        "covered_gold_split_candidate_count": len(covered_split_candidates),
        "split_proposal_recall": round(
            len(covered_split_candidates) / max(1, len(gold_split_candidates)), 6
        ),
    }


def _action_names(result: EditRuntimeResult) -> list[str]:
    by_id = result.catalog.by_id()
    return [by_id[value].action for value in result.selected_proposal_ids if value in by_id]


def _conservation(result: EditRuntimeResult) -> bool:
    before = sorted(
        evidence_id for candidate in result.h0.candidates for evidence_id in candidate.evidence_ids
    )
    after = sorted(
        evidence_id for candidate in result.h1.candidates for evidence_id in candidate.evidence_ids
    )
    return before == after and len(after) == len(set(after))


def evaluate_workload(
    workload: HeldoutWorkload,
    *,
    oracle_max_edits: int = 2,
    deterministic_selector: ProposalSelector | None = None,
    model_selector: ProposalSelector | None = None,
    evidence_label: str = "simulation/model",
) -> dict[str, Any]:
    runtime = BoundedEditRuntime(
        base_reducer=SemanticGraphMergeReducer(),
        proposal_budget=workload.proposal_budget,
        service_topology=workload.service_topology,
    )
    h0 = runtime.build_h0(workload.dataset.evidence)
    catalog = runtime.build_catalog(h0, workload.dataset.evidence)
    h0_result = runtime.commit_selection(
        evidence=workload.dataset.evidence,
        h0=h0,
        catalog=catalog,
        raw_selection=[],
        selector_name="h0-no-edit",
    )
    deterministic_selector = deterministic_selector or DeterministicProposalSelector()
    model_selector = model_selector or MockModelProposalSelector()
    deterministic_ids = deterministic_selector.select(
        h0=h0, catalog=catalog, evidence=workload.dataset.evidence
    )
    model_ids = model_selector.select(h0=h0, catalog=catalog, evidence=workload.dataset.evidence)
    oracle_result, oracle_score, improving = proposal_oracle(
        runtime=runtime,
        workload=workload,
        h0=h0,
        catalog=catalog,
        max_edits=oracle_max_edits,
    )
    deterministic_result = runtime.commit_selection(
        evidence=workload.dataset.evidence,
        h0=h0,
        catalog=catalog,
        raw_selection=deterministic_ids,
        selector_name=deterministic_selector.name,
    )
    model_result = runtime.commit_selection(
        evidence=workload.dataset.evidence,
        h0=h0,
        catalog=catalog,
        raw_selection=model_ids,
        selector_name=model_selector.name,
    )

    constrained = ConstrainedAgglomerativeMergeReducer().reduce(workload.dataset.evidence)
    scores = {
        "h0": score_state(h0_result.hypotheses, workload.dataset.incidents),
        "oracle": oracle_score,
        "deterministic": score_state(deterministic_result.hypotheses, workload.dataset.incidents),
        "mock_model": score_state(model_result.hypotheses, workload.dataset.incidents),
        "constrained_reference": score_state(constrained, workload.dataset.incidents),
    }
    coverage = _gold_proposal_coverage(h0, catalog, workload.dataset.evidence)
    oracle_set = set(oracle_result.selected_proposal_ids)

    def policy_record(result: EditRuntimeResult, score: ScoredState) -> dict[str, Any]:
        selected_set = set(result.selected_proposal_ids)
        return {
            **score.to_dict(),
            "selected_proposal_ids": list(result.selected_proposal_ids),
            "selected_actions": _action_names(result),
            "commit_outcome": result.trace["commit_outcome"],
            "validator_outcome": result.trace["validator_outcome"],
            "validator_reason_code": result.trace["validator_reason_code"],
            "accepted_edit_count": result.trace["accepted_edit_count"],
            "merge_count": result.trace["merge_count"],
            "split_count": result.trace["split_count"],
            "evidence_conserved": _conservation(result),
            "selector_exact_oracle_match": selected_set == oracle_set,
            "selector_oracle_proposal_precision": round(
                len(selected_set & oracle_set) / max(1, len(selected_set)), 6
            ),
            "f1_delta_from_h0": round(score.f1 - scores["h0"].f1, 6),
        }

    model_policy_key = (
        "mock_model_selector"
        if isinstance(model_selector, MockModelProposalSelector)
        else "online_model_selector"
    )
    model_permission = (
        "offline ID-only policy emulator; no endpoint/model invocation"
        if model_policy_key == "mock_model_selector"
        else "real-online ID-only selector over the shared system-owned catalog"
    )
    policies = {
        "h0": policy_record(h0_result, scores["h0"]),
        "proposal_oracle": {
            **policy_record(oracle_result, scores["oracle"]),
            "permission": "ground-truth diagnostic selection over prebuilt catalog",
        },
        "deterministic_selector": policy_record(deterministic_result, scores["deterministic"]),
        model_policy_key: {
            **policy_record(model_result, scores["mock_model"]),
            "selector_name": model_selector.name,
            "permission": model_permission,
        },
        "constrained_reference": {
            **scores["constrained_reference"].to_dict(),
            "permission": "full-evidence global reclustering; not an H0 edit peer",
            "f1_delta_from_h0": round(scores["constrained_reference"].f1 - scores["h0"].f1, 6),
        },
    }
    return {
        "family": workload.family,
        "seed": workload.seed,
        "split": workload.split,
        "evidence_label": evidence_label,
        "workload_source": "repo-local:src/sage/workloads/semantic_reduce_heldout.py",
        "axis_metadata": workload.axis_metadata,
        "base_reducer": h0.base_reducer,
        "h0_digest": h0.digest,
        "proposal_catalog_digest": catalog.digest,
        "shared_catalog_digest_match": (
            deterministic_result.trace["proposal_catalog_digest"]
            == model_result.trace["proposal_catalog_digest"]
            == catalog.digest
        ),
        "candidate_count": len(h0.candidates),
        "proposal_count": len(catalog.proposals),
        "state_changing_proposal_count": catalog.state_changing_retained,
        "catalog_budget": catalog.proposal_budget,
        "catalog_truncation_by_action": dict(catalog.truncation_by_action),
        "proposal_coverage": {
            **coverage,
            "improving_merge_proposal_exists": improving["MERGE"],
            "improving_split_proposal_exists": improving["SPLIT"],
            "h0_error": scores["h0"].f1 < 1.0 - 1e-12,
            "oracle_improves_h0": scores["oracle"].f1 > scores["h0"].f1 + 1e-12,
        },
        "field_separability": field_separability(workload),
        "policies": policies,
    }
