"""Persist transistor-proxy searches/builds inside the existing reviewed role loop."""
import copy
from pathlib import Path
import shutil
import subprocess
import sys
from runtime import atomic, artifact, event, evidence, identity, read, require

SCHEMA = 'transistor-placement-v1'


def is_device_plan(root, state, problem):
    if problem is not None:
        return problem.get('schema') == SCHEMA
    candidate=state.get('last_result',{}).get('baseline_candidate')
    if not candidate:
        return False
    evidence(root,state,[candidate])
    manifest=read(root/state['artifacts'][candidate]['object'])
    return 'transistor-layout.json' in manifest['files']


def source_payloads(problem):
    """Exact captured inputs; a source label alone is not connectivity evidence."""
    netlist={k:copy.deepcopy(problem[k]) for k in ('technology','devices','ports')}
    netlist['schema']='transistor-netlist-v1'
    rules={k:copy.deepcopy(problem[k]) for k in ('technology','rows','rules','obstacles','reserved_access')}
    rules['schema']='transistor-rules-v1'
    return {'netlist':netlist,'rules':rules}


def validate_sources(root,state,problem):
    from transistor_search import validate_problem
    validate_problem(problem)
    require(problem['technology']==state['project']['technology'],'Device technology differs from project')
    require(all(problem['technology'].values()),'Declare process, release and stack')
    for name,payload in source_payloads(problem).items():
        key=problem['sources'][name]
        evidence(root,state,[key])
        require(state['artifacts'][key]['kind']=='evidence','Capture netlist/rules through evidence entry')
        require(read(root/state['artifacts'][key]['object'])==payload,'Captured '+name+' differs from search problem')
    macro=state['project']['macro']
    for axis in ('width','height'):
        bound=macro.get('max_'+axis+'_um')
        if bound is not None:
            require(problem['constraints']['max_'+axis+'_um']<=bound,'Device search exceeds declared parent bound')


def previous_devices(root,state,candidate,files,review):
    from transistor_search import build_abstract, evaluate
    require('placement_state.json' in files,'Device baseline state missing')
    keys=[files['placement_state.json'],files['transistor-layout.json']]
    evidence(root,state,keys)
    snapshot=read(root/state['artifacts'][keys[0]]['object'])
    layout=read(root/state['artifacts'][keys[1]]['object'])
    require(snapshot.get('schema')=='transistor-placement-state-v1' and
            snapshot['round']==state['round'] and snapshot['candidate']==candidate,'Wrong device baseline identity')
    problem=snapshot['problem']
    validate_sources(root,state,problem)
    require(layout==build_abstract(problem,layout['state']),'Actual abstract output differs from regenerated device plan')
    require(evaluate(problem,snapshot['state'])['state']==evaluate(problem,layout['state'])['state'],
            'Saved device state differs from actual abstract output')
    return snapshot,{'candidate':candidate,'round':state['round'],'artifact':keys[0],'layout':keys[1],
                     'sha256':state['artifacts'][keys[0]]['sha256'],'review':review['id'],
                     'verdict':review['verdict'],'qualification':review['scope']}


def plan_devices(root,state,problem,budget,baseline):
    from transistor_search import search, initial_state
    from search.baseline import previous
    require(state.get('schema_version')==5,'Device search needs a newly initialized schema-5 run')
    require('reflect-'+str(state['round']) not in state['requests'],'Finish saved Reflect request before searching')
    require(state['phase'] in ('learning','awaiting_reflect'),'Search follows reviewed memory inside Reflect')
    if state['round']:
        snapshot,origin=previous(root,state,baseline)
        require(snapshot.get('schema')=='transistor-placement-state-v1','Representation transition needs a new linked run')
        base=snapshot['problem'];problem=copy.deepcopy(problem if problem is not None else base)
        # Refine objectives/bounds explicitly; preserve every actual circuit and rule input.
        require({k:v for k,v in problem.items() if k not in ('constraints','objective')}==
                {k:v for k,v in base.items() if k not in ('constraints','objective')},
                'Device population, terminal mapping or rule changes require a new linked construction run')
        initial=snapshot['state']
    else:
        require(baseline is None and problem is not None,'Initial device search needs captured inputs')
        problem=copy.deepcopy(problem);initial=initial_state(problem)
        origin={'kind':'captured_device_initialization','round':0}
    validate_sources(root,state,problem)
    name='device-search-'+identity({'problem':problem,'budget':budget,'baseline':origin,'initial':initial,'round':state['round']})[:16]
    if name in state['artifacts']:
        evidence(root,state,[name])
        recorded=next(e['payload'] for e in state['events'] if e['operation']=='heuristic_plan' and e['payload']['artifact']==name)
        return dict(recorded,already_recorded=True)
    used=[e['payload'] for e in state['events'] if e['round']==state['round'] and e['operation']=='heuristic_plan']
    require(len(used)<8,'Reflect search call budget exhausted')
    remaining={'evaluations':10000-sum(e['evaluations'] for e in used),
               'steps':100000-sum(e['attempts'] for e in used),
               'seconds':60-sum(e['elapsed_seconds'] for e in used)}
    effective=dict(budget)
    for key,default in [('evaluations',128),('steps',budget.get('evaluations',128)*8),('seconds',5)]:
        value=budget.get(key,default)
        require(type(value) in ((int,) if key!='seconds' else (int,float)) and 0<value<=
                {'evaluations':10000,'steps':100000,'seconds':60}[key],'Invalid search budget '+key)
        require(remaining[key]>0,'Aggregate Reflect search budget exhausted')
        effective[key]=min(value,remaining[key])
    if str(effective.get('algorithm','')).startswith('scipy_'):
        from solver_adapter import search as external_search
        result=external_search(problem,effective,initial)
    else:
        result=search(problem,effective,initial)
    result.update(problem=problem,baseline=origin,objective_identity=identity(problem))
    path=root/'requests'/(name+'.json');atomic(path,result)
    artifact(root,state,name,path,'search')
    routes=[]
    for item in result['selected']:
        rid=name+'-'+item['id']
        state['routes'][rid]={'id':rid,'source':'algorithm','lifecycle':'active','evidence':[name],
            'plan':item,'search':name,'baseline':origin,'mechanism':result['algorithm']+':device-ordering',
            'validation':['device_identity','terminal_mapping','abstract_geometry'],
            'status':'proxy_only','representation':'transistor','round':state['round']}
        routes.append({'id':rid,'area_um2':item['area_um2'],'hpwl_proxy_um':item['hpwl_proxy_um']})
    summary={'artifact':name,'algorithm':result['algorithm'],'baseline':origin,'routes':routes,
        'evaluations':result['evaluations'],'attempts':result['attempts'],'cache_hits':result['cache_hits'],
        'elapsed_seconds':result['elapsed_seconds'],'stop':result['stop'],'qualification':'transistor_proxy'}
    event(state,'heuristic_plan',summary)
    return summary


BUILD = r"""from pathlib import Path
import json
from transistor_search import build_abstract
root=Path(__file__).resolve().parent
spec=json.loads((root/'input.json').read_text())
layout=build_abstract(spec['problem'],spec['state'])
(root/'transistor-layout.json').write_text(json.dumps(layout,sort_keys=True,indent=2,allow_nan=False)+'\n')
print(json.dumps({'qualification':'transistor_proxy','routing':'not_generated'}))
"""


def build_devices(root,state,name):
    from learning_contract import bind_task
    from transistor_search import build_abstract, evaluate
    task=state['task'];route=state['routes'][task['route']]
    require(route.get('representation')=='transistor' and route['round']==state['round']-1,'Wrong transistor route')
    used=sum(a['kind']=='candidate' and a['round']==state['round'] for a in state['artifacts'].values())
    require(used<task['max_candidates'],'Candidate budget exhausted')
    evidence(root,state,[route['search']])
    search=read(root/state['artifacts'][route['search']]['object']);problem=search['problem']
    validate_sources(root,state,problem)
    measured=evaluate(problem,route['plan']['state'])
    require(measured['feasible'],'Selected device plan violates abstract constraints')
    directory=root/'candidates'/name
    require(not directory.exists(),'Candidate exists; keep failed output and use a new ID')
    directory.mkdir()
    atomic(directory/'learning_contract.json',{'task':task['id'],'goals':bind_task(state,task)})
    atomic(directory/'input.json',{'problem':problem,'state':measured['state']})
    for key,source in problem['sources'].items():
        shutil.copyfile(root/state['artifacts'][source]['object'],directory/('source-'+key+'.json'))
    shutil.copyfile(Path(__file__).with_name('transistor_search.py'),directory/'transistor_search.py')
    # runtime.py is copied only if the engine uses the shared require helper.
    engine=(directory/'transistor_search.py').read_text()
    if 'from runtime import' in engine:
        for file in ('runtime.py','dcim_config.py','project_config.py'):
            shutil.copyfile(Path(__file__).with_name(file),directory/file)
    (directory/'build.py').write_text(BUILD,encoding='utf-8')
    argv=[sys.executable,'-B',str(directory/'build.py')]
    atomic(directory/'execution.json',{'state':'prepared','round':state['round'],'task':task,'argv':argv})
    try:
        result=subprocess.run(argv,cwd=str(directory),capture_output=True,timeout=30)
        (directory/'stdout.log').write_bytes(result.stdout);(directory/'stderr.log').write_bytes(result.stderr)
        outcome={'state':'finished','returncode':result.returncode}
    except subprocess.TimeoutExpired as error:
        (directory/'stdout.log').write_bytes(error.stdout or b'');(directory/'stderr.log').write_bytes(error.stderr or b'')
        outcome={'state':'timeout','returncode':None}
    if outcome['returncode']==0:
        try:
            actual=read(directory/'transistor-layout.json')
            require(actual==build_abstract(problem,measured['state']),'Generated device output differs from selected plan')
            atomic(directory/'placement_state.json',{'schema':'transistor-placement-state-v1',
                'round':state['round'],'candidate':name,'problem':problem,'state':actual['state'],
                'parent_baseline':route['baseline'],'search':route['search']})
        except (ValueError,KeyError,TypeError,OSError) as error:
            outcome.update(state='invalid_output',error=str(error))
    atomic(directory/'outcome.json',outcome)
    files={}
    for path in sorted(directory.iterdir()):
        if path.is_file():
            key=name+'-'+path.name;artifact(root,state,key,path,'candidate_file');files[path.name]=key
    atomic(directory/'manifest.json',{'files':files,'outcome':outcome,'task':task,'route':task['route'],
                                    'qualification':'transistor_proxy','physical_verification':'not_run'})
    artifact(root,state,name,directory/'manifest.json','candidate')
    event(state,'builder_execute',{'candidate':name,'outcome':outcome})
    return {'candidate':name,'directory':str(directory),'outcome':outcome,'evidence':[name,*files.values()],
            'next':'Independent Analyst checks the abstract output; physical qualification remains not_run'}
