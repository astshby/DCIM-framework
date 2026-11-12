"""Artifact-bound private physical Builder driver. Never supplies node recipes."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import action_guard
from runtime import atomic,artifact,cli,event,evidence,identity,read,require,transaction


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract(root,state,task):
    from capabilities import task as check_capability
    from architecture import admit
    check_capability(state, task)
    admit(root, state, task, state['routes'].get(task.get('route'), {}).get('plan'))
    key=task.get('physical_adapter');evidence(root,state,[key])
    require(state['artifacts'][key]['kind']=='evidence','Physical adapter must be captured evidence')
    spec=read(root/state['artifacts'][key]['object'])
    required={'schema','commands','dependencies','required_checks','deliverables','scope','timeout_seconds'}
    require(isinstance(spec,dict) and required<=set(spec) and not set(spec)-required-{'required_stages','construction_plan','action_guard'} and spec['schema']=='private-physical-adapter-v1','Unsupported physical adapter')
    stages=spec.get('required_stages',['apr','drc','lvs','function'])
    require(isinstance(stages,list) and 1<=len(stages)<=8 and len(set(stages))==len(stages) and all(isinstance(x,str) and re.fullmatch(r'[a-z][a-z0-9_]{0,63}',x) for x in stages),'Invalid physical stage contract')
    if 'construction_plan' in spec:
        plan=spec['construction_plan']
        require(isinstance(plan,dict) and set(plan)=={'artifact','sha256'} and plan['artifact']==task.get('construction_plan'),'Physical task must bind construction plan')
        evidence(root,state,[plan['artifact']])
        require(state['artifacts'][plan['artifact']]['sha256']==plan['sha256'],'Construction plan identity differs')
        require('construction_witness' in spec['deliverables'],'Plan-driven build requires a consumption witness')
    require(set(spec['commands'])=={'prepare','submit','collect'},'Explicit physical actions required')
    require(type(spec['timeout_seconds']) is int and 1<=spec['timeout_seconds']<=60,'Adapter action must return within 60 seconds')
    require(isinstance(spec['required_checks'],list) and set(spec['required_checks'])<=set(task['checks']), 'Task cannot omit adapter-required complete-module checks')
    require({'full_periphery','module_connectivity','drc','source_lvs','erc','behavioral'}<=set(spec['required_checks']), 'Complete physical module scope required')
    require(isinstance(spec['dependencies'],list) and spec['dependencies'],'Pin adapter code and input dependencies')
    for dep in spec['dependencies']:
        require(set(dep)=={'path','sha256'},'Dependency needs exact identity')
        path=Path(dep['path']);require(path.is_absolute() and path.is_file() and not path.is_symlink(),'Missing physical adapter dependency')
        require(digest(path)==dep['sha256'],'Physical adapter dependency changed: '+str(path))
    require(isinstance(spec['deliverables'],dict) and {'layout.gds','source.cdl','routed.def'}<=set(spec['deliverables']),'Complete physical deliverables required')
    for action,argv in spec['commands'].items():
        require(isinstance(argv,list) and argv and all(isinstance(x,str) and x for x in argv),'Use explicit argv, never a shell command')
    if 'action_guard' in spec:
        action_guard.admit(root,state,task,spec)
    return spec


def action(run,name,operation,stage='apr'):
    require(name and all(c.isalnum() or c in '_-' for c in name),'Simple candidate name required')
    require(operation in ('prepare','submit','collect','finalize'),'Unknown physical action')
    with transaction(run) as (root,state):
        require(state['phase']=='awaiting_builder' and state['task'].get('execution')=='physical_adapter','Physical actions belong to active Builder')
        task=state['task'];spec=contract(root,state,task);directory=root/'candidates'/name
        admission=action_guard.admit(root,state,task,spec) if 'action_guard' in spec else None
        stages=spec.get('required_stages',['apr','drc','lvs','function'])
        require(operation in ('prepare','finalize') or stage in stages,'Unknown physical stage')
        if operation=='prepare':
            require(not directory.exists(),'Candidate already prepared; collect or use a new revision')
            used=sum(1 for p in (root/'candidates').glob('*/physical-execution.json') if read(p).get('round')==state['round'])
            require(used<task['max_candidates'],'Physical candidate budget exhausted')
            directory.mkdir();(directory/'physical').mkdir();(directory/'dependencies').mkdir()
            for index,dep in enumerate(spec['dependencies']):
                shutil.copyfile(dep['path'],directory/'dependencies'/('%04d-%s'%(index,Path(dep['path']).name)))
            if 'construction_plan' in spec:
                key=spec['construction_plan']['artifact']
                shutil.copyfile(root/state['artifacts'][key]['object'],directory/'construction-plan.json')
            atomic(directory/'adapter.json',spec)
            if admission is not None:
                action_guard.capture(root,state,directory,admission)
            atomic(directory/'physical-execution.json',{'round':state['round'],'task':task,'adapter_identity':identity(spec),'actions':[]})
        require(directory.is_dir(),'Prepare physical candidate first')
        if 'construction_plan' in spec:
            consumed=directory/'construction-plan.json'
            require(consumed.is_file() and not consumed.is_symlink() and digest(consumed)==spec['construction_plan']['sha256'],
                    'Consumed construction plan differs from captured plan')
        if admission is not None:
            action_guard.verify_copies(directory,spec,admission)
        journal=read(directory/'physical-execution.json')
        require(journal['round']==state['round'] and journal['task']==task and journal['adapter_identity']==identity(spec),'Physical task changed during execution')
        if operation=='finalize':
            require(name not in state['artifacts'],'Candidate already finalized')
            # Adapter owns its asynchronous job ledger. Reject known live or uncollected work.
            for required_stage in stages:
                submitted=[x for x in journal['actions'] if x['action']=='submit' and x['stage']==required_stage]
                collected=[x for x in journal['actions'] if x['action']=='collect' and x['stage']==required_stage]
                require(len(submitted)==1 and submitted[0].get('returncode')==0 and submitted[0].get('receipt',{}).get('state')=='submitted' and collected and collected[-1]['returncode']==0 and
                        collected[-1].get('receipt',{}).get('state')=='terminal' and collected[-1]['receipt'].get('job_id')==submitted[0]['receipt'].get('job_id'),
                        'Collect every required physical stage before freezing: '+required_stage)
            bindings={'OUT':str(directory/'physical'),'CANDIDATE':name,'STAGE':stage,'PLAN':str(directory/'construction-plan.json'),'ADMISSION':str(directory/'action-admission.json')}
            actual={}
            for label,template in spec['deliverables'].items():
                path=Path(template.format(**bindings)).resolve()
                require(directory.resolve() in path.parents and path.is_file() and not path.is_symlink(),'Missing or escaped physical output '+label)
                actual[label]=path
            if admission is not None:
                action_guard.witness(actual,spec,admission)
            elif 'construction_plan' in spec:
                witness=read(actual['construction_witness'])
                require(witness.get('plan_sha256')==spec['construction_plan']['sha256'] and witness.get('output_sha256')==digest(actual['layout.gds']), 'Physical output does not witness the captured construction plan')
            files={}
            for path in sorted(directory.rglob('*')):
                if path.is_file() and not path.is_symlink():
                    relative=str(path.relative_to(directory));key=name+'-file-'+identity(relative)[:12]
                    artifact(root,state,key,path,'candidate_file');files[relative]=key
            outputs={label:files[str(path.relative_to(directory))] for label,path in actual.items()}
            atomic(directory/'manifest.json',{'files':files,'physical_outputs':outputs,'task':task,
                'route':task['route'],'outcome':{'state':'collected','returncode':0},'qualification':'not_run','scope':spec['scope']})
            artifact(root,state,name,directory/'manifest.json','candidate')
            event(state,'builder_execute',{'candidate':name,'execution':'physical_adapter','qualification':'not_run'})
            return {'candidate':name,'evidence':[name,*files.values()],'directory':str(directory),'qualification':'not_run'}
        values={'OUT':str(directory/'physical'),'CANDIDATE':name,'STAGE':stage,'PLAN':str(directory/'construction-plan.json'),'ADMISSION':str(directory/'action-admission.json')}
        if admission is not None:
            values.update(action_guard.values(directory))
        argv=[s.format(**values) for s in spec['commands'][operation]]
        # Submit is never automatically retried, including after ambiguous failure.
        if operation=='submit':
            require(not any(x['action']=='submit' and x['stage']==stage for x in journal['actions']), 'Submission already attempted; recover its job ledger')
        if operation=='collect':
            submissions=[x for x in journal['actions'] if x['action']=='submit' and x['stage']==stage]
            require(len(submissions)==1 and submissions[0].get('returncode')==0 and submissions[0].get('receipt',{}).get('state')=='submitted', 'Collect requires one successful bound submission')
        index=len(journal['actions']);record={'action':operation,'stage':stage,'argv':argv,'started_epoch':time.time(),'state':'prepared'}
        journal['actions'].append(record);atomic(directory/'physical-execution.json',journal)
        try:
            result=subprocess.run(argv,cwd=str(directory),capture_output=True,timeout=spec['timeout_seconds'])
            (directory/('action-%03d.stdout'%index)).write_bytes(result.stdout)
            (directory/('action-%03d.stderr'%index)).write_bytes(result.stderr)
            record.update(state='returned',returncode=result.returncode)
            if operation in ('submit','collect') and result.returncode==0:
                try: receipt=json.loads(result.stdout.decode('utf-8'))
                except (ValueError,UnicodeError): receipt={}
                record['receipt']=receipt
                expected='submitted' if operation=='submit' else 'terminal'
                valid=(isinstance(receipt,dict) and receipt.get('state')==expected and receipt.get('stage')==stage and
                       type(receipt.get('job_id')) is int and receipt['job_id']>0)
                if operation=='collect':valid=valid and receipt['job_id']==submissions[0]['receipt']['job_id']
                if not valid:record.update(state='invalid_receipt',returncode=-1)
        except subprocess.TimeoutExpired as error:
            (directory/('action-%03d.stdout'%index)).write_bytes(error.stdout or b'')
            (directory/('action-%03d.stderr'%index)).write_bytes(error.stderr or b'')
            record.update(state='timeout',returncode=None)
        record['elapsed_seconds']=time.time()-record['started_epoch'];atomic(directory/'physical-execution.json',journal)
        event(state,'physical_builder_action',{'candidate':name,**record})
        return dict(record,candidate=name,directory=str(directory))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True);p.add_argument('--candidate',required=True)
    p.add_argument('--action',required=True,choices=('prepare','submit','collect','finalize'));p.add_argument('--stage',default='apr')
    a=p.parse_args();return action(a.run,a.candidate,a.action,a.stage)


if __name__=='__main__':cli(main)
