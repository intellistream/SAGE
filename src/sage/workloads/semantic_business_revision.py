"""Strong public count/trace rule and full/indexed/versioned execution adapters."""
from __future__ import annotations
from copy import deepcopy
import json
import time
from sage.workloads.semantic_revision_state import DependencyReader,VersionedDependencyState,publish_value,stable_digest

HYPOTHESES=[['catalog-empty-response'],['expected-request-history-filter']]


def keys(item):
    event=item['event'];p=item['payload'];eid=event['evidence_id'];mod=event['modality']
    if mod=='metric' and p.get('method')=='ListRecommendations': return ['metric:'+eid]
    if mod=='trace': return ['trace:'+str(p.get('trace_id'))]
    if mod=='log' and p.get('event')=='recommendation_business_decision': return ['business:'+str(p.get('trace_id'))]
    if mod=='change' and p.get('operation')=='configuration_published': return ['config:'+str(p.get('component'))]
    if mod=='topology': return ['topology']
    return []


def integer(value): return type(value) is int and value>=0


def evaluate(target,reader):
    refs={}
    def cite(items):
        for item in items:
            e=item['event'];refs[e['evidence_id']]={'evidence_id':e['evidence_id'],'raw_sha256':e['raw_sha256']}
    def result(kind,sets): return {'target_type':kind,'admissible_sets':sets,'evidence_refs':[refs[k] for k in sorted(refs)]}
    metrics=reader.get('metric:'+target);cite(metrics)
    if len(metrics)!=1: return result('unknown',[])
    p=metrics[0]['payload'];trace=p.get('trace_id');start=p.get('start_ns',p.get('timestamp_ns',0))
    configs={}
    for service in ['catalog','recommendation']:
        applicable=[x for x in reader.get('config:'+service) if x['event']['event_time_ns']<=start]
        if not applicable: return result('unknown',[])
        latest=max(x['event']['event_time_ns'] for x in applicable)
        chosen=[x for x in applicable if x['event']['event_time_ns']==latest];cite(chosen)
        if len(chosen)!=1: return result('unknown',[])
        configs[service]=chosen[0]['payload']['contents']
    topology=[x for x in reader.get('topology') if x['event']['event_time_ns']<=start];cite(topology)
    if not any(['recommendation','catalog'] in x['payload'].get('edges',[]) for x in topology): return result('unknown',[])
    spans=reader.get('trace:'+str(trace));cite(spans)
    expected={('catalog','server','ListProducts'),('recommendation','client','ListProducts'),('recommendation','server','ListRecommendations')}
    if len(spans)!=3 or {(x['payload'].get('service'),x['payload'].get('kind'),x['payload'].get('method')) for x in spans}!=expected:
        return result('unknown',[])
    by={(x['payload']['service'],x['payload']['kind']):x['payload'] for x in spans}
    server=by['recommendation','server'];client=by['recommendation','client'];catalog=by['catalog','server']
    if (any(x['payload'].get('status')!='OK' for x in spans) or
        catalog.get('parent_span_id')!=client.get('span_id') or client.get('parent_span_id')!=server.get('span_id')):
        return result('unknown',[])
    limit=configs['recommendation'].get('max_results');count=p.get('result_count')
    if p.get('status')!='OK' or not integer(count) or not integer(limit) or limit<=0 or count>limit:
        return result('unknown',[])
    if count>0: return result('background',[[]])
    logs=reader.get('business:'+str(trace));cite(logs)
    if not logs: return result('set_valued',deepcopy(HYPOTHESES))
    if len(logs)!=1: return result('unknown',[])
    log=logs[0]['payload']
    # Do not consult reason, scenario, decision_role, or any custody metadata.
    fields=['catalog_count','request_history_count','excluded_catalog_count','eligible_count','result_count']
    if any(not integer(log.get(k)) for k in fields): return result('unknown',[])
    c,h,x,eligible,returned=[log[k] for k in fields]
    if x>min(c,h) or eligible!=c-x or returned!=min(limit,eligible) or returned!=count:
        return result('unknown',[])
    if c==0: return result('identified_exact',[['catalog-empty-response']])
    if x==c and eligible==0: return result('identified_exact',[['expected-request-history-filter']])
    return result('unknown',[])


class PublicEvidenceIndex:
    def __init__(self): self.events={};self.buckets={};self.targets=set()

    def stage(self,items,as_of_ns):
        events=dict(self.events);buckets=dict(self.buckets);targets=set(self.targets);changed=set();admitted=[]
        episode_ids={x['event']['episode_id'] for x in events.values()}
        for item in items:
            e=item['event'];eid=e['evidence_id']
            if e['available_time_ns']>as_of_ns: raise ValueError('future evidence delivery')
            episode_ids.add(e['episode_id'])
            if len(episode_ids)>1: raise ValueError('cross-episode evidence')
            if eid in events:
                if stable_digest(events[eid])!=stable_digest(item): raise ValueError('conflicting duplicate evidence ID')
                continue
            events[eid]=deepcopy(item);admitted.append(eid)
            for key in keys(item):
                buckets[key]=sorted([*buckets.get(key,[]),deepcopy(item)],key=lambda x:x['event']['evidence_id']);changed.add(key)
                if key.startswith('metric:'): targets.add(eid)
        stage=PublicEvidenceIndex();stage.events=events;stage.buckets=buckets;stage.targets=targets
        return stage,{k:buckets[k] for k in sorted(changed)},admitted


class RevisionAdapter:
    def __init__(self,arm):
        if arm not in ('full','versioned','plain-index'): raise ValueError(arm)
        self.arm=arm;self.index=PublicEvidenceIndex();self.graph=VersionedDependencyState(evaluate)
        self.outputs={};self.versions={};self.state_version=0;self.as_of_ns=None
        self.episode_id=None;self.identity_digests={}

    def apply(self,items,as_of_ns):
        started=time.perf_counter_ns()
        if type(as_of_ns) is not int or as_of_ns<0 or (self.as_of_ns is not None and as_of_ns<self.as_of_ns):
            raise ValueError('decision cutoff must not move backward')
        # Full recomputation discards computational indexes, not input identity.
        # Stage the same immutable-ID ledger for every arm before any commit.
        episode_id=self.episode_id;identity_digests=dict(self.identity_digests)
        for item in items:
            event=item['event'];eid=event['evidence_id']
            if episode_id is None: episode_id=event['episode_id']
            if event['episode_id']!=episode_id: raise ValueError('cross-episode evidence')
            digest=stable_digest(item)
            if eid in identity_digests and identity_digests[eid]!=digest:
                raise ValueError('conflicting duplicate evidence ID')
            identity_digests[eid]=digest
        base=PublicEvidenceIndex() if self.arm=='full' else self.index
        staged,changes,admitted=base.stage(items,as_of_ns)
        ingest_ns=time.perf_counter_ns()-started;maintenance_started=time.perf_counter_ns()
        if self.arm=='versioned':
            trace=self.graph.apply(changes,staged.targets)
            self.outputs=self.graph.snapshot();self.state_version=self.graph.state_version
        else:
            versions=dict(self.versions)
            for key,value in changes.items():
                if key not in self.index.buckets or stable_digest(value)!=stable_digest(self.index.buckets[key]): versions[key]=versions.get(key,0)+1
            if self.arm=='full': dirty=set(staged.targets)
            else:
                dirty=set(staged.targets)-set(self.outputs)
                # Strong ordinary index control uses the known query structure,
                # including the positive-result branch that never reads a log.
                for target in staged.targets:
                    metric=staged.events[target]['payload'];tid=str(metric.get('trace_id'))
                    watch={'metric:'+target,'trace:'+tid,'config:catalog','config:recommendation','topology'}
                    if metric.get('result_count')==0: watch.add('business:'+tid)
                    if watch.intersection(changes): dirty.add(target)
            outputs=dict(self.outputs);semantic=[];evidence=[];reads={};count=0;evaluation_ns=0
            for target in sorted(dirty):
                eval_started=time.perf_counter_ns()
                reader=DependencyReader(staged.buckets,versions);value=evaluate(target,reader)
                row,sem,proof=publish_value(value,self.outputs.get(target),reader.reads);outputs[target]=row
                evaluation_ns+=time.perf_counter_ns()-eval_started
                if sem: semantic.append(target)
                if proof: evidence.append(target)
                reads[target]=reader.reads;count+=reader.records_read
            self.outputs=outputs;self.versions=versions
            if changes or dirty: self.state_version+=1
            trace={'state_version':self.state_version,'changed_keys':sorted(changes),'recomputed_targets':sorted(dirty),
                'semantic_changed_targets':semantic,'evidence_changed_targets':evidence,'reused_targets':sorted(set(outputs)-dirty),
                'dependency_reads':reads,'records_read':count,'evaluation_ns':evaluation_ns,
                'dependency_maintenance_ns':time.perf_counter_ns()-maintenance_started-evaluation_ns}
        self.index=staged;self.as_of_ns=as_of_ns
        self.episode_id=episode_id;self.identity_digests=identity_digests
        trace.update({'ingest_index_ns':ingest_ns,'arm':self.arm,'received_records':len(items),'admitted_records':len(admitted),
            'retained_public_records':len(staged.events),'index_buckets':len(staged.buckets),
            'staged_event_map_entries':len(staged.events)})
        return deepcopy(self.outputs),trace

    def checkpoint(self):
        value={'arm':self.arm,'events':self.index.events,'graph':self.graph.checkpoint() if self.arm=='versioned' else None,
            'outputs':self.outputs,'versions':self.versions,'state_version':self.state_version,'as_of_ns':self.as_of_ns,
            'episode_id':self.episode_id,'identity_digests':self.identity_digests}
        return {'state':deepcopy(value),'sha256':stable_digest(value)}

    @classmethod
    def restore(cls,checkpoint):
        value=deepcopy(checkpoint['state'])
        if stable_digest(value)!=checkpoint['sha256']: raise ValueError('adapter checkpoint hash mismatch')
        result=cls(value['arm']);items=list(value['events'].values())
        result.index,_,_=result.index.stage(items,max((i['event']['available_time_ns'] for i in items),default=0))
        # Valid pre-fix checkpoints have the retained public events needed to
        # reconstruct identity. Never rewrite the archived checkpoint itself.
        retained_ids={item['event']['evidence_id']:stable_digest(item) for item in items}
        retained_episode=items[0]['event']['episode_id'] if items else None
        result.episode_id=value.get('episode_id',retained_episode)
        result.identity_digests=value.get('identity_digests',retained_ids)
        if (retained_episode is not None and result.episode_id!=retained_episode) or any(
            result.identity_digests.get(eid)!=digest for eid,digest in retained_ids.items()):
            raise ValueError('checkpoint identity disagrees with retained evidence')
        if result.arm=='versioned': result.graph=VersionedDependencyState.restore(value['graph'],evaluate)
        result.outputs=value['outputs'];result.versions=value['versions'];result.state_version=value['state_version'];result.as_of_ns=value['as_of_ns']
        if items and (type(result.as_of_ns) is not int or max(i['event']['available_time_ns'] for i in items)>result.as_of_ns):
            raise ValueError('checkpoint cutoff excludes retained evidence')
        if result.arm=='versioned' and result.outputs!=result.graph.snapshot(): raise ValueError('checkpoint output mismatch')
        return result
