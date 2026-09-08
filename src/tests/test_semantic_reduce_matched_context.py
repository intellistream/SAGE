from dataclasses import replace
import copy
import pytest
from sage.workloads.semantic_reduce_edit_runtime import BoundedEditRuntime,observable_evidence_dict
from sage.workloads.semantic_merge_analysis import SemanticGraphMergeReducer
from sage.workloads.semantic_reduce_heldout import generate_heldout_workload
from sage.workloads.semantic_reduce_matched_context import reconstruct,messages,check_owned_output


def fixture():
    w=generate_heldout_workload('mixed-split-merge',seed=7,split='development')
    runtime=BoundedEditRuntime(base_reducer=SemanticGraphMergeReducer(),service_topology=w.service_topology,proposal_budget=w.proposal_budget)
    h0=runtime.build_h0(w.dataset.evidence);cat=runtime.build_catalog(h0,w.dataset.evidence)
    return {'schema':'matched-pilot-observable/1','evidence':[{**observable_evidence_dict(e),'shard_id':e.shard_id} for e in w.dataset.evidence],
        'service_topology':{k:list(v) for k,v in w.service_topology.items()},'proposal_budget':w.proposal_budget,'h0':h0.to_dict(),'system_catalog':cat.to_dict()}


def test_reconstruction_matches_and_both_interfaces_share_exact_context():
    obs=fixture();e,r,h,c=reconstruct(obs)
    assert messages(obs,'T-ID')[1]==messages(obs,'B-validated')[1]
    assert check_owned_output(h,h,e)['h0_digest']==h.digest
    damaged=replace(h,candidates=h.candidates[:-1])
    with pytest.raises(ValueError,match='ownership'):check_owned_output(h,damaged,e)


def test_labels_and_oracle_do_not_enter_prompt_or_reconstruction():
    for location in ['top','evidence']:
        obs=fixture()
        if location=='top':obs['oracle_f1']=1.0
        else:obs['evidence'][0]['source_incident_id']='hidden'
        for arm in ['T-ID','B-validated']:
            with pytest.raises(ValueError):messages(obs,arm)
        with pytest.raises(ValueError):reconstruct(obs)
    obs=fixture();obs['h0']['base_reducer']='altered'
    with pytest.raises(ValueError,match='reconstruction'):reconstruct(obs)
