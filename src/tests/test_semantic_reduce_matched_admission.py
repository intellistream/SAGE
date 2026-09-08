import json
from sage.workloads.semantic_merge_analysis import SemanticGraphMergeReducer
from sage.workloads.semantic_reduce_edit_runtime import BoundedEditRuntime
from sage.workloads.semantic_reduce_heldout import generate_heldout_workload
from sage.workloads.semantic_reduce_matched_admission import MatchedEditAdmission


def context():
    w=generate_heldout_workload('mixed-split-merge',seed=7,split='development')
    runtime=BoundedEditRuntime(base_reducer=SemanticGraphMergeReducer(),service_topology=w.service_topology)
    h0=runtime.build_h0(w.dataset.evidence);catalog=runtime.build_catalog(h0,w.dataset.evidence)
    return MatchedEditAdmission(runtime),dict(evidence=w.dataset.evidence,h0=h0,system_catalog=catalog,expected_h0_digest=h0.digest)


def payload(p):
    d={'action':p.action}
    if p.action!='ABSTAIN':d['candidate_ids']=list(p.candidate_ids)
    if p.action=='SPLIT':d['parts']=[list(x) for x in p.parts]
    return d


def test_catalog_actions_have_exact_matched_payload_results():
    adapter,c=context();actions=set()
    for p in c['system_catalog'].proposals:
        a=adapter.commit(arm='T-ID',response=json.dumps({'proposal_ids':[p.proposal_id]}),**c)
        b=adapter.commit(arm='B-validated',response=json.dumps({'edits':[payload(p)]}),**c)
        assert a.h1.digest==b.h1.digest
        assert a.trace['commit_outcome']==b.trace['commit_outcome']
        actions.add(p.action)
    assert {'MERGE','SPLIT'}<=actions


def test_rejection_preserves_h0_for_foreign_missing_duplicate_and_stale():
    adapter,c=context();split=next(p for p in c['system_catalog'].proposals if p.action=='SPLIT')
    bad=[]
    for mode in ['foreign','missing','duplicate']:
        d=payload(split)
        if mode=='foreign':d['parts'][0].append('not-source-evidence')
        if mode=='missing':d['parts'][0].pop()
        if mode=='duplicate':d['parts'][0].append(d['parts'][0][0])
        bad.append(json.dumps({'edits':[d]}))
    bad += ['{"edits":[],"edits":[]}',json.dumps({'edits':[{'action':'MERGE','candidate_ids':['C0','C0']}]}),json.dumps({'edits':[payload(split)]*3})]
    for response in bad:
        result=adapter.commit(arm='B-validated',response=response,**c)
        assert result.h1.digest==c['h0'].digest
        assert result.trace['commit_outcome'].startswith('rolled-back')
    c['expected_h0_digest']='stale'
    for arm,response in [('T-ID','{"proposal_ids":[]}'),('B-validated','{"edits":[]}')]:
        result=adapter.commit(arm=arm,response=response,**c)
        assert result.h1.digest==c['h0'].digest
        assert result.trace['validator_reason_code']=='stale_h0_version'


def test_both_interfaces_enforce_two_edit_budget_before_mutation():
    adapter,c=context();p=next(p for p in c['system_catalog'].proposals if p.action=='SPLIT')
    for arm,response in [('T-ID',{'proposal_ids':[p.proposal_id]*3}),('B-validated',{'edits':[payload(p)]*3})]:
        r=adapter.commit(arm=arm,response=json.dumps(response),**c)
        assert r.h1.digest==c['h0'].digest
        assert r.trace['validator_reason_code']=='edit_budget_exceeded'


def test_free_payload_keeps_explicit_outside_catalog_permission():
    from sage.workloads.semantic_reduce_edit_runtime import ProposalCatalog
    adapter,c=context();p=next(p for p in c['system_catalog'].proposals if p.action=='SPLIT')
    c['system_catalog']=ProposalCatalog((),0,0,0,())
    free=adapter.commit(arm='B-validated',response=json.dumps({'edits':[payload(p)]}),**c)
    ids=adapter.commit(arm='T-ID',response=json.dumps({'proposal_ids':[p.proposal_id]}),**c)
    assert free.trace['commit_outcome']=='committed-edits'
    assert ids.trace['validator_reason_code']=='unknown_proposal_id'
    assert free.catalog.proposals[0].generator=='model-payload-untrusted'
