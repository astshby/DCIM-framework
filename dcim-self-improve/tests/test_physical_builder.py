import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from runtime import atomic,artifact,transaction
from init_run import initialize
import physical_builder as pb
DRIVER="from pathlib import Path\nimport sys,json\nmode,action,stage,out=sys.argv[1:]\nout=Path(out)\nif action=='prepare':\n for name in ('layout.gds','source.cdl','routed.def'):(out/name).write_text('SYNTHETIC PLACEHOLDER; NOT AN EDA RESULT')\n print(json.dumps({'state':'prepared'}))\nelif action=='submit':\n print(json.dumps({'state':'submitted','stage':stage,'job_id':100+('apr','drc','lvs','function').index(stage)}))\n if mode=='failed_submit':raise SystemExit(1)\nelse:\n print(json.dumps({'state':'terminal','stage':stage,'job_id':999 if mode=='wrong_job' else 100+('apr','drc','lvs','function').index(stage)}))\n"

class PhysicalBuilderTests(unittest.TestCase):
 def run_case(self,mode):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);driver=base/'driver.py';driver.write_text(DRIVER)
   cfg=base/'config.json';atomic(cfg,{'work_root':'runs','input_files':{}});run=initialize(cfg,'test')
   checks=['full_periphery','module_connectivity','drc','source_lvs','erc','behavioral']
   spec={'schema':'private-physical-adapter-v1','commands':{a:[sys.executable,str(driver),mode,a,'{STAGE}','{OUT}'] for a in ('prepare','submit','collect')},'dependencies':[{'path':str(driver),'sha256':hashlib.sha256(driver.read_bytes()).hexdigest()}],'required_checks':checks,'deliverables':{n:'{OUT}/'+n for n in ('layout.gds','source.cdl','routed.def')},'scope':'synthetic only','timeout_seconds':5}
   atomic(base/'adapter.json',spec)
   with transaction(run) as (root,state):
    artifact(root,state,'adapter',base/'adapter.json','evidence')
    state.update(phase='awaiting_builder',round=1,task={'id':'task-1','round':1,'execution':'physical_adapter','physical_adapter':'adapter','checks':checks,'max_candidates':1,'route':'fixture'})
   pb.action(run,'candidate','prepare')
   if mode=='early':return pb.action(run,'candidate','finalize')
   for stage in ('apr','drc','lvs','function'):
    pb.action(run,'candidate','submit',stage);pb.action(run,'candidate','collect',stage)
   return pb.action(run,'candidate','finalize')
 def test_valid_bound_receipts_can_freeze(self):self.assertEqual(self.run_case('valid')['qualification'],'not_run')
 def test_wrong_job_cannot_freeze(self):
  with self.assertRaises(ValueError):self.run_case('wrong_job')
 def test_failed_submission_cannot_collect_or_freeze(self):
  with self.assertRaises(ValueError):self.run_case('failed_submit')
 def test_uncollected_stages_cannot_freeze(self):
  with self.assertRaises(ValueError):self.run_case('early')

 def test_declared_non_apr_stages_are_required_and_unknown_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);driver=base/'driver.py'
   driver.write_text("from pathlib import Path\nimport sys,json\naction,stage,out=sys.argv[1:]\np=Path(out)\nif action=='prepare':\n for n in ('layout.gds','source.cdl','routed.def'):(p/n).write_text('fixture')\n print(json.dumps({'state':'prepared'}))\nelse: print(json.dumps({'state':'submitted' if action=='submit' else 'terminal','stage':stage,'job_id':17 if stage=='drc_default' else 18}))\n")
   cfg=base/'config.json';atomic(cfg,{'work_root':'runs','input_files':{}});run=initialize(cfg,'test')
   checks=['full_periphery','module_connectivity','drc','source_lvs','erc','behavioral']
   spec={'schema':'private-physical-adapter-v1','commands':{a:[sys.executable,str(driver),a,'{STAGE}','{OUT}'] for a in ('prepare','submit','collect')},'dependencies':[{'path':str(driver),'sha256':hashlib.sha256(driver.read_bytes()).hexdigest()}],'required_checks':checks,'deliverables':{n:'{OUT}/'+n for n in ('layout.gds','source.cdl','routed.def')},'scope':'synthetic only','timeout_seconds':5,'required_stages':['drc_default','drc_conservative']}
   atomic(base/'adapter.json',spec)
   with transaction(run) as (root,state):
    artifact(root,state,'adapter',base/'adapter.json','evidence')
    state.update(phase='awaiting_builder',round=1,task={'id':'task-1','round':1,'execution':'physical_adapter','physical_adapter':'adapter','checks':checks,'max_candidates':1,'route':'fixture'})
   pb.action(run,'candidate','prepare')
   with self.assertRaises(ValueError):pb.action(run,'candidate','submit','apr')
   pb.action(run,'candidate','submit','drc_default');pb.action(run,'candidate','collect','drc_default')
   with self.assertRaises(ValueError):pb.action(run,'candidate','finalize')
   pb.action(run,'candidate','submit','drc_conservative');pb.action(run,'candidate','collect','drc_conservative')
   self.assertEqual(pb.action(run,'candidate','finalize')['qualification'],'not_run')
