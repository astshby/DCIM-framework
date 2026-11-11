"""Opted-in actual-byte decoder protocol; synthetic files only, no EDA."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from runtime import atomic,artifact,read,transaction,identity
import physical_scope as ps,physical_builder as pb,hierarchy
from search.model import evaluate,state_from_placements
import test_action_guard as guard_tests

DECODER = """import hashlib,json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[-1]).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.loads(Path(r['outputs']['routed.def']).read_text())
g=json.loads(Path(r['outputs']['layout.gds']).read_text())
assert p==g
out={'schema':'physical-hierarchy-measurement-v1','placements':p,
     'output_sha256':{k:sha(v) for k,v in r['outputs'].items()},
     'source_sha256':sha(r['outputs']['source.cdl']),
     'observations':{'measured_DEF_and_GDS_placements':p,'units':'synthetic geometry; no physical claim'}}
print(json.dumps(out))
"""
DRIVER = """import hashlib,json,sys
from pathlib import Path
action,stage,out,plan,admission,gds,cdl,deffile,scope,hierarchy=sys.argv[1:]
out=Path(out)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if action=='prepare':
 data=json.loads(Path(deffile).read_text())
 d=json.loads(Path(scope).read_text())
 for a in d['actions']:
  if a['operation']=='translate':
   # This fixture's sole leaf a0 is also the sole group descendant.
   for p in data:
    p['x_um']+=a['delta_um'][0];p['y_um']+=a['delta_um'][1]
 for key in ('layout.gds','routed.def'):(out/key).write_text(json.dumps(data))
 (out/'source.cdl').write_bytes(Path(cdl).read_bytes())
 (out/'witness.json').write_text(json.dumps({'schema':'physical-action-witness-v1',
   'plan_sha256':sha(plan),'admission_sha256':sha(admission),
   'outputs':{k:sha(out/k) for k in ('layout.gds','source.cdl','routed.def')}}))
 (out/'scope-witness.json').write_text(json.dumps({'schema':'physical-hierarchy-consumption-v1',
   'scope_sha256':sha(scope),'hierarchy_sha256':sha(hierarchy),
   'output_sha256':{k:sha(out/k) for k in ('layout.gds','source.cdl','routed.def')}}))
 print(json.dumps({'state':'prepared'}))
else:print(json.dumps({'state':'submitted' if action=='submit' else 'terminal','stage':stage,'job_id':123}))
"""

class PhysicalScopeTests(unittest.TestCase):
 def fixture(self):
  helper=guard_tests.ActionGuardTests();helper.addCleanup=self.addCleanup
  run,directory=helper.fixture();base=run.parent.parent
  state=read(run/'state.json');adapter=read(run/state['artifacts']['adapter']['object'])
  problem={'blocks':[{'id':'a0','source':'leafsource','cell':'gate','width_um':1,'height_um':1,'orientations':[0]}],
           'gap_um':0,'max_width_um':10,'max_height_um':10,'nets':[]}
  tree={'schema':hierarchy.SCHEMA,'goal':'dcim','root':'root','frontier':['root'],
        'nodes':[{'id':'root','origin_um':[0,0],'children':['a0'],'ports':{'Z':{'object':'a0','port':'Z'}}},
                 {'id':'a0','origin_um':[1,1],'source':'leafsource','cell':'gate','width_um':1,'height_um':1,'ports':{'Z':{'net':'Z','xy_um':[1,.5]}}}],
        'must':[{'id':'complete','owner':'root','depends_on':['root'],'checks':['drc','source_lvs','erc','power_body','pp_np_seams'],'status':'unknown','evidence':[]}],
        'claims':[]}
  decision={'goal':'dcim','scope':'coarse','region':'root','actions':[{'operation':'translate','object':'root','delta_um':[1,0]}],
    'frozen':[],'algorithm':'explicit_actions','budget':{'actions':1},'decisive_checks':['drc','source_lvs','erc','power_body','pp_np_seams']}
  decoder=base/'decoder.py';decoder.write_text(DECODER)
  driver=base/'driver.py';driver.write_text(DRIVER)
  poses=hierarchy.flatten(tree,problem)
  initial={}
  with transaction(run) as (root,s):
   for label in ps.OUTPUTS:
    p=base/('new-'+label);p.write_text('canonical source' if label=='source.cdl' else json.dumps(poses))
    k='actual-'+label;item=artifact(root,s,k,p,'evidence');initial[label]=k
   consumer={'schema':ps.CONSUMER,'decoder':{'argv':[sys.executable,str(decoder),'--request','{REQUEST}'],
      'dependencies':[{'path':str(decoder),'sha256':ps.digest(decoder)}],'timeout_seconds':5},
      'binding':{'a0':{'def':'a0','gds':'gate'}},'source_sha256':s['artifacts'][initial['source.cdl']]['sha256']}
   after,measurement,transition=hierarchy.decode(tree,problem,decision)
   physical={'schema':'physical-hierarchy-initial-v1','problem':problem,'hierarchy':tree,'outputs':initial,'consumer':consumer}
   q=base/'leafsource.json';atomic(q,{'fixture':'synthetic native source only'});artifact(root,s,'leafsource',q,'evidence')
   q=base/'initial-descriptor.json';atomic(q,physical);artifact(root,s,'bound-initial',q,'evidence')
   measurement,q=ps.measure(root,consumer,problem,tree,{k:root/s['artifacts'][v]['object'] for k,v in initial.items()})
   artifact(root,s,'bound-initial-measurement',q,'evidence')
   s['physical_initial']={'descriptor':'bound-initial','measurement':'bound-initial-measurement'}
   data={'problem':problem,'hierarchy_before':tree,'hierarchy_input':tree,'hierarchy_review':None,'hierarchy':after,
     'scope_decision':decision,'transition':transition,'hierarchy_artifact':'tree','physical':physical,
     'baseline':{'kind':'actual_physical_initialization','round':0}}
   p=base/'tree.json';atomic(p,tree);artifact(root,s,'tree',p,'evidence')
   p=base/'route.json';atomic(p,data);artifact(root,s,'scope-search',p,'search')
   s['routes']['fixture']={'hierarchy':data,'plan':measurement,'search':'scope-search'}
   # Reissue guard for the exact actual input bytes and scope action.
   oldplan=read(root/s['artifacts']['plan']['object'])
   actualbase={k:{'artifact':v,'sha256':s['artifacts'][v]['sha256']} for k,v in initial.items()}
   oldplan['baseline']=actualbase
   guard=adapter['action_guard'];guard['baseline']=actualbase
   records=read(root/s['artifacts']['checks']['object'])
   for record in records['records'].values():record['baseline']=actualbase
   p=base/'bound-checks.json';atomic(p,records);item=artifact(root,s,'bound-checks',p,'evidence')
   oldplan['checks']=[dict(x,artifact='bound-checks',sha256=item['sha256']) for x in oldplan['checks']]
   p=base/'bound-plan.json';atomic(p,oldplan);item=artifact(root,s,'bound-plan',p,'evidence')
   adapter['construction_plan']={'artifact':'bound-plan','sha256':item['sha256']}
   adapter['hierarchy_consumer']=consumer
   adapter['dependencies']=[{'path':str(driver),'sha256':ps.digest(driver)},*consumer['decoder']['dependencies']]
   adapter['commands']={a:[sys.executable,str(driver),a,'{STAGE}','{OUT}','{PLAN}','{ADMISSION}','{PARENT_GDS}','{PARENT_CDL}','{PARENT_DEF}','{SCOPE}','{HIERARCHY}'] for a in ('prepare','submit','collect')}
   adapter['required_checks']+=['power_body','pp_np_seams']
   adapter['deliverables']['physical_scope_witness']='{OUT}/scope-witness.json'
   p=base/'physical-adapter.json';atomic(p,adapter);artifact(root,s,'physical-adapter',p,'evidence')
   s['task'].update(physical_adapter='physical-adapter',construction_plan='bound-plan',scope_decision=decision,module='dcim',stage='module',checks=adapter['required_checks'])
  return run,directory,problem,tree,consumer,initial

 def build(self,run):
  for op in ('prepare','submit','collect'):self.assertEqual(pb.action(run,'candidate',op,'materialize')['returncode'],0)
  return pb.action(run,'candidate','finalize')

 def test_actual_decoder_finalizes_and_recovers_same_candidate(self):
  run,directory,problem,tree,c,initial=self.fixture();result=self.build(run)
  self.assertEqual(result['qualification'],'not_run')
  state=read(run/'state.json');manifest=read(directory/'manifest.json')
  self.assertEqual(manifest['physical_hierarchy'],ps.CONSUMER)
  actual=read(directory/'placement_state.json');self.assertEqual(actual['placements'][0]['x_um'],2)
  self.assertEqual(actual['output_sha256']['source.cdl'],c['source_sha256'])
  with transaction(run) as (root,s):
   s['last_result']={'round':1,'baseline_candidate':'candidate','evidence':['candidate']}
   s['reviews']['1']={'id':'review-1','scope':'failed physical fixture','verdict':'failed','evidence':['candidate']}
  state=read(run/'state.json')
  from search.baseline import previous
  snap,origin=previous(run,state)
  self.assertEqual(snap['placements'],actual['placements']);self.assertEqual(origin['candidate'],'candidate')
  hierarchy.review_records(run,state,{'checks':{'drc':'failed','erc':'incomplete'}})

 def test_initial_actual_binding_measures_bytes(self):
  run,d,p,tree,c,ids=self.fixture()
  with transaction(run) as (root,s):
   s.update(round=0,phase='learning');s['requests']={};s.pop('physical_initial')
   descriptor={'schema':'physical-hierarchy-initial-v1','problem':p,'hierarchy':tree,'outputs':ids,'consumer':c}
   x=run/'descriptor.json';atomic(x,descriptor);artifact(root,s,'initial-physical',x,'evidence')
  ps.bind_initial(run,'initial-physical')
  self.assertIn('physical_initial',read(run/'state.json'))
  with self.assertRaisesRegex(ValueError,'once'):ps.bind_initial(run,'initial-physical')

 def test_rejects_missing_optin_or_postchecks_or_consumption(self):
  for mutation in ('optin','postchecks','scopearg','hierarchyarg','decoderdep'):
   run,d,p,t,c,ids=self.fixture()
   state=read(run/'state.json');spec=read(run/state['artifacts']['physical-adapter']['object'])
   if mutation=='optin':spec.pop('hierarchy_consumer')
   if mutation=='postchecks':spec['required_checks'].remove('power_body')
   if mutation=='scopearg':spec['commands']['prepare'].remove('{SCOPE}')
   if mutation=='hierarchyarg':spec['commands']['prepare'].remove('{HIERARCHY}')
   if mutation=='decoderdep':spec['dependencies']=spec['dependencies'][:1]
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):ps.contract(run,state,state['task'],spec)

 def test_changed_scope_copy_and_decoder_code_reject(self):
  for mutation in ('scope','hierarchy','decoder'):
   run,d,p,t,c,ids=self.fixture();pb.action(run,'candidate','prepare')
   if mutation=='scope':(d/'scope-decision.json').write_text('{}')
   if mutation=='hierarchy':(d/'hierarchy-selected.json').write_text('{}')
   if mutation=='decoder':Path(c['decoder']['dependencies'][0]['path']).write_text('print("{}")')
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):pb.action(run,'candidate','submit','materialize')

 def test_wrong_actual_pose_source_or_witness_reject(self):
  for mutation in ('pose','source','witness'):
   run,d,p,t,c,ids=self.fixture()
   for op in ('prepare','submit','collect'):pb.action(run,'candidate',op,'materialize')
   if mutation=='pose':
    for label in ('layout.gds','routed.def'):
     path=d/'physical'/label;v=read(path);v[0]['x_um']+=.5;atomic(path,v)
    # Reissue a matching ordinary witness: scope decoder still must reject the pose.
   if mutation=='source':(d/'physical/source.cdl').write_text('different circuit')
   witness=read(d/'physical/witness.json');witness['outputs']={k:ps.digest(d/'physical'/k) for k in ps.OUTPUTS};atomic(d/'physical/witness.json',witness)
   w=read(d/'physical/scope-witness.json');w['output_sha256']=witness['outputs']
   if mutation=='witness':w['scope_sha256']='0'*64
   atomic(d/'physical/scope-witness.json',w)
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):pb.action(run,'candidate','finalize')
   self.assertNotIn('candidate',read(run/'state.json')['artifacts'])

 def conditional(self):
  import test_physical_contract as contracts
  h=contracts.PhysicalContractTests();h.addCleanup=self.addCleanup;h.setUp()
  p=copy.deepcopy(h.p);opt=p['physical_contract']['repetitions'].pop()
  p['physical_contract']['seam_options']=[opt]
  cert=copy.deepcopy(h.cert);cert.update(schema='native-seam-construction-v1',scope='exact_pair_construction',
    required_postchecks=['drc','source_lvs','erc','power_body','pp_np_seams'])
  cert['checks']['body_supply']='unknown'
  def save(value):
   sh=contracts.captured(h.root,h.state,'seam',value)
   opt['evidence']['sha256']=sh
  save(cert)
  return h,p,cert,save

 def test_conditional_native_options_keep_fullmasks_and_body_unknown(self):
  from physical_contract import verify_contract_evidence
  h,p,c,save=self.conditional()
  with self.assertRaisesRegex(ValueError,'opted-in'):verify_contract_evidence(h.root,h.state,p)
  bound=verify_contract_evidence(h.root,h.state,p,allow_construction=True)
  self.assertEqual(bound[0]['qualification'],'construction_only_body_unknown')
  self.assertEqual(c['checks']['body_supply'],'unknown')
  e=evaluate(p,h.initial);self.assertTrue(e['feasible']);self.assertEqual(e['area_um2'],20)
  self.assertEqual(e['placements'][1]['height_um'],3)
  # Inactive exact alternative does not waive a different overlapping pose.
  bad=evaluate(p,((0,0,0),(0,2.25,0)))
  self.assertIn('spacing:a:b',bad['violations'])

 def test_conditional_native_invalid_checks_transform_or_reused_certificate_reject(self):
  from physical_contract import verify_contract_evidence
  for mutation in ('bodypass','missingpost','wrongdelta','wrongsource','oldaccepted','topology'):
   h,p,c,save=self.conditional()
   if mutation=='bodypass':c['checks']['body_supply']='passed'
   if mutation=='missingpost':c['required_postchecks'].remove('erc')
   if mutation=='wrongdelta':c['delta_um']=[0,3]
   if mutation=='wrongsource':c['masters'][0]['source_sha256']='0'*64
   if mutation=='oldaccepted':
    c.update(schema='native-seam-evidence-v1',scope='exact_pair_transform');c.pop('required_postchecks');c['checks']['body_supply']='passed'
   if mutation=='topology':p['physical_contract']['seam_options'][0]['second']='missing'
   save(c)
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):verify_contract_evidence(h.root,h.state,p,allow_construction=True)

 def test_route_cannot_replace_original_problem_or_source_hierarchy(self):
  for mutation in ('bounds','leaf','consumer'):
   run,d,p,t,c,ids=self.fixture();state=read(run/'state.json')
   data=state['routes']['fixture']['hierarchy']
   if mutation=='bounds':data['problem']=dict(data['problem'],max_width_um=20)
   if mutation=='leaf':data['hierarchy']=copy.deepcopy(data['hierarchy']);data['hierarchy']['nodes'][1]['cell']='different'
   if mutation=='consumer':data['physical']=copy.deepcopy(data['physical']);data['physical']['consumer']['binding']={'fake':'source'}
   spec=read(run/state['artifacts']['physical-adapter']['object'])
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):ps.contract(run,state,state['task'],spec)

if __name__=='__main__':unittest.main()
