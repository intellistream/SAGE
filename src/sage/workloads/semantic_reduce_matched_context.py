"""Observable-only reconstruction and prompts for the matched pilot.

This module never opens labels, oracle files, model credentials, or a network.
Both model interfaces consume the same context bytes.
"""
from __future__ import annotations
from collections import Counter
import json
from sage.workloads.semantic_merge_analysis import EvidenceObject, SemanticGraphMergeReducer
from sage.workloads.semantic_reduce_edit_runtime import BoundedEditRuntime, stable_digest

OBSERVABLE_FIELDS = frozenset(('evidence_id','shard_id','service','region','start_minute','end_minute',
    'signals','score','p95_latency_ms','error_rate','queue_depth','npu_util','upstream_hint'))
COMMON_INSTRUCTION = (
    'Revise existing incident hypotheses using only the supplied observations. '
    'Preserve every evidence item owned by H0 exactly once; do not introduce or drop evidence. '
    'Keep distinct incidents separate. Each edit consumes distinct H0 candidates; '
    'do not edit a produced candidate within the same batch. Merge only within one region. '
    'Use at most two MERGE/SPLIT edits. A split must have at least two nonempty disjoint parts '
    'whose union is exactly the source candidate evidence. Unchanged H0 candidates carry forward. '
    'Choose no edits when there is insufficient observational support. Return only JSON, no prose. '
    'The catalog is a menu, not a to-do list. Choose at most two compatible state-changing edits '
    'instead of copying all entries. KEEP/ABSTAIN need not be listed because unselected H0 '
    'candidates carry forward. Return the interface JSON object without catalog metadata, '
    'explanation, arrays at the top level or Markdown fences.'
)
INTERFACES = {
    'T-ID': 'Return {"proposal_ids":["<catalog proposal ID>", ...]}. Use only IDs in system_catalog; an empty list preserves H0.',
    'B-validated': 'Return {"edits":[{"action":"MERGE","candidate_ids":["C0","C1"]} or {"action":"SPLIT","candidate_ids":["C0"],"parts":[["<evidence ID>"],["<evidence ID>"]]}]}. These are syntax examples, not proposed actions. You may choose any legal split, including one absent from system_catalog. An empty list preserves H0.'
}


def reconstruct(observable):
    if set(observable) != {'schema','evidence','service_topology','proposal_budget','h0','system_catalog'}:
        raise ValueError('unexpected observable context fields')
    evidence = []
    for row in observable['evidence']:
        if set(row) != OBSERVABLE_FIELDS:
            raise ValueError('hidden or missing evidence fields')
        evidence.append(EvidenceObject(**{**row,'signals':tuple(row['signals'])}))
    runtime = BoundedEditRuntime(base_reducer=SemanticGraphMergeReducer(),
        service_topology={k:tuple(v) for k,v in observable['service_topology'].items()},
        proposal_budget=observable['proposal_budget'])
    h0=runtime.build_h0(evidence);catalog=runtime.build_catalog(h0,evidence)
    if h0.to_dict()!=observable['h0'] or catalog.to_dict()!=observable['system_catalog']:
        raise ValueError('frozen H0 or catalog reconstruction mismatch')
    return evidence,runtime,h0,catalog


def messages(observable, arm, feedback=None):
    if arm not in INTERFACES:
        raise ValueError('unknown interface')
    # Select fixed fields rather than serializing unit metadata or scoring objects.
    if set(observable) != {'schema','evidence','service_topology','proposal_budget','h0','system_catalog'}:
        raise ValueError('unexpected observable context fields')
    if any(set(row)!=OBSERVABLE_FIELDS for row in observable['evidence']):
        raise ValueError('hidden evidence fields')
    out=[{'role':'system','content':COMMON_INSTRUCTION+' '+INTERFACES[arm]},
         {'role':'user','content':json.dumps(observable,sort_keys=True,separators=(',',':'),ensure_ascii=False)}]
    if feedback is not None:
        # Only deterministic failure codes, never scores or oracle choices.
        if not isinstance(feedback,str) or not feedback.replace('_','').isalnum():
            raise ValueError('invalid repair feedback code')
        out.append({'role':'user','content':'Previous attempt failed validation: '+feedback+'. Return a corrected complete JSON proposal using the same constraints.'})
    return out


def check_owned_output(h0,h1,evidence):
    """Separate publication check over Counters and evidence-eligible fields."""
    before=Counter(e for c in h0.candidates for e in c.evidence_ids)
    after=Counter(e for c in h1.candidates for e in c.evidence_ids)
    if before!=after or any(v!=1 for v in after.values()):
        raise ValueError('publication_ownership_failure')
    source={e.evidence_id:e for e in evidence}
    for c in h1.candidates:
        if not c.evidence_ids or any(e not in source for e in c.evidence_ids):
            raise ValueError('publication_foreign_or_empty')
        items=[source[e] for e in c.evidence_ids]
        allowed={x.service for x in items}|{x.upstream_hint for x in items if x.upstream_hint}
        if c.hypothesis['root_service'] not in allowed or not set(c.hypothesis['affected_services'])<=allowed:
            raise ValueError('publication_ineligible_service')
    return {'owned_evidence_count':sum(after.values()),'h0_digest':h0.digest,'h1_digest':h1.digest,
            'publication_digest':stable_digest(h1.to_dict())}
