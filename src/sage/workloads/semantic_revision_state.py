"""Versioned deterministic materialization seam for public evidence revisions.

Extends the workload carrier; reuses the bounded-edit runtime's canonical digest.
This is ordinary dependency-indexed maintenance, not a semantic model policy.
"""
from __future__ import annotations
from copy import deepcopy
import time
from typing import Callable, Any
from sage.workloads.semantic_reduce_edit_runtime import stable_digest

CONTRACT = 'semantic-revision-state/v1'


class DependencyReader:
    def __init__(self, inputs, versions):
        self.inputs=inputs;self.versions=versions;self.reads={};self.records_read=0

    def get(self,key):
        self.reads[key]=self.versions.get(key,0)
        value=self.inputs.get(key,[])
        self.records_read+=len(value)
        return deepcopy(value)


def publish_value(value, previous, dependencies):
    if set(value)!={'target_type','admissible_sets','evidence_refs'}:
        raise ValueError('invalid revision value shape')
    kind=value['target_type'];sets=value['admissible_sets'];refs=value['evidence_refs']
    if kind not in ('identified_exact','set_valued','unknown','background'):
        raise ValueError('invalid target type')
    if (kind=='identified_exact' and (len(sets)!=1 or not sets[0]) or
        kind=='set_valued' and (len(sets)<2 or any(not s for s in sets)) or
        kind=='unknown' and sets!=[] or kind=='background' and sets!=[[]]):
        raise ValueError('invalid admissible sets')
    if sets!=sorted([sorted(set(s)) for s in sets]) or len({tuple(s) for s in sets})!=len(sets):
        raise ValueError('noncanonical admissible sets')
    if refs!=sorted(refs,key=lambda r:r['evidence_id']) or len({r['evidence_id'] for r in refs})!=len(refs):
        raise ValueError('invalid evidence references')
    old=previous['value'] if previous else None
    semantic_changed=old is None or (old['target_type'],old['admissible_sets'])!=(kind,sets)
    evidence_changed=old is None or old['evidence_refs']!=refs
    return {'value':deepcopy(value),
        'semantic_version':(previous['semantic_version'] if previous else 0)+int(semantic_changed),
        'evidence_version':(previous['evidence_version'] if previous else 0)+int(evidence_changed),
        'materialization_version':(previous['materialization_version'] if previous else 0)+1,
        'dependency_versions':dict(sorted(dependencies.items()))},semantic_changed,evidence_changed


class VersionedDependencyState:
    """Atomic input-delta commit with recorded reads, including absent lookups."""
    def __init__(self,evaluate:Callable[[str,DependencyReader],dict]):
        self.evaluate=evaluate;self.inputs={};self.versions={};self.outputs={}
        self.readers={};self.state_version=0

    def apply(self,changes:dict[str,list],targets=(),expected_version=None):
        started=time.perf_counter_ns();evaluation_ns=0
        if expected_version is not None and expected_version!=self.state_version:
            raise ValueError('stale state version')
        staged_inputs=dict(self.inputs);staged_versions=dict(self.versions)
        changed=[]
        for key,value in sorted(changes.items()):
            if key not in self.inputs or stable_digest(value)!=stable_digest(self.inputs[key]):
                staged_inputs[key]=deepcopy(value);staged_versions[key]=self.versions.get(key,0)+1;changed.append(key)
        dirty=set(targets)-set(self.outputs)
        for key in changed: dirty.update(self.readers.get(key,()))
        staged_outputs=dict(self.outputs);staged_readers={k:set(v) for k,v in self.readers.items()}
        semantic_changed=[];evidence_changed=[];reads={};records_read=0
        for target in sorted(dirty):
            reader=DependencyReader(staged_inputs,staged_versions)
            eval_started=time.perf_counter_ns()
            value=self.evaluate(target,reader)
            row,sem,proof=publish_value(value,self.outputs.get(target),reader.reads)
            evaluation_ns+=time.perf_counter_ns()-eval_started
            staged_outputs[target]=row
            for key in self.outputs.get(target,{}).get('dependency_versions',{}):
                staged_readers[key].discard(target)
            for key in reader.reads: staged_readers.setdefault(key,set()).add(target)
            if sem: semantic_changed.append(target)
            if proof: evidence_changed.append(target)
            reads[target]=reader.reads;records_read+=reader.records_read
        # Nothing observable changes until every dirty evaluator has succeeded.
        self.inputs=staged_inputs;self.versions=staged_versions;self.outputs=staged_outputs;self.readers=staged_readers
        if changed or dirty: self.state_version+=1
        return {'state_version':self.state_version,'changed_keys':changed,'recomputed_targets':sorted(dirty),
            'semantic_changed_targets':semantic_changed,'evidence_changed_targets':evidence_changed,
            'reused_targets':sorted(set(self.outputs)-dirty),'dependency_reads':reads,'records_read':records_read,
            'evaluation_ns':evaluation_ns,'dependency_maintenance_ns':time.perf_counter_ns()-started-evaluation_ns,
            'copied_input_map_entries':len(self.inputs),'copied_reverse_index_entries':len(self.readers)}

    def snapshot(self): return deepcopy(self.outputs)

    def checkpoint(self):
        value={'contract':CONTRACT,'inputs':deepcopy(self.inputs),'versions':dict(self.versions),
               'outputs':self.snapshot(),'state_version':self.state_version}
        return {'state':value,'sha256':stable_digest(value)}

    @classmethod
    def restore(cls,checkpoint,evaluate):
        value=deepcopy(checkpoint['state'])
        if checkpoint['sha256']!=stable_digest(value) or value['contract']!=CONTRACT:
            raise ValueError('checkpoint integrity/contract mismatch')
        result=cls(evaluate);result.inputs=value['inputs'];result.versions=value['versions']
        result.outputs=value['outputs'];result.state_version=value['state_version']
        for target,row in result.outputs.items():
            for key,version in row['dependency_versions'].items():
                if version!=result.versions.get(key,0): raise ValueError('stale checkpoint dependency')
                result.readers.setdefault(key,set()).add(target)
        return result
