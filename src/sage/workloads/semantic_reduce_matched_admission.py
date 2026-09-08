"""Matched pilot admission for ID selection and model-authored edit payloads.

Both interfaces retain the same H0, ownership validator, atomic commit/fallback,
and two-edit limit. Free proposals have explicitly broader split permissions;
they are never relabeled as members of the system-generated catalog.
"""
from __future__ import annotations
import json
from typing import Any
from sage.workloads.semantic_reduce_edit_runtime import (
    BoundedEditRuntime, CandidateState, EditProposal, ProposalCatalog,
)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def _strings(value):
    if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
        raise ValueError('expected_string_list')
    return tuple(value)


class MatchedEditAdmission:
    def __init__(self, runtime: BoundedEditRuntime, max_edits: int = 2):
        if type(max_edits) is not int or max_edits < 0:
            raise ValueError('invalid_edit_budget')
        self.runtime, self.max_edits = runtime, max_edits

    def commit(self, *, arm: str, response: str, evidence, h0: CandidateState,
               system_catalog: ProposalCatalog, expected_h0_digest: str):
        catalog = system_catalog
        def reject(reason):
            return self.runtime._preserved_result(
                h0=h0, catalog=catalog, selected=(), selector_name=arm,
                outcome='rolled-back-invalid-selection', reason_code=reason)
        if expected_h0_digest != h0.digest:
            return reject('stale_h0_version')
        try:
            if not isinstance(response, str) or len(response.encode()) > 131072:
                raise ValueError('response_size_or_type')
            payload = json.loads(response, object_pairs_hook=_object)
            if not isinstance(payload, dict):
                raise ValueError('expected_object')
            if arm == 'T-ID':
                if set(payload) != {'proposal_ids'}:
                    raise ValueError('unexpected_payload_fields')
                selected = _strings(payload['proposal_ids'])
                lookup = catalog.by_id()
                if any(i not in lookup for i in selected):
                    raise ValueError('unknown_proposal_id')
                proposals = [lookup[i] for i in selected]
            elif arm == 'B-validated':
                if set(payload) != {'edits'} or not isinstance(payload['edits'], list):
                    raise ValueError('unexpected_payload_fields')
                proposals = []
                for index, edit in enumerate(payload['edits']):
                    if not isinstance(edit, dict):
                        raise ValueError('expected_edit_object')
                    action = edit.get('action')
                    required = {'action'} if action == 'ABSTAIN' else {'action','candidate_ids'}
                    if action == 'SPLIT':
                        required.add('parts')
                    if action not in ('KEEP','MERGE','SPLIT','ABSTAIN') or set(edit) != required:
                        raise ValueError('invalid_action_schema')
                    ids = _strings(edit['candidate_ids']) if action != 'ABSTAIN' else ()
                    parts = ()
                    if action == 'SPLIT':
                        if not isinstance(edit['parts'], list):
                            raise ValueError('expected_parts')
                        parts = tuple(_strings(part) for part in edit['parts'])
                    proposals.append(EditProposal(f'F{index}', action, ids, parts,
                                                  generator='model-payload-untrusted'))
                catalog = ProposalCatalog(tuple(proposals),len(proposals),
                    sum(p.action in ('MERGE','SPLIT') for p in proposals),
                    sum(p.action in ('MERGE','SPLIT') for p in proposals),())
                selected = tuple(p.proposal_id for p in proposals)
            else:
                raise ValueError('unknown_arm')
            if sum(p.action in ('MERGE','SPLIT') for p in proposals) > self.max_edits:
                raise ValueError('edit_budget_exceeded')
            candidates = {c.candidate_id:c for c in h0.candidates}
            # Same guard for both arms; the system catalog already obeys these.
            for p in proposals:
                arity = {'KEEP':1,'MERGE':2,'SPLIT':1,'ABSTAIN':0}[p.action]
                if len(p.candidate_ids) != arity or len(set(p.candidate_ids)) != arity:
                    raise ValueError('invalid_candidate_arity')
                if any(i not in candidates for i in p.candidate_ids):
                    raise ValueError('unknown_candidate_id')
                if p.action == 'MERGE' and len({candidates[i].hypothesis['region'] for i in p.candidate_ids}) != 1:
                    raise ValueError('cross_region_merge')
        except (ValueError, TypeError, KeyError) as exc:
            return reject(str(exc))
        return self.runtime.commit_selection(evidence=evidence,h0=h0,catalog=catalog,
                                             raw_selection=selected,selector_name=arm)
