"""Plan a staged DCIM campaign; admit only closed, reviewed, frozen run outputs.

This coordinator does not execute EDA or advance a run's role cycle. Accepted
abstract placement is not routed or physically qualified. Full physical stages
remain capability-blocked until actual adapters are implemented.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import re

from dcim_config import digest
from project_config import normalize_project, open_items
from runtime import atomic, cli, encoded, evidence, identity, read, require, run_root

LEGACY_SCHEMA = 'dcim-campaign-v1'
SCHEMA = 'dcim-campaign-v2'
AVAILABLE = {'transistor_proxy','geometry_only'}
ABSTRACT_CHECKS = ['device_identity', 'terminal_mapping', 'abstract_geometry']
PHYSICAL_CHECKS = ['routed_dimensions', 'drc', 'source_lvs', 'function', 'erc']


def _text(value, label):
    require(isinstance(value, str) and value.strip(), 'Missing '+label)
    return value


def _keys(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected), 'Invalid '+label+' fields')


def _legacy_stages(project, profile):
    stages = []
    modules = [m for m in project['modules'] if m['enabled']]
    require(any(m['id']=='sram' for m in modules), 'Campaign requires enabled SRAM')
    require(not {'tile','repeat','macro'} & {m['id'] for m in modules}, 'Module ID collides with campaign stages')
    ordered = sorted(modules, key=lambda m: m['id']!='sram')
    for module in ordered:
        abstract = profile == 'abstract'
        stages.append(dict(id=module['id'], module=module['id'], stage='module',
            dependencies=[] if module['id']=='sram' else ['sram'],
            reference_kinds=['compiler'] if module['id']=='sram' else ['digital_flow'],
            execution='transistor_proxy' if abstract else 'physical_layout',
            checks=ABSTRACT_CHECKS if abstract else PHYSICAL_CHECKS,
            outputs=['transistor-layout.json','placement_state.json'] if abstract
                    else ['layout.gds','source.sp','routed-report.json'],
            scope='transistor_proxy' if abstract else 'qualified module',
            interface_contract=module['interface_contract'], geometry_contract=module['geometry_contract']))
    for name, deps in [('tile',[m['id'] for m in ordered]), ('repeat',['tile']), ('macro',['repeat'])]:
        stages.append(dict(id=name, module='dcim', stage=name, dependencies=deps,
            reference_kinds=['compiler','digital_flow'], execution='connected_layout',
            checks=PHYSICAL_CHECKS, outputs=['layout.gds','source.sp','routed-report.json'],
            scope='qualified '+name, interface_contract=project['verification']['macro_closure_suite'],
            geometry_contract='declared macro width/height'))
    return stages


def _stages(project, profile, schema=SCHEMA):
    if schema==LEGACY_SCHEMA:return _legacy_stages(project,profile)
    # Goal dependencies are independent of how Reflect exposes their relative scopes.
    # Compute roles remain descriptions in project.modules, never prerequisite macros.
    modules={m['id']:m for m in project['modules'] if m['enabled']}
    require('sram' in modules, 'Campaign requires enabled SRAM')
    result=[]
    for goal,deps in [('sram',[]),('dcim',['sram'])]:
        result.append(dict(id=goal,module=goal,stage='module',dependencies=deps,
            reference_kinds=['compiler'] if goal=='sram' else ['compiler','digital_flow'],
            execution='geometry_only' if profile=='abstract' else 'physical_layout',
            checks=['geometry','hierarchy_identity'] if profile=='abstract' else PHYSICAL_CHECKS,
            outputs=['layout.json','placement_state.json','hierarchy_state.json'] if profile=='abstract'
                else ['layout.gds','source.sp','routed-report.json'],
            scope='hierarchy_geometry_only' if profile=='abstract' else 'qualified '+goal,
            interface_contract=modules['sram']['interface_contract'] if goal=='sram' else project['verification']['macro_closure_suite'],
            geometry_contract=modules['sram']['geometry_contract'] if goal=='sram' else 'declared macro width/height'))
    return result

def create(root, project, profile='physical', schema_version=2):
    require(profile in ('physical','abstract'), 'Unknown campaign profile')
    root = Path(root).resolve()
    require(not root.exists(), 'Campaign already exists; create a new version')
    package=Path(__file__).resolve().parents[2]
    require(package not in root.parents and root!=package, 'Campaign outputs must be outside framework source')
    project = normalize_project(project)
    require(schema_version in (1,2),'Unknown campaign schema version')
    schema=LEGACY_SCHEMA if schema_version==1 else SCHEMA
    plan = dict(schema=schema, profile=profile, project=project,
                project_identity=identity(project), stages=_stages(project,profile,schema))
    root.mkdir(parents=True)
    (root/'accepts').mkdir(); (root/'objects').mkdir()
    atomic(root/'plan.json', plan)
    atomic(root/'plan-identity.json', {'identity':identity(plan)})
    return status(root)


def _load(root):
    root = Path(root).resolve()
    require(root.is_dir(), 'Missing campaign root')
    plan = read(root/'plan.json')
    _keys(plan, ('schema','profile','project','project_identity','stages'), 'campaign plan')
    require(plan['schema'] in (SCHEMA,LEGACY_SCHEMA) and plan['profile'] in ('physical','abstract'), 'Unknown campaign schema/profile')
    require(identity(plan)==read(root/'plan-identity.json')['identity'], 'Changed immutable campaign plan')
    require(normalize_project(plan['project'])==plan['project'] and
            identity(plan['project'])==plan['project_identity'], 'Invalid project snapshot')
    require(plan['stages']==_stages(plan['project'],plan['profile'],plan['schema']), 'Unsupported stage contract')
    return root, plan


@contextmanager
def _lock(root):
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _records(root):
    result=[]
    for path in sorted((root/'accepts').glob('*.json')):
        require(not path.is_symlink(), 'Acceptance record cannot be a symlink')
        record=read(path)
        _keys(record, ('sequence','stage','binding','source_run','candidate','round','review_scope',
                       'object_hashes','created_utc'), 'acceptance record')
        require(path.name=='%06d-%s.json'%(record['sequence'],identity(record)), 'Changed acceptance record')
        require(type(record['sequence']) is int and record['sequence']==len(result)+1,
                'Missing or reordered campaign history')
        require(isinstance(record['object_hashes'],dict) and record['object_hashes'], 'Acceptance needs evidence objects')
        for sha in record['object_hashes'].values():
            require(isinstance(sha,str) and re.fullmatch(r'[0-9a-f]{64}',sha), 'Invalid evidence hash')
            obj=root/'objects'/sha
            require(obj.is_file() and not obj.is_symlink() and digest(obj)==sha, 'Changed campaign evidence')
        result.append(dict(record, acceptance=identity(record)))
    return result


def _snapshot_status(root, plan):
    records=_records(root)
    known={s['id'] for s in plan['stages']}
    require(all(r['stage'] in known for r in records), 'Unknown accepted stage')
    latest={r['stage']:r for r in records}
    result={}
    missing=open_items(plan['project'])
    for stage in plan['stages']:
        deps=stage['dependencies']
        parents={d:result[d]['acceptance'] for d in deps if result[d]['status']=='accepted'}
        requirements=[]
        for k,v in plan['project']['technology'].items():
            if not v: requirements.append('technology.'+k)
        for k in ('ratio_definition','storage_bits','input_bits','weight_bits','output_bits','cycles_per_result'):
            if plan['project']['macro'][k] is None: requirements.append('macro.'+k)
        if not stage['interface_contract']: requirements.append('interface_contract')
        if not stage['geometry_contract']: requirements.append('geometry_contract')
        if plan['profile']=='physical' or stage['module']=='dcim':
            if not plan['project']['verification']['macro_closure_suite']: requirements.append('macro_closure_suite')
            for k in ('max_width_um','max_height_um'):
                if plan['project']['macro'][k] is None: requirements.append('macro.'+k)
        binding=dict(campaign_identity=identity(plan), stage=stage['id'],
                     interface_identity=identity({'interface':stage['interface_contract'],
                         'geometry':stage['geometry_contract'],'macro':plan['project']['macro']}), parents=parents)
        selected=latest.get(stage['id'])
        if selected and selected['binding']==binding and len(parents)==len(deps):
            state='accepted'
        elif selected:
            state='stale'
        elif len(parents)!=len(deps):
            state='awaiting_parents'
        elif requirements:
            state='awaiting_inputs'
        elif stage['execution'] not in AVAILABLE:
            state='awaiting_capability'
        else:
            state='ready'
        result[stage['id']]=dict(status=state, binding=binding,
            acceptance=selected['acceptance'] if state=='accepted' else None,
            missing_inputs=requirements,
            missing_capabilities=[] if stage['execution'] in AVAILABLE else [stage['execution']],
            required_checks=stage['checks'], required_outputs=stage['outputs'], scope=stage['scope'],
            module=stage['module'], reference_kinds=stage['reference_kinds'])
    return result,records,missing


def status(root):
    root,plan=_load(root)
    stages,records,missing=_snapshot_status(root,plan)
    return dict(schema=plan['schema'], campaign_identity=identity(plan), profile=plan['profile'], stages=stages,
                accepted_records=len(records), project_open_items=missing,
                complete=all(s['status']=='accepted' for s in stages.values()), eda_launched=False,
                qualification='abstract selections are not physical qualification')


def binding(root, stage):
    current=status(root)
    require(stage in current['stages'], 'Unknown stage')
    item=current['stages'][stage]
    require(item['status'] in ('ready','accepted','stale') and not item['missing_inputs'] and
            not item['missing_capabilities'] and
            len(item['binding']['parents'])==len(next(s for s in _load(root)[1]['stages'] if s['id']==stage)['dependencies']),
            'Stage requires parents, inputs or an implemented capability')
    return item['binding']


def _run_objects(run, ids, state):
    evidence(run,state,ids)
    return {key:state['artifacts'][key]['sha256'] for key in ids}


def _validate_run(run, stage, expected, project_identity, candidate):
    run=run_root(run)
    state=read(run/'state.json')
    require(identity(read(run/'config.json'))==state['config_identity'], 'Changed pinned run configuration')
    require(identity(state['project'])==project_identity and
            normalize_project(read(run/'config.json').get('project',{}))==state['project'], 'Run project/technology differs')
    n=state['round']
    require(type(n) is int and n>0 and state['phase']=='closed', 'Finish Builder, Analyst, memory and final Reflect first')
    keys=['result-'+str(n),'review-'+str(n),'reflect-'+str(n),'reflect-'+str(n)+'-reply',candidate]
    hashes=_run_objects(run,keys,state)
    for key,kind in zip(keys,('builder_result','analyst_review','reflect_request','reflect_reply','candidate')):
        require(state['artifacts'][key]['kind']==kind and state['artifacts'][key]['round']==n,
                'Wrong evidence kind or round: '+key)
    result=read(run/state['artifacts'][keys[0]]['object'])
    review=read(run/state['artifacts'][keys[1]]['object'])
    reply=read(run/state['artifacts'][keys[3]]['object'])
    manifest=read(run/state['artifacts'][candidate]['object'])
    require(state['artifacts'][candidate]['kind']=='candidate' and state['artifacts'][candidate]['round']==n,
            'Candidate must be from current reviewed round')
    require(result=={k:v for k,v in state['last_result'].items() if k!='baseline_candidate'} or
            result==state['last_result'], 'Saved result differs from state')
    require(state['last_result'].get('baseline_candidate')==candidate, 'Candidate is not the selected baseline')
    require(result['round']==n and result['outcome']=='passed' and result.get('baseline_candidate',candidate)==candidate and
            candidate in result['evidence'] and candidate in review['evidence'], 'Candidate must be the passed reviewed baseline')
    require(review['round']==n and review['result_id']==keys[0] and review['verdict']=='passed', 'Current positive Analyst review required')
    require(state['reviews'][str(n)]==dict(review,id=keys[1]), 'Saved Analyst review differs from state')
    require(reply['request_id']==keys[2] and reply['decision']=='close' and reply.get('author')=='ai', 'Final AI Reflect closure required')
    request=read(run/state['artifacts'][keys[2]]['object'])
    require(request['request_digest']==identity({k:v for k,v in request.items() if k!='request_digest'}) and
            reply['request_digest']==request['request_digest'] and
            state['requests'][keys[2]]['request_digest']==request['request_digest'], 'Reflect reply does not match request')
    for token,payload in [(keys[0],result),(keys[1],review),(keys[2],reply)]:
        require(state['submissions'].get(token)==identity(payload), 'Submission identity differs: '+token)
    require('memory:'+str(n) in state['submissions'], 'Current Analyst memory must be committed')
    require(any(m['type']=='reflection' and m['round']==n and keys[3] in m['evidence'] for m in state['memory']),
            'Final concise reflection must be committed')
    ops=[e['operation'] for e in state['events'] if e['round']==n]
    expected_ops=['builder_result','analyst_review','memory_commit','reflect_request','reflect_commit']
    pos=-1
    for op in expected_ops:
        positions=[i for i,x in enumerate(ops) if x==op and i>pos]
        require(positions, 'Missing or out-of-order '+op)
        pos=positions[0]
    task=manifest['task']
    require(task['round']==n and task['id']==result['task_id'] and task['module']==stage['module'] and
            task['stage']==stage['stage'] and task.get('execution')==stage['execution'], 'Run task differs from campaign stage')
    require(task.get('campaign_binding')==expected, 'Task did not freeze current campaign parents and interface')
    require(set(stage['checks'])<=set(task['checks']) and
            all(review['checks'].get(k)=='passed' for k in stage['checks']), 'Missing campaign qualification checks')
    require(review['scope']==stage['scope'], 'Analyst scope differs from declared campaign acceptance')
    require(manifest.get('outcome',{}).get('returncode')==0, 'Builder output failed')
    files=manifest['files']
    require(set(stage['outputs'])<=set(files), 'Missing required actual outputs')
    require(set(files.values())<=set(review['evidence']), 'Analyst must bind every candidate output')
    refs={x['id']:x['kind'] for x in state['learning']}
    require(set(stage['reference_kinds'])<={refs[i] for i in task['learning_ids'] if i in refs}, 'Missing stage reference observations')
    all_ids=list(dict.fromkeys(keys+list(files.values())+list(task['learning_ids'])+review['evidence']))
    hashes.update(_run_objects(run,all_ids,state))
    if stage['execution']=='geometry_only':
        from hierarchy import flatten
        from search.baseline import measured_placements
        from search.model import state_from_placements
        required=['placement_state.json','layout.json','hierarchy_state.json']
        evidence(run,state,[files[x] for x in required])
        placement=read(run/state['artifacts'][files['placement_state.json']]['object'])
        tree=read(run/state['artifacts'][files['hierarchy_state.json']]['object'])
        actual=measured_placements(placement['problem'],read(run/state['artifacts'][files['layout.json']]['object']))
        require(tree['goal']==stage['module'] and
                state_from_placements(placement['problem'],flatten(tree,placement['problem']))==
                state_from_placements(placement['problem'],actual), 'Accepted hierarchy differs from actual geometry')
    if stage['execution']=='transistor_proxy':
        from device_flow import previous_devices
        from transistor_search import evaluate
        snapshot,_=previous_devices(run,state,candidate,files,dict(review,id=keys[1]))
        require(evaluate(snapshot['problem'],snapshot['state'])['feasible'], 'Abstract output violates its constraints')
        hashes.update(_run_objects(run,list(snapshot['problem']['sources'].values()),state))
    return run,state,hashes,review


def accept(root, stage, run, candidate):
    root,plan=_load(root)
    with _lock(root):
        stages,records,_=_snapshot_status(root,plan)
        require(stage in stages, 'Unknown stage')
        expected=binding(root,stage)
        contract=next(s for s in plan['stages'] if s['id']==stage)
        run,state,hashes,review=_validate_run(run,contract,expected,plan['project_identity'],candidate)
        prior=next((r for r in reversed(records) if r['stage']==stage),None)
        if prior and prior['binding']==expected and prior['object_hashes']==hashes:
            return dict(acceptance=prior['acceptance'],already_accepted=True)
        for key,sha in hashes.items():
            source=run/state['artifacts'][key]['object']
            target=root/'objects'/sha
            data=source.read_bytes()
            require(digest(source)==sha,'Run evidence changed during snapshot')
            if not target.exists():
                with target.open('xb') as stream: stream.write(data)
            require(digest(target)==sha, 'Campaign object snapshot differs')
        record=dict(sequence=len(records)+1,stage=stage,binding=expected,source_run=str(run),candidate=candidate,
                    round=state['round'],review_scope=review['scope'],object_hashes=hashes,
                    created_utc=datetime.now(timezone.utc).isoformat())
        sha=identity(record)
        atomic(root/'accepts'/('%06d-%s.json'%(record['sequence'],sha)),record)
        return dict(acceptance=sha,already_accepted=False,status=status(root))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True)
    sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('create'); c.add_argument('--project',required=True); c.add_argument('--profile',choices=('physical','abstract'),default='physical'); c.add_argument('--schema-version',type=int,choices=(1,2),default=2)
    sub.add_parser('status')
    c=sub.add_parser('binding'); c.add_argument('--stage',required=True)
    c=sub.add_parser('accept'); c.add_argument('--stage',required=True); c.add_argument('--run',required=True); c.add_argument('--candidate',required=True)
    a=p.parse_args()
    if a.command=='create': return create(a.root,read(a.project),a.profile,a.schema_version)
    if a.command=='binding': return binding(a.root,a.stage)
    if a.command=='accept': return accept(a.root,a.stage,a.run,a.candidate)
    return status(a.root)


if __name__=='__main__':
    cli(main)
