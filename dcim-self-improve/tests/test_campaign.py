"""Synthetic campaign qualification ledger checks; no EDA or physical claims."""
import copy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import campaign
import transistor_search as ts
from device_flow import source_payloads
from test_transistor_search import problem as transistor_problem
from init_run import initialize
from project_config import normalize_project
from runtime import atomic,artifact,identity,read,transaction


def project():
    value=normalize_project({'technology':{'process':'TEST','release':'r1','stack':'m1'},
        'macro':{'ratio_definition':'stored words per lane','storage_bits':512,'input_bits':1,
                 'weight_bits':1,'output_bits':8,'cycles_per_result':1,'max_width_um':40,'max_height_um':130},
        'verification':{'macro_closure_suite':'frozen TEST macro suite'}})
    for module in value['modules']:
        module['interface_contract']='TEST '+module['id']+' interface v1'
        module['geometry_contract']='TEST aligned device rows v1'
    return value


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.camp=self.root/'campaign'; self.project=project()
        campaign.create(self.camp,self.project,'abstract')
        self.count=0

    def closed_run(self,stage='sram',change=None):
        # Protocol records are explicit fixtures. This exercises acceptance
        # binding, not AI reasoning or physical verification.
        self.count+=1
        config=self.root/('config%d.json'%self.count)
        atomic(config,{'work_root':'runs','project':self.project,'input_files':{}})
        run=initialize(config,'run%d'%self.count)
        expected=campaign.binding(self.camp,stage)
        contract=next(s for s in read(self.camp/'plan.json')['stages'] if s['id']==stage)
        with transaction(run) as (root,state):
            state.update(round=1,phase='closed')
            task={'round':1,'id':'task-1','module':contract['module'],'stage':contract['stage'],
                  'execution':contract['execution'],'checks':contract['checks'],
                  'campaign_binding':expected,'learning_ids':['learn-ref']}
            problem=transistor_problem(); problem['technology']=copy.deepcopy(self.project['technology'])
            for key,payload in source_payloads(problem).items():
                atomic(root/('source-'+key+'.json'),payload)
                artifact(root,state,problem['sources'][key],root/('source-'+key+'.json'),'evidence')
            device_state=ts.initial_state(problem)
            data=ts.build_abstract(problem,device_state)
            atomic(root/'layout-fixture.json',data)
            artifact(root,state,'cand-layout',root/'layout-fixture.json','candidate_file')
            atomic(root/'placement-fixture.json',{'schema':'transistor-placement-state-v1',
                'round':1,'candidate':'candidate1','problem':problem,'state':device_state})
            artifact(root,state,'cand-placement',root/'placement-fixture.json','candidate_file')
            refs={'sram':'compiler'}
            atomic(root/'reference-fixture.json',{'source':'synthetic'})
            artifact(root,state,'learn-ref',root/'reference-fixture.json','reference_layout')
            state['learning']=[{'id':'learn-ref','kind':refs.get(stage,'digital_flow')}]
            files={'transistor-layout.json':'cand-layout','placement_state.json':'cand-placement'}
            manifest={'task':task,'files':files,'outcome':{'state':'finished','returncode':0}}
            atomic(root/'manifest-fixture.json',manifest)
            artifact(root,state,'candidate1',root/'manifest-fixture.json','candidate')
            ev=['candidate1','cand-layout','cand-placement']
            result={'round':1,'task_id':'task-1','outcome':'passed','summary':'Synthetic candidate',
                    'evidence':ev,'baseline_candidate':'candidate1'}
            review={'round':1,'result_id':'result-1','verdict':'passed','scope':contract['scope'],
                    'summary':'Synthetic protocol check','checks':{k:'passed' for k in contract['checks']},'evidence':ev}
            request={'id':'reflect-1','source':'real_ai_reply_required'}
            request['request_digest']=identity(request)
            reply={'request_id':'reflect-1','request_digest':request['request_digest'],'author':'ai','decision':'close'}
            for key,doc,kind in [('result-1',result,'builder_result'),('review-1',review,'analyst_review'),
                                 ('reflect-1',request,'reflect_request'),('reflect-1-reply',reply,'reflect_reply')]:
                atomic(root/(key+'.json'),doc); artifact(root,state,key,root/(key+'.json'),kind)
            state['last_result']=result
            state['reviews']['1']=dict(review,id='review-1')
            state['requests']['reflect-1']={'request_digest':request['request_digest']}
            state['submissions']={'result-1':identity(result),'review-1':identity(review),
                                  'reflect-1':identity(reply),'memory:1':'fixture'}
            state['memory']=[{'type':'reflection','round':1,'evidence':['reflect-1-reply']}]
            state['events']=[{'round':1,'operation':op,'payload':{}} for op in
                ('builder_result','analyst_review','memory_commit','reflect_request','reflect_commit')]
            if change: change(root,state)
        return run

    def test_default_plan_names_dependencies_and_no_fabricated_inputs(self):
        state=campaign.status(self.camp)
        self.assertEqual(state['stages']['sram']['status'],'ready')
        self.assertEqual(state['stages']['adder']['status'],'awaiting_parents')
        self.assertEqual(state['stages']['tile']['missing_capabilities'],['connected_layout'])
        self.assertFalse(state['complete']); self.assertFalse(state['eda_launched'])
        other=self.root/'unconfigured'
        campaign.create(other,{},'physical')
        missing=campaign.status(other)['stages']['sram']
        self.assertEqual(missing['status'],'awaiting_inputs')
        self.assertIn('technology.process',missing['missing_inputs'])
        with self.assertRaises(ValueError): campaign.binding(other,'sram')

    def test_accept_is_append_only_and_copies_evidence_for_relocation(self):
        run=self.closed_run(); result=campaign.accept(self.camp,'sram',run,'candidate1')
        self.assertFalse(result['already_accepted'])
        self.assertTrue(campaign.accept(self.camp,'sram',run,'candidate1')['already_accepted'])
        shutil.rmtree(run)
        self.assertEqual(campaign.status(self.camp)['stages']['sram']['status'],'accepted')
        self.assertEqual(len(list((self.camp/'accepts').glob('*.json'))),1)

    def test_missing_analyst_memory_reflect_or_bad_order_rejected(self):
        changes=[lambda r,s:s.update(phase='awaiting_reflect'),
                 lambda r,s:s['submissions'].pop('memory:1'),
                 lambda r,s:s.update(memory=[]),
                 lambda r,s:s['events'].reverse()]
        for change in changes:
            with self.subTest(change=change):
                run=self.closed_run(change=change)
                with self.assertRaises(ValueError): campaign.accept(self.camp,'sram',run,'candidate1')
        self.assertEqual(campaign.status(self.camp)['accepted_records'],0)

    def test_changed_project_configuration_and_wrong_baseline_rejected(self):
        run=self.closed_run(change=lambda r,s:s['project']['technology'].update(process='OTHER'))
        with self.assertRaises(ValueError): campaign.accept(self.camp,'sram',run,'candidate1')
        run=self.closed_run(change=lambda r,s:s['last_result'].update(baseline_candidate='old-candidate'))
        with self.assertRaises(ValueError): campaign.accept(self.camp,'sram',run,'candidate1')
        run=self.closed_run()
        data=read(run/'config.json'); data['project']['macro']['weight_bits']=2; atomic(run/'config.json',data)
        with self.assertRaises(ValueError): campaign.accept(self.camp,'sram',run,'candidate1')

    def test_missing_check_wrong_scope_interface_and_tamper_rejected(self):
        def replace_manifest(root,state,edit):
            path=root/state['artifacts']['candidate1']['object']
            doc=read(path); edit(doc)
            target=root/'changed.json'; atomic(target,doc)
            state['artifacts'].pop('candidate1'); artifact(root,state,'candidate1',target,'candidate')
        for edit in [lambda d:d['task']['campaign_binding'].update(interface_identity='wrong'),
                     lambda d:d['task'].update(execution='geometry_only'),
                     lambda d:d['files'].pop('placement_state.json')]:
            run=self.closed_run(change=lambda r,s:replace_manifest(r,s,edit))
            with self.assertRaises(ValueError): campaign.accept(self.camp,'sram',run,'candidate1')
        run=self.closed_run()
        state=read(run/'state.json')
        (run/state['artifacts']['cand-layout']['object']).write_text('tamper')
        with self.assertRaises(ValueError): campaign.accept(self.camp,'sram',run,'candidate1')

    def test_parent_reselection_invalidates_children_and_preserves_history(self):
        first=self.closed_run(); campaign.accept(self.camp,'sram',first,'candidate1')
        child=self.closed_run('adder'); campaign.accept(self.camp,'adder',child,'candidate1')
        self.assertEqual(campaign.status(self.camp)['stages']['adder']['status'],'accepted')
        # A distinct preserved candidate revision changes the acceptance identity.
        second=self.closed_run()
        with transaction(second) as (root,state):
            path=root/'new-reference.json'; atomic(path,{'source':'second synthetic revision'})
            state['artifacts'].pop('learn-ref'); artifact(root,state,'learn-ref',path,'reference_layout')
        campaign.accept(self.camp,'sram',second,'candidate1')
        status=campaign.status(self.camp)
        self.assertEqual(status['stages']['adder']['status'],'stale')
        self.assertEqual(status['accepted_records'],3)
        with self.assertRaises(ValueError): campaign.accept(self.camp,'adder',child,'candidate1')

    def test_physical_profile_cannot_admit_abstract_layout(self):
        root=self.root/'physical'; campaign.create(root,self.project,'physical')
        self.assertEqual(campaign.status(root)['stages']['sram']['status'],'awaiting_capability')
        with self.assertRaises(ValueError): campaign.binding(root,'sram')
        with self.assertRaises(ValueError): campaign.accept(root,'sram',self.closed_run(),'candidate1')

    def test_changed_ledger_object_or_plan_is_detected(self):
        run=self.closed_run(); campaign.accept(self.camp,'sram',run,'candidate1')
        record=read(next((self.camp/'accepts').glob('*.json')))
        (self.camp/'objects'/next(iter(record['object_hashes'].values()))).write_text('modified')
        with self.assertRaises(ValueError): campaign.status(self.camp)
        other=self.root/'changed-plan'; campaign.create(other,self.project,'abstract')
        plan=read(other/'plan.json'); plan['project']['macro']['weight_bits']=4; atomic(other/'plan.json',plan)
        with self.assertRaises(ValueError): campaign.status(other)


if __name__=='__main__': unittest.main()
