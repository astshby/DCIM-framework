"""Actual Reflect/planner/Builder software scopes; no EDA or physical qualification."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from runtime import atomic,artifact,read,transaction
from init_run import initialize
from test_runtime import layout
import learn,planner,builder,workflow,memory,hierarchy,campaign

class HierarchyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        from test_campaign import project
        cfg=self.root/'config.json';atomic(cfg,{'work_root':'runs','project':project(),'input_files':{}})
        self.run=initialize(cfg,'scope')
        self.ids=[]
        for kind,module,w,h in [('compiler','sram',4,6),('digital_flow','adder',2,3)]:
            p=self.root/(kind+'.json');atomic(p,layout(w,h))
            self.ids.append(learn.learn(self.run,kind,p,'leaf',{'module':module,'process':'TEST','release':'r1','stack':'m1','source_run':'synthetic'})['id'])
        self.problem={'blocks':[dict(id=k,source=self.ids[i],cell='leaf',width_um=w,height_um=h,orientations=[0])
            for k,i,w,h in [('s0',0,4,6),('a0',1,2,3),('a1',1,2,3)]],
            'gap_um':0,'max_width_um':20,'max_height_um':10,'nets':[['s0','a0'],['a0','a1']]}
        initial=[dict(b,x_um=x,y_um=0,rotation_deg=0) for b,x in zip(self.problem['blocks'],[0,6,9])]
        self.problem['initial_placements']=initial
        self.search=planner.plan(self.run,self.problem,{'algorithm':'local','evaluations':1,'seconds':1})['artifact']
        # Stored search problem no longer carries initial_placements.
        state=read(self.run/'state.json');self.problem=read(self.run/state['artifacts'][self.search]['object'])['problem']
        hierarchy.bind_initial(self.run,self.search)
        pin=lambda net,x,y:{'net':net,'xy_um':[x,y]}
        self.tree={'schema':hierarchy.SCHEMA,'goal':'dcim','root':'root','frontier':['root'],
            'nodes':[{'id':'root','origin_um':[0,0],'children':['s0','compute'],'ports':{'OUT':{'object':'compute','port':'OUT'}}},
              {'id':'compute','origin_um':[6,0],'children':['a0','a1'],'ports':{'W':{'object':'a0','port':'W'},'OUT':{'object':'a1','port':'Z'}}},
              dict(self.problem['blocks'][0],origin_um=[0,0],ports={'W':pin('w',0,3)}),
              dict(self.problem['blocks'][1],origin_um=[0,0],ports={'W':pin('w',0,1),'Z':pin('y',2,1)}),
              dict(self.problem['blocks'][2],origin_um=[3,0],ports={'A':pin('y',0,1),'Z':pin('out',2,1)})],
            'must':[{'id':'complete-geometry','owner':'root','depends_on':['root'],'checks':['geometry'],'status':'unknown','evidence':[]}],
            'claims':[{'id':'compute-interface','owner':'compute','depends_on':['compute'],'checks':['interface'],'status':'passed','evidence':[self.ids[1]]}]}
        for n in self.tree['nodes']:n.pop('orientations',None)
        p=self.run/'initial-hierarchy.json';atomic(p,self.tree)
        with transaction(self.run) as (root,state):artifact(root,state,'hierarchy-initial',p,'evidence')
        self.hid='hierarchy-initial';self.n=0

    def decision(self,scope='fine',actions=None):
        return {'goal':self.tree['goal'],'scope':scope,'region':'root','actions':actions or [{'operation':'refine','object':'root'}],
            'frozen':['s0'],'algorithm':'explicit_actions','budget':{'actions':8},'decisive_checks':['geometry','interface']}

    def dispatch(self,d,alter=None):
        route=planner.plan(self.run,scope_decision=d,hierarchy_artifact=self.hid)
        q=workflow.request(self.run);n=read(self.run/'state.json')['round']
        proposal='idea-'+str(n)
        reflection={'type':'reflection','stage':'module','module':self.tree['goal'],'route':route['route'],'scope':'general','status':'uncertain',
            'condition':'Synthetic hierarchical geometry','operation':'Execute scoped leaf-preserving changes',
            'observation':'Software fixture only','next_test':'Compare actual leaves','evidence':[route['artifact']]}
        payload={'request_id':q['id'],'request_digest':q['request_digest'],'author':'ai','comparison':'Synthetic test packet, not autonomous AI judgment',
            'evidence':[route['artifact']],'reflection':reflection,'self_proposal':proposal,
            'proposals':[{'id':proposal,'source':'ai','mechanism':'Synthetic mechanism '+str(n),'difference':'Scope regression '+str(n),
                'expected':'Identity preserved','minimal_test':'Compare actual geometry','stop':'One software candidate','evidence':[route['artifact']]}],
            'decision':'build','task':{'route':route['route'],'module':self.tree['goal'],'stage':'module','goal':'Retain complete DCIM fixture',
                'stop':'One software candidate','checks':['geometry','interface','hierarchy_identity'],'execution':'geometry_only',
                'max_candidates':1,'learning_ids':self.ids,'learning_goals':['scope-learning'],'scope_decision':d}}
        if n==0:
            payload['learning_updates']=[{'id':'scope-learning','module':self.tree['goal'],'stage':'module','scope':'general',
                'condition':'Synthetic retained leaf graph','operation':'Test scoped geometry','observation':'Reference rectangles available',
                'next_test':'Check actual hierarchy','evidence':self.ids,'checks':['geometry']}]
        if hasattr(self,'camp'):
            payload['task']['campaign_binding']=campaign.binding(self.camp,self.tree['goal'])
        if alter:alter(payload)
        p=self.root/'reply.json';atomic(p,payload);workflow.reflect(self.run,payload,p)
        return route

    def complete(self,review_records=None):
        state=read(self.run/'state.json');n=state['round'];generated=builder.build(self.run,'c'+str(n))
        self.assertEqual(generated['outcome']['returncode'],0)
        directory=Path(generated['directory']);self.tree=read(directory/'hierarchy_state.json')
        result={'round':n,'task_id':state['task']['id'],'outcome':'passed','summary':'Synthetic actual geometry only','evidence':generated['evidence']}
        p=self.root/'result.json';atomic(p,result);workflow.result(self.run,result,p)
        review={'round':n,'result_id':'result-'+str(n),'verdict':'passed','scope':'hierarchy_geometry_only','summary':'Software fixture review',
            'evidence':generated['evidence'],'checks':{'geometry':'passed','interface':'passed','hierarchy_identity':'passed'},
            'learning_checks':{'scope-learning':{'conclusion':'supported','observation':'Synthetic fixture','evidence':[generated['candidate']]}}}
        if review_records:
            review['hierarchy_checks']={key:{'status':'passed','evidence':[generated['candidate']]} for key in review_records}
        atomic(p,review);workflow.review(self.run,review,p)
        memory.commit(self.run,{'round':n,'disposition':'no_new','entries':[]})
        state=read(self.run/'state.json');manifest=read(self.run/state['artifacts'][generated['candidate']]['object'])
        self.hid=manifest['files']['hierarchy_state.json'];self.n=n
        return directory

    def test_actual_workflow_coarse_fine_coarse_roundtrip(self):
        d=self.decision('joint',[{'operation':'refine','object':'root'},{'operation':'translate','object':'compute','delta_um':[1,0]}])
        self.dispatch(d);one=self.complete()
        flat=hierarchy.flatten(self.tree,self.problem);xy={p['id']:[p['x_um'],p['y_um']] for p in flat}
        self.assertEqual(xy,{'s0':[0,0],'a0':[7,0],'a1':[10,0]})
        self.assertEqual(self.tree['claims'][0]['status'],'stale')
        identity=hierarchy.circuit_identity(self.tree)
        d=self.decision('fine',[{'operation':'refine','object':'compute'},{'operation':'translate','object':'a0','delta_um':[0,1]}])
        self.dispatch(d);two=self.complete(['compute-interface'])
        self.assertEqual(hierarchy.circuit_identity(self.tree),identity)
        self.assertEqual(self.tree['claims'][0]['status'],'stale') # immutable candidate remains original
        self.dispatch(self.decision('coarse',[{'operation':'compose','object':'compute'}]));three=self.complete()
        self.assertEqual(self.tree['claims'][0]['status'],'passed') # current-round reviewed overlay consumed
        self.assertEqual(hierarchy.circuit_identity(self.tree),identity)
        self.assertEqual(hierarchy.flatten(self.tree,self.problem),read(three/'placement_state.json')['placements'])
        self.assertEqual(read(self.run/'state.json')['task']['stage'],'module')
        self.assertTrue((one/'scope-transition.json').is_file())
        self.assertEqual(read(three/'scope-transition.json')['changed_leaves'],[])

    def test_view_only_keeps_actual_geometry_and_evidence(self):
        before=copy.deepcopy(self.tree)
        after,measure,transition=hierarchy.decode(before,self.problem,self.decision())
        self.assertEqual(hierarchy.flatten(before,self.problem),hierarchy.flatten(after,self.problem))
        self.assertEqual(before['claims'],after['claims']);self.assertEqual(transition['invalidated_records'],[])
        self.dispatch(self.decision());self.complete()
        with self.assertRaisesRegex(ValueError,'Hierarchy baseline'):planner.plan(self.run)
        state=read(self.run/'state.json')
        self.assertEqual(state['task']['stage'],'module')

    def test_invalid_mapping_and_scope_controls(self):
        edits=[
            lambda t:t['nodes'][1].update(ports={}),
            lambda t:t['nodes'][1]['ports']['W'].update(object='s0'),
            lambda t:t['nodes'][1]['children'].append('root'),
            lambda t:t['nodes'][2].update(source='wrong'),
            lambda t:t.update(frontier=['root','compute']),
            lambda t:t['nodes'][2]['ports']['W'].update(xy_um=[5,0])]
        for edit in edits:
            with self.subTest(edit=edit):
                tree=copy.deepcopy(self.tree);edit(tree)
                with self.assertRaises(ValueError):hierarchy.validate(tree,self.problem)
        decisions=[
            self.decision('coarse',[{'operation':'translate','object':'compute','delta_um':[1,0]}]),
            self.decision('joint',[{'operation':'refine','object':'root'},{'operation':'translate','object':'s0','delta_um':[1,0]}]),
            self.decision('joint',[{'operation':'refine','object':'root'},{'operation':'translate','object':'compute','delta_um':[1,0]},
                                  {'operation':'refine','object':'compute'},{'operation':'translate','object':'a0','delta_um':[1,0]}]),
            self.decision('fine',[{'operation':'resize','object':'a0'}])]
        for d in decisions:
            with self.subTest(d=d):
                with self.assertRaises(ValueError):hierarchy.decode(self.tree,self.problem,d)
        for key,value in [('algorithm','scipy_de'),('decisive_checks',[]),('goal','sram')]:
            d=self.decision();d[key]=value
            with self.assertRaises(ValueError):hierarchy.decode(self.tree,self.problem,d)

    def test_previous_artifact_and_recheck_controls(self):
        self.dispatch(self.decision());self.complete()
        self.dispatch(self.decision('coarse',[{'operation':'compose','object':'root'}]));self.complete()
        self.assertEqual(self.tree['frontier'],['root'])
        with self.assertRaisesRegex(ValueError,'immediately previous'):
            planner.plan(self.run,scope_decision=self.decision(),hierarchy_artifact='hierarchy-initial')
        self.dispatch(self.decision());directory=self.complete()
        d=self.decision('coarse',[{'operation':'translate','object':'compute','delta_um':[1,0]}]);d['decisive_checks']=['geometry']
        with self.assertRaisesRegex(ValueError,'invalidated evidence'):
            hierarchy.decode(self.tree,self.problem,d)
        state=read(self.run/'state.json')
        check={'hierarchy_checks':{'compute-interface':{'status':'passed','evidence':[self.ids[1]]}},
               'evidence':[self.ids[1]],'checks':{'interface':'passed'}}
        with self.assertRaisesRegex(ValueError,'current-round'):
            hierarchy.review_records(self.run,state,check)

    def test_reflect_rejects_missing_inherited_checks_and_physical_backend(self):
        with self.assertRaises(ValueError):self.dispatch(self.decision(),lambda p:p['task'].update(checks=['interface']))
        self.assertEqual(read(self.run/'state.json')['phase'],'awaiting_reflect')
        # Existing measured scope route is still immutable; use same open request directly.
        state=read(self.run/'state.json');rid=next(k for k,v in state['routes'].items() if 'hierarchy' in v)
        task=dict(state['routes'][rid]['hierarchy']['scope_decision'])
        with self.assertRaisesRegex(ValueError,'physical'):
            hierarchy.admit(self.run,state,{'module':self.tree['goal'],'stage':'module','execution':'physical_adapter','checks':['geometry'],'scope_decision':task},state['routes'][rid])
        import physical_builder
        with self.assertRaisesRegex(ValueError,'unavailable'):
            physical_builder.contract(self.run,state,{'scope_decision':task})
        with self.assertRaisesRegex(ValueError,'no supported decoder'):
            hierarchy.admit(self.run,state,{'scope_decision':task},{})

    def test_default_campaign_accepts_actual_hierarchy_builder_output(self):
        from test_campaign import project
        self.camp=self.root/'integrated';campaign.create(self.camp,project(),'abstract')
        self.tree['goal']='sram'
        p=self.run/'sram-hierarchy.json';atomic(p,self.tree)
        with transaction(self.run) as (root,state):artifact(root,state,'sram-hierarchy',p,'evidence')
        self.hid='sram-hierarchy'
        route=self.dispatch(self.decision());self.complete()
        q=workflow.request(self.run)
        payload={'request_id':q['id'],'request_digest':q['request_digest'],'author':'ai','comparison':'Synthetic closure',
            'evidence':[route['artifact']],'reflection':{'type':'reflection','stage':'module','module':'sram',
                'route':route['route'],'scope':'general','status':'uncertain','condition':'Fixture completed',
                'operation':'Close software round','observation':'Geometry fixture retained','next_test':'Physical experiment deferred',
                'evidence':[route['artifact']]},'self_proposal':'close-idea',
            'proposals':[{'id':'close-idea','source':'ai','mechanism':'Synthetic closure counterexample',
                'difference':'Final fixture observation','expected':'Retained software scope','minimal_test':'Check stored actual leaves',
                'stop':'No new candidate','evidence':[route['artifact']]}],'decision':'close'}
        p=self.root/'close.json';atomic(p,payload);workflow.reflect(self.run,payload,p)
        result=campaign.accept(self.camp,'sram',self.run,'c1')
        self.assertEqual(result['status']['stages']['sram']['status'],'accepted')
        self.assertEqual(result['status']['stages']['dcim']['status'],'ready')

    def test_geometry_review_cannot_pass_physical_checks(self):
        self.dispatch(self.decision())
        state=read(self.run/'state.json')
        physical=['drc','source_lvs','erc','power_body','pin_access','pp_np_seams',
                  'behavioral','dcim_function','genuine_model_function','routed_dimensions',
                  'unknown_physical_check']
        for key in physical:
            payload={'checks':{'geometry':'passed',key:'passed'}}
            with self.subTest(check=key):
                with self.assertRaisesRegex(ValueError,'cannot pass physical'):
                    hierarchy.review_records(self.run,state,payload)
        hierarchy.review_records(self.run,state,{'checks':{'geometry':'passed','pin_anchor_mapping':'passed',
            'drc':'not_run','source_lvs':'incomplete','erc':'failed'}})
        # The legacy nonhierarchical geometry review contract is preserved.
        legacy=copy.deepcopy(state);legacy['task']['route']='legacy-route'
        hierarchy.review_records(self.run,legacy,{'checks':{'drc':'passed'}})

    def test_remote_net_endpoint_and_unknown_claim_invalidation(self):
        tree=copy.deepcopy(self.tree);tree['frontier']=['s0','compute']
        tree['claims'].append({'id':'unknown-proof','owner':'compute','depends_on':['compute'],
            'checks':['custom_signal_proof'],'status':'passed','evidence':[self.ids[1]]})
        d=self.decision('fine',[{'operation':'translate','object':'s0','delta_um':[0,1]}])
        d['frozen']=[];d['decisive_checks'].append('custom_signal_proof')
        after,_,transition=hierarchy.decode(tree,self.problem,d)
        self.assertIn('w',transition['changed_nets'])
        self.assertIn('a0',transition['connected_leaves'])
        self.assertIn('compute',transition['affected_objects'])
        self.assertEqual({x['id']:x['status'] for x in after['claims']},
            {'compute-interface':'stale','unknown-proof':'stale'})

    def test_stage_guard_uses_runtime_phase_not_supplied_task_id(self):
        self.dispatch(self.decision());self.complete()
        d=self.decision('fine',[{'operation':'refine','object':'compute'}])
        with self.assertRaisesRegex(ValueError,'retrieval stage'):
            self.dispatch(d,lambda p:p['task'].update(stage='macro',id='task-1'))
        state=read(self.run/'state.json')
        self.assertEqual(state['round'],1)
        self.assertEqual(state['task']['stage'],'module')
        self.assertEqual(state['phase'],'awaiting_reflect')

    def test_group_port_name_validation(self):
        for bad in ['', ' ', 7]:
            with self.subTest(name=bad):
                tree=copy.deepcopy(self.tree)
                tree['nodes'][0]['ports']={bad:{'object':'compute','port':'OUT'}}
                with self.assertRaisesRegex(ValueError,'Group port name'):
                    hierarchy.validate(tree,self.problem)

    def test_group_alias_and_distinct_terminal_identity(self):
        tree=copy.deepcopy(self.tree)
        tree['nodes'][1]['ports']['ALIAS']=copy.deepcopy(tree['nodes'][1]['ports']['W'])
        with self.assertRaisesRegex(ValueError,'alias'):
            hierarchy.validate(tree,self.problem)
        # Distinct named leaf terminals may genuinely share the same net and anchor.
        tree=copy.deepcopy(self.tree)
        tree['nodes'][3]['ports']['W2']=copy.deepcopy(tree['nodes'][3]['ports']['W'])
        tree['nodes'][1]['ports']['W2']={'object':'a0','port':'W2'}
        hierarchy.validate(tree,self.problem)

    def test_actual_workflow_review_rejects_physical_pass(self):
        self.dispatch(self.decision());state=read(self.run/'state.json')
        generated=builder.build(self.run,'review-boundary')
        result={'round':1,'task_id':state['task']['id'],'outcome':'passed','summary':'Synthetic geometry only','evidence':generated['evidence']}
        p=self.root/'physical-result.json';atomic(p,result);workflow.result(self.run,result,p)
        review={'round':1,'result_id':'result-1','verdict':'passed','scope':'geometry only','summary':'Negative review control',
                'checks':{'geometry':'passed','interface':'passed','hierarchy_identity':'passed'},
                'evidence':generated['evidence'],
                'learning_checks':{'scope-learning':{'conclusion':'supported','observation':'Fixture','evidence':[generated['candidate']]}}}
        for check in ['drc','source_lvs','erc','power_body','pin_access','behavioral','dcim_function']:
            payload=copy.deepcopy(review);payload['checks'][check]='passed';atomic(p,payload)
            with self.subTest(check=check):
                with self.assertRaisesRegex(ValueError,'cannot pass physical'):
                    workflow.review(self.run,payload,p)
                self.assertEqual(read(self.run/'state.json')['phase'],'awaiting_analyst')
        # Geometry endpoint coverage passes through the same production reviewer.
        review['checks']['pin_anchor_mapping']='passed';atomic(p,review)
        workflow.review(self.run,review,p)
        self.assertEqual(read(self.run/'state.json')['phase'],'awaiting_memory')

    def test_default_campaign_uses_module_goals_and_v1_readable(self):
        from test_campaign import project
        c=self.root/'newcampaign';campaign.create(c,project(),'abstract')
        stages=campaign.status(c)['stages']
        self.assertEqual(set(stages),{'sram','dcim'})
        self.assertEqual(stages['dcim']['module'],'dcim')
        old=self.root/'oldcampaign';campaign.create(old,project(),'abstract',schema_version=1)
        self.assertIn('tile',campaign.status(old)['stages'])

if __name__=='__main__':unittest.main()
