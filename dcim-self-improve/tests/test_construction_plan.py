"""Consumed construction-plan identity and declared-stage regressions; synthetic only."""
import json,hashlib,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from runtime import read,atomic,artifact,transaction
from init_run import initialize
import physical_builder as pb
DRIVER="from pathlib import Path\nimport sys,json,hashlib\naction,stage,out,plan,claimed=sys.argv[1:]\nout=Path(out);p=Path(plan)\nif action=='prepare':\n for name in ('layout.gds','source.cdl','routed.def'):(out/name).write_text('SYNTHETIC placeholder, not silicon')\n witness={'plan_sha256':claimed,'output_sha256':hashlib.sha256((out/'layout.gds').read_bytes()).hexdigest()}\n (out/'witness.json').write_text(json.dumps(witness))\n print(json.dumps({'state':'prepared'}))\nelse:\n # Actual consumed-plan digest is recorded for independent comparison, while\n # witness claim remains the explicit captured digest supplied in test config.\n (out/('consumed-'+action+'-'+stage+'.json')).write_text(json.dumps({'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'plan':json.loads(p.read_text())}))\n print(json.dumps({'state':'submitted' if action=='submit' else 'terminal','stage':stage,'job_id':100+len(stage)}))\n"
def run_case(parent,mode):
 base=parent/('case-'+mode);base.mkdir(exist_ok=False)
 driver=base/'driver.py';driver.write_text(DRIVER)
 cfg=base/'config.json';atomic(cfg,{'work_root':str(base/'runs'),'input_files':{}});run=initialize(cfg,'probe')
 planfile=base/'plan.json';atomic(planfile,{'schema':'synthetic-plan-v1','required_action':'A'})
 checks=['full_periphery','module_connectivity','drc','source_lvs','erc','behavioral']
 with transaction(run) as (root,state):
  item=artifact(root,state,'plan',planfile,'evidence');psha=item['sha256']
  spec={'schema':'private-physical-adapter-v1','commands':{a:[sys.executable,str(driver),a,'{STAGE}','{OUT}','{PLAN}',psha] for a in ('prepare','submit','collect')},
   'dependencies':[{'path':str(driver),'sha256':hashlib.sha256(driver.read_bytes()).hexdigest()}],
   'required_checks':checks,'deliverables':{n:'{OUT}/'+n for n in ('layout.gds','source.cdl','routed.def')},
   'scope':'synthetic API identity audit','timeout_seconds':5,'required_stages':['drc_default','drc_conservative','lvs_erc','function'],
   'construction_plan':{'artifact':'plan','sha256':psha}}
  spec['deliverables']['construction_witness']='{OUT}/witness.json'
  atomic(base/'adapter.json',spec);artifact(root,state,'adapter',base/'adapter.json','evidence')
  state.update(phase='awaiting_builder',round=1,task={'id':'task-1','round':1,'execution':'physical_adapter','physical_adapter':'adapter','construction_plan':'plan','checks':checks,'max_candidates':1,'route':'synthetic'})
 records=[]
 try:
  records.append(pb.action(run,'c1','prepare'))
  c=run/'candidates/c1'
  if mode=='missing_copy':(c/'construction-plan.json').unlink()
  if mode=='tamper_copy':atomic(c/'construction-plan.json',{'schema':'synthetic-plan-v1','required_action':'UNSELECTED'})
  if mode=='wrong_plan_witness':
   w=read(c/'physical/witness.json');w['plan_sha256']='0'*64;atomic(c/'physical/witness.json',w)
  if mode=='wrong_output_witness':
   w=read(c/'physical/witness.json');w['output_sha256']='0'*64;atomic(c/'physical/witness.json',w)
  if mode=='unknown_stage':records.append(pb.action(run,'c1','submit','apr'))
  for stage in spec['required_stages']:
   records.append(pb.action(run,'c1','submit',stage));records.append(pb.action(run,'c1','collect',stage))
  if mode=='tamper_finalize':atomic(c/'construction-plan.json',{'required_action':'UNSELECTED'})
  final=pb.action(run,'c1','finalize')
  result={'finalized':True,'final':final,'records':records,'copied_plan_sha256':hashlib.sha256((c/'construction-plan.json').read_bytes()).hexdigest(),'captured_sha256':psha}
 except Exception as error:
  result={'finalized':False,'error':str(error),'records':records}
 return result

class ConstructionPlanTests(unittest.TestCase):
 def test_exact_plan_and_declared_stages(self):
  with tempfile.TemporaryDirectory() as t:self.assertTrue(run_case(Path(t),'valid')['finalized'])
 def test_changed_or_missing_consumed_copy_never_executes(self):
  for mode in ('tamper_copy','missing_copy','tamper_finalize'):
   with tempfile.TemporaryDirectory() as t:
    result=run_case(Path(t),mode);self.assertFalse(result['finalized'],mode);self.assertIn('Consumed construction plan',result['error'])
 def test_bad_witness_and_unknown_stage_reject(self):
  for mode in ('wrong_plan_witness','wrong_output_witness','unknown_stage'):
   with tempfile.TemporaryDirectory() as t:self.assertFalse(run_case(Path(t),mode)['finalized'],mode)
