"""Create a new executable drawing script and retain every generated candidate."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/tools'))
from geometry import capture_closure, read_gds
from runtime import atomic, artifact, cli, event, evidence, identity, read, require, transaction
from search.baseline import measured_placements
from search.model import state_from_placements, states_match
from learning_contract import bind_task

TOOLS = Path(__file__).resolve().parents[1]/'assets/tools'
DRAW = '''"""Generated Builder program. Modify only in a new candidate revision."""
from pathlib import Path
import json
from layout_tools import generate
root = Path(__file__).resolve().parent
print(json.dumps(generate(json.loads((root/'input.json').read_text()),root)))
'''


def build(run, name):
    from runtime import run_root
    preview=read(run_root(run)/'state.json')
    if (preview.get('task') or {}).get('execution')=='physical_adapter':
        from physical_builder import action
        return action(run,name,'prepare')
    require(name and all(c.isalnum() or c in '_-' for c in name), 'Simple candidate ID required')
    with transaction(run) as (root,state):
        require(state['phase']=='awaiting_builder', 'Builder requires a committed Reflect task')
        task=state['task']
        from capabilities import task as check_capability
        check_capability(state, task)
        from architecture import admit
        admit(root, state, task, state['routes'][task['route']].get('plan'))
        if task.get('execution')=='transistor_proxy':
            from device_flow import build_devices
            return build_devices(root,state,name)
        used=sum(a['kind']=='candidate' and a['round']==state['round'] for a in state['artifacts'].values())
        require(used < task['max_candidates'], 'Candidate budget exhausted')
        route=state['routes'][task['route']]
        require('plan' in route, 'This route needs a measured placement plan before drawing')
        require(route['round']==state['round']-1, 'Builder needs the current Reflect route')
        evidence(root,state,[route['search']])
        search=read(root/state['artifacts'][route['search']]['object'])
        problem=search['problem']
        from physical_contract import verify_contract_evidence
        verify_contract_evidence(root,state,problem)
        directory=root/'candidates'/name
        require(not directory.exists(), 'Candidate already exists; inspect it or use a new revision ID')
        sources={}
        for placement in route['plan']['placements']:
            source=placement['source']
            require(source in task['learning_ids'], 'Task must bind all construction learning inputs')
            evidence(root,state,[source])
            item=next(x for x in state['learning'] if x['id']==source)
            original=state['artifacts'][source]
            saved=root/original['object']
            # Legacy source/origin paths supply format metadata, never a file to open.
            suffix=original.get('suffix', Path(original.get('origin_path', original.get('source', ''))).suffix.lower())
            if suffix == '.json':
                sources[source]=read(saved)['cells']
            else:
                sources[source]=capture_closure(read_gds(saved),[item['observations']['top']])
        directory.mkdir()
        atomic(directory/'learning_contract.json',{'task':task['id'],'goals':bind_task(state,task)})
        atomic(directory/'input.json', {'placements':route['plan']['placements'],'sources':sources,
            'export_gds_precision_m':task.get('export_gds_precision_m')})
        (directory/'draw.py').write_text(DRAW,encoding='utf-8')
        for file in ('geometry.py','layout_tools.py'):
            shutil.copyfile(TOOLS/file,directory/file)
        # Persist identity before launch. On interruption the same candidate is never executed implicitly again.
        atomic(directory/'execution.json',{'state':'prepared','round':state['round'],'task':task,
                                         'argv':[sys.executable,'-B',str(directory/'draw.py')]})
        try:
            result=subprocess.run([sys.executable,'-B',str(directory/'draw.py')],cwd=str(directory),
                                  capture_output=True,timeout=30)
            (directory/'stdout.log').write_bytes(result.stdout)
            (directory/'stderr.log').write_bytes(result.stderr)
            outcome={'state':'finished','returncode':result.returncode}
        except subprocess.TimeoutExpired as error:
            (directory/'stdout.log').write_bytes(error.stdout or b'')
            (directory/'stderr.log').write_bytes(error.stderr or b'')
            outcome={'state':'timeout','returncode':None}
        if outcome['returncode']==0:
            try:
                placements=measured_placements(problem,read(directory/'layout.json'))
                require(states_match(state_from_placements(problem,placements),state_from_placements(problem,route['plan']['placements'])),
                        'Generated coordinates differ from selected plan')
                from search.model import evaluate as evaluate_actual
                require(evaluate_actual(problem,state_from_placements(problem,placements))['feasible'], 'Generated output violates its physical placement contract')
                atomic(directory/'placement_state.json',{'schema':'coordinate-placement-v1',
                    'round':state['round'],'candidate':name,'problem':problem,'placements':placements,
                    'parent_baseline':route['baseline'],'search':route['search']})
            except (OSError,ValueError,KeyError,TypeError) as error:
                outcome.update(state='invalid_output',error=str(error))
        atomic(directory/'outcome.json',outcome)
        files={}
        for path in sorted(directory.iterdir()):
            if path.is_file():
                key=name+'-'+path.name
                artifact(root,state,key,path,'candidate_file')
                files[path.name]=key
        atomic(directory/'manifest.json',{'files':files,'outcome':outcome,'task':task,'route':task['route'],
                                         'qualification':'not_run'})
        artifact(root,state,name,directory/'manifest.json','candidate')
        event(state,'builder_execute',{'candidate':name,'outcome':outcome})
        return {'candidate':name,'directory':str(directory),'outcome':outcome,
                'evidence':[name,*files.values()],'next':'Independent review of actual outputs; report via workflow result'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True)
    p.add_argument('--candidate',required=True)
    a=p.parse_args()
    return build(a.run,a.candidate)


if __name__=='__main__':
    cli(main)
