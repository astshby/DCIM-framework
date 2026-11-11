"""Opt-in physical hierarchy consumption and read-only actual-output reconstruction.

This binds executable measurement provenance and retained circuit identity.
It does not certify the decoder's scientific truth or physical qualification.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import uuid

from runtime import atomic, artifact, evidence, event, identity, read, require, transaction
from search.model import state_from_placements, states_match, evaluate
from physical_contract import verify_contract_evidence

CONSUMER = 'physical-hierarchy-consumer-v1'
OUTPUTS = ('layout.gds','source.cdl','routed.def')
POSTCHECKS = {'drc','source_lvs','erc','power_body','pp_np_seams'}

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def validate_consumer(spec):
    require(isinstance(spec,dict) and set(spec)=={'schema','decoder','binding','source_sha256'}, 'Exact physical hierarchy consumer required')
    require(spec['schema']==CONSUMER, 'Unsupported physical hierarchy consumer')
    require(isinstance(spec['binding'],dict) and spec['binding'], 'Explicit physical leaf/source binding required')
    require(isinstance(spec['source_sha256'],str) and len(spec['source_sha256'])==64 and all(x in '0123456789abcdef' for x in spec['source_sha256']), 'Canonical source SHA256 required')
    d=spec['decoder']
    require(isinstance(d,dict) and set(d)=={'argv','dependencies','timeout_seconds'}, 'Exact read-only decoder contract required')
    require(type(d['timeout_seconds']) is int and 1<=d['timeout_seconds']<=60, 'Bound decoder invocation')
    require(isinstance(d['argv'],list) and len(d['argv'])>=2 and all(isinstance(x,str) and x for x in d['argv']) and d['argv'].count('{REQUEST}')==1, 'Explicit argv and standalone request token required')
    require(all('{' not in x and '}' not in x for x in d['argv'] if x!='{REQUEST}'), 'Unknown decoder argument template')
    require(isinstance(d['dependencies'],list) and d['dependencies'], 'Freeze decoder code and input dependencies')
    paths=[]
    for dep in d['dependencies']:
        require(isinstance(dep,dict) and set(dep)=={'path','sha256'}, 'Exact decoder dependency required')
        p=Path(dep['path']);require(p.is_absolute() and p.is_file() and not p.is_symlink(), 'Decoder dependency must be an absolute regular file')
        require(digest(p)==dep['sha256'], 'Physical decoder dependency changed')
        paths.append(str(p))
    require(len(paths)==len(set(paths)), 'Duplicate decoder dependency')
    require(any(arg in paths for arg in d['argv'][1:]), 'Decoder code must be one of its frozen dependencies')
    for arg in d['argv'][1:]:
        if arg!='{REQUEST}' and Path(arg).is_absolute() and Path(arg).is_file():
            require(arg in paths,'Unfrozen decoder file argument')
    return spec

def measure(root, consumer, problem, hierarchy, outputs, destination=None):
    """Run retained read-only decoder on actual bytes, without supplying target poses."""
    from hierarchy import flatten
    validate_consumer(consumer)
    require(set(outputs)==set(OUTPUTS),'Measure all actual GDS/CDL/DEF outputs')
    files={label:Path(p).resolve() for label,p in outputs.items()}
    require(all(p.is_file() and not p.is_symlink() for p in files.values()),'Actual measurement input missing')
    before={k:digest(p) for k,p in files.items()}
    require(before['source.cdl']==consumer['source_sha256'], 'Actual canonical circuit source changed')
    directory=Path(destination) if destination else Path(root)/'physical-measurements'/uuid.uuid4().hex
    directory.mkdir(parents=True,exist_ok=False)
    request={'schema':'physical-hierarchy-measurement-request-v1','blocks':problem['blocks'],
             'binding':consumer['binding'],'outputs':{k:str(v) for k,v in files.items()}}
    request_path=directory/'request.json';atomic(request_path,request)
    argv=[str(request_path) if x=='{REQUEST}' else x for x in consumer['decoder']['argv']]
    atomic(directory/'execution.json',{'argv':argv,'consumer_identity':identity(consumer),'input_sha256':before})
    proc=subprocess.run(argv,cwd=str(directory),capture_output=True,timeout=consumer['decoder']['timeout_seconds'])
    (directory/'stdout').write_bytes(proc.stdout);(directory/'stderr').write_bytes(proc.stderr)
    require(proc.returncode==0,'Actual physical decoder failed; retained raw measurement output')
    validate_consumer(consumer)
    require({k:digest(p) for k,p in files.items()}==before,'Read-only decoder changed actual outputs')
    result=json.loads(proc.stdout.decode('utf8'))
    require(isinstance(result,dict) and set(result)=={'schema','output_sha256','placements','source_sha256','observations'},'Exact physical measurement record required')
    require(result['schema']=='physical-hierarchy-measurement-v1','Unknown actual measurement schema')
    require(result['output_sha256']==before and result['source_sha256']==before['source.cdl'],'Actual measured output identities differ')
    require(isinstance(result['observations'],dict) and result['observations'],'Actual raw physical observations required')
    actual=state_from_placements(problem,result['placements'])
    expected=state_from_placements(problem,flatten(hierarchy,problem))
    require(states_match(actual,expected),'Actual GDS/DEF placement differs from selected hierarchy')
    require(evaluate(problem,actual)['feasible'],'Measured physical placement violates retained geometric constraints')
    record={'schema':'physical-hierarchy-decoder-record-v1','consumer_identity':identity(consumer),
            'request_sha256':digest(request_path),'output_sha256':before,'measurement':result,
            'qualification':'actual decoder measurement binding; no inherited physical qualification'}
    atomic(directory/'record.json',record)
    return result, directory/'record.json'

def contract(root,state,task,spec):
    data=state['routes'].get(task.get('route'),{}).get('hierarchy')
    consumer=spec.get('hierarchy_consumer')
    if not data:
        require(consumer is None and 'scope_decision' not in task,'Physical hierarchy scope has no decoder route')
        return None
    require(data.get('physical') and consumer is not None,'Physical hierarchy consumer is unavailable')
    binding=state.get('physical_initial')
    require(binding and set(binding)=={'descriptor','measurement'},'Physical hierarchy needs measured initial binding')
    evidence(root,state,[binding['descriptor'],binding['measurement']])
    initial=read(root/state['artifacts'][binding['descriptor']]['object'])
    require(initial==data['physical'],'Physical hierarchy source descriptor changed')
    from hierarchy import circuit_identity
    require(data['problem']==initial['problem'] and circuit_identity(data['hierarchy'])==circuit_identity(initial['hierarchy']),
            'Physical hierarchy changed source population, nets or contract')
    evidence(root,state,list(initial['outputs'].values()))
    evidence(root,state,[b['source'] for b in data['problem']['blocks']])
    validate_consumer(consumer)
    require(identity(consumer)==identity(data['physical']['consumer']), 'Physical consumer differs from actual baseline decoder')
    require(task.get('scope_decision')==data['scope_decision'], 'Physical adapter omitted selected scope')
    require('action_guard' in spec and 'construction_plan' in spec,'Physical hierarchy requires source-bound action admission and construction plan')
    require(POSTCHECKS<=set(task['checks']) and POSTCHECKS<=set(spec['required_checks']),'Physical hierarchy requires seam/body and full physical postchecks')
    require('{SCOPE}' in spec['commands']['prepare'] and '{HIERARCHY}' in spec['commands']['prepare'], 'Physical prepare must consume scope and hierarchy files')
    require('physical_scope_witness' in spec['deliverables'],'Physical scope consumption witness required')
    require(all(dep in spec['dependencies'] for dep in consumer['decoder']['dependencies']),'Adapter must freeze every decoder dependency')
    bindings=verify_contract_evidence(root,state,data['problem'],allow_construction=True)
    require(all(set(b.get('required_postchecks',[]))<=set(task['checks']) and
                set(b.get('required_postchecks',[]))<=set(spec['required_checks']) for b in bindings),
            'Task or adapter omitted conditional seam postchecks')
    return data

def copies(root,state,task,spec,directory,prepare=False):
    data=contract(root,state,task,spec)
    if data is None:return {}
    objects={'scope-decision.json':data['scope_decision'],'hierarchy-input.json':data['hierarchy_before'],
             'hierarchy-selected.json':data['hierarchy'],'physical-consumer.json':spec['hierarchy_consumer']}
    for name,obj in objects.items():
        p=directory/name
        if prepare:atomic(p,obj)
        require(p.is_file() and not p.is_symlink() and read(p)==obj,'Consumed physical scope/hierarchy copy changed')
    return {'SCOPE':str(directory/'scope-decision.json'),'HIERARCHY':str(directory/'hierarchy-selected.json'),
            'HIERARCHY_INPUT':str(directory/'hierarchy-input.json')}

def finalize(root,state,task,spec,directory,actual):
    from hierarchy import interfaces
    data=contract(root,state,task,spec)
    if data is None:return None
    copies(root,state,task,spec,directory)
    outputs={key:actual[key] for key in OUTPUTS}
    result,record=measure(root,spec['hierarchy_consumer'],data['problem'],data['hierarchy'],outputs,directory/'physical-scope-measurements'/uuid.uuid4().hex)
    witness=read(actual['physical_scope_witness'])
    require(isinstance(witness,dict) and witness.get('schema')=='physical-hierarchy-consumption-v1','Physical scope witness schema required')
    require(witness.get('scope_sha256')==digest(directory/'scope-decision.json') and
            witness.get('hierarchy_sha256')==digest(directory/'hierarchy-selected.json') and
            witness.get('output_sha256')==result['output_sha256'],'Physical output did not consume selected scope/hierarchy')
    atomic(directory/'hierarchy_state.json',data['hierarchy'])
    atomic(directory/'scope-transition.json',data['transition'])
    atomic(directory/'hierarchy-interfaces.json',interfaces(data['hierarchy'],data['problem']))
    snapshot={'schema':'physical-hierarchy-placement-state-v1','round':state['round'],'candidate':directory.name,
              'problem':data['problem'],'placements':result['placements'],'hierarchy':data['hierarchy'],
              'physical':data['physical'],'parent_baseline':data['baseline'],'output_sha256':result['output_sha256'],
              'decoder_record':str(record.relative_to(directory))}
    atomic(directory/'placement_state.json',snapshot)
    return snapshot

def previous(root,state,candidate,manifest,review):
    from hierarchy import flatten
    files=manifest['files'];outputs=manifest['physical_outputs']
    require('placement_state.json' in files and 'hierarchy_state.json' in files and 'physical_scope_witness' in outputs,'Physical construction has no declared hierarchy decoder state')
    ids=[files['placement_state.json'],files['hierarchy_state.json']]+[outputs[k] for k in OUTPUTS]+[outputs['physical_scope_witness']]
    evidence(root,state,ids)
    snapshot=read(root/state['artifacts'][files['placement_state.json']]['object'])
    tree=read(root/state['artifacts'][files['hierarchy_state.json']]['object'])
    require(snapshot.get('schema')=='physical-hierarchy-placement-state-v1' and snapshot['round']==state['round'] and snapshot['candidate']==candidate,'Physical hierarchy baseline identity/round differs')
    require(snapshot['hierarchy']==tree,'Retained physical hierarchy differs')
    require('physical' in snapshot and snapshot['physical']['schema']=='physical-hierarchy-initial-v1','Actual decoder provenance missing')
    verify_contract_evidence(root,state,snapshot['problem'],allow_construction=True)
    actual={key:root/state['artifacts'][outputs[key]]['object'] for key in OUTPUTS}
    measured,record=measure(root,snapshot['physical']['consumer'],snapshot['problem'],tree,actual)
    require(measured['output_sha256']==snapshot['output_sha256'],'Physical baseline output snapshot changed')
    require(states_match(state_from_placements(snapshot['problem'],snapshot['placements']),state_from_placements(snapshot['problem'],measured['placements'])),'Physical stored pose differs from remeasurement')
    snapshot=dict(snapshot,placements=measured['placements'],hierarchy=tree,hierarchy_artifact=files['hierarchy_state.json'])
    return snapshot,{'candidate':candidate,'round':state['round'],'artifact':files['placement_state.json'],
                     'layout':outputs['layout.gds'],'sha256':state['artifacts'][files['placement_state.json']]['sha256'],
                     'review':review['id'],'verdict':review['verdict'],'qualification':review['scope']}

def bind_initial(run, descriptor_artifact):
    with transaction(run) as (root,state):
        require(state['round']==0 and 'reflect-0' not in state['requests'] and 'physical_initial' not in state,'Bind actual physical initial input once before Reflect0')
        evidence(root,state,[descriptor_artifact]);descriptor=read(root/state['artifacts'][descriptor_artifact]['object'])
        require(isinstance(descriptor,dict) and set(descriptor)=={'schema','problem','hierarchy','outputs','consumer'},'Exact physical initial descriptor required')
        require(descriptor['schema']=='physical-hierarchy-initial-v1' and set(descriptor['outputs'])==set(OUTPUTS),'Physical initial descriptor scope differs')
        from search.model import validate_problem
        validate_problem(descriptor['problem'])
        validate_consumer(descriptor['consumer'])
        evidence(root,state,[b['source'] for b in descriptor['problem']['blocks']])
        evidence(root,state,list(descriptor['outputs'].values()))
        verify_contract_evidence(root,state,descriptor['problem'],allow_construction=True)
        outputs={k:root/state['artifacts'][v]['object'] for k,v in descriptor['outputs'].items()}
        result,record=measure(root,descriptor['consumer'],descriptor['problem'],descriptor['hierarchy'],outputs)
        rid='physical-initial-measurement';artifact(root,state,rid,record,'evidence')
        state['physical_initial']={'descriptor':descriptor_artifact,'measurement':rid}
        event(state,'physical_hierarchy_initial_binding',{'descriptor':descriptor_artifact,'measurement':rid,'actual_output_sha256':result['output_sha256']})
        return state['physical_initial']
