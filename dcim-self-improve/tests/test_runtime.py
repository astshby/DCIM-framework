"""Synthetic protocol and geometry checks. No EDA or claimed AI reasoning."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/tools'))
from dcim_config import load_config
from init_run import initialize
from runtime import atomic, read, transaction
import builder
import learn
import memory
import planner
import workflow
import roles
import learning_contract
import experience
from geometry import bbox


def layout(w,h):
    return {'cells': {'leaf': {'polygons':[{'layer':1,'datatype':0,'points_um':[[0,0],[w,0],[w,h],[0,h]]}],
                    'labels':[{'text':'A','layer':1,'datatype':0,'origin_um':[0,h/2]}], 'references':[]}}}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.config=self.root/'config.json'
        atomic(self.config,{'work_root':'runs','project':{'technology':{'process':'TEST','release':'r1','stack':'m1'}},'input_files':{}})
        self.run=initialize(self.config,'test')

    def prepare(self):
        ids=[]
        for kind,w,h,module in [('compiler',4,6,'sram'),('digital_flow',2,3,'adder')]:
            path=self.root/(kind+'.json')
            atomic(path,layout(w,h))
            ids.append(learn.learn(self.run,kind,path,'leaf',{'module':module,'process':'TEST','release':'r1','stack':'m1','source_run':'synthetic-fixture'})['id'])
        problem={'blocks':[{'id':'s0','cell':'leaf','source':ids[0],'width_um':4,'height_um':6,'orientations':[0]},
                           {'id':'s1','cell':'leaf','source':ids[0],'width_um':4,'height_um':6,'orientations':[0]},
                           {'id':'a0','cell':'leaf','source':ids[1],'width_um':2,'height_um':3,'orientations':[0,90]}],
                 'gap_um':1,'max_width_um':8,'max_height_um':20,'nets':[['s0','a0'],['s1','a0']]}
        result=planner.plan(self.run,problem,{'evaluations':96,'beam':8,'seconds':2,'seed':4})
        self.ids=ids
        self.route=result['routes'][0]['id']
        self.search=result['artifact']
        return problem,result

    def record(self,kind='reflection',status='uncertain'):
        return {'type':kind,'stage':'module','module':'adder','route':self.route,
                'scope':'general','status':status,'condition':'Synthetic fixture only',
                'operation':'Compose explicit reference blocks', 'observation':'Geometry proxy observed',
                'next_test':'Check overlap and envelope independently', 'evidence':[self.search]}

    def refresh_search(self):
        result=planner.plan(self.run,budget={'algorithm':'anneal','evaluations':64,'seed':4})
        self.route=result['routes'][0]['id']
        self.search=result['artifact']
        return result

    def reply_payload(self,decision='build'):
        state=read(self.run/'state.json')
        if decision=='build' and state['round'] and state['routes'][self.route]['round']!=state['round']:
            self.refresh_search()
        req=workflow.request(self.run)
        round_number=read(self.run/'state.json')['round']
        proposal_id='ai-point-'+str(round_number)
        mechanisms=('Isolate rotation while holding row cuts fixed',
                    'Measure center-wire bias against explicit pin access',
                    'Probe feasibility under a tighter aspect bound')
        payload={'request_id':req['id'],'request_digest':req['request_digest'],'author':'ai',
                 'comparison':'Synthetic test reply; not an AI evaluation', 'evidence':[self.search],
                 'reflection':self.record(),'decision':decision,
                 'self_proposal':proposal_id,
                 'proposals':[{'id':proposal_id,'source':'ai','mechanism':mechanisms[round_number],
                     'difference':'Controlled observation beyond selecting the ranked winner',
                     'expected':'Distinguish geometry and proxy explanations',
                     'minimal_test':'Hold the other variables constant and measure the changed quantity',
                     'stop':'One bounded observation','evidence':[self.search]}],
                 'task':{'route':self.route,'module':'adder','stage':'module','goal':'Synthetic composition',
                         'stop':'One geometry candidate','checks':['geometry'], 'execution':'geometry_only',
                         'max_candidates':2,'learning_ids':self.ids,'learning_goals':['goal-layout']}}
        if round_number==0:
            payload['learning_updates']=[self.learning_goal()]
        return payload

    def learning_goal(self):
        return {'id':'goal-layout','module':'adder','stage':'module','scope':'general',
                'condition':'Observed compiler and digital-flow rectangles; geometry scope only',
                'operation':'Test grouping under the common envelope and separation checks',
                'observation':'Reference geometry motivates a composition hypothesis',
                'next_test':'Check the actually generated parent independently',
                'evidence':self.ids,'checks':['geometry']}

    def learning_check(self, evidence, conclusion='supported'):
        return {'goal-layout':{'conclusion':conclusion,'observation':'Synthetic scope only',
                               'evidence':evidence}}

    def dispatch(self,decision='build'):
        payload=self.reply_payload(decision)
        path=self.root/'reply.json'
        atomic(path,payload)
        workflow.reflect(self.run,payload,path)
        return payload,path

    def complete(self,verdict='passed'):
        state=read(self.run/'state.json')
        n=state['round']
        generated=builder.build(self.run,'candidate'+str(n))
        self.assertEqual(generated['outcome']['returncode'],0)
        payload={'round':n,'task_id':state['task']['id'],'outcome':verdict,
                 'summary':'Synthetic geometry result','evidence':generated['evidence']}
        path=self.root/'result.json'
        atomic(path,payload)
        workflow.result(self.run,payload,path)
        review={'round':n,'result_id':'result-'+str(n),'verdict':verdict,'scope':'geometry only',
                'summary':'Fixture checks', 'checks':{'geometry':verdict},'evidence':generated['evidence'],
                'learning_checks':self.learning_check([generated['candidate']],
                                  'supported' if verdict=='passed' else 'inconclusive')}
        atomic(path,review)
        workflow.review(self.run,review,path)
        return generated

    def test_no_learning_no_reflect_or_builder(self):
        with self.assertRaises(ValueError): workflow.request(self.run)
        with self.assertRaises(ValueError): builder.build(self.run,'early')
        with self.assertRaises(ValueError): memory.commit(self.run,{'round':0,'entries':[],'disposition':'no_new'})

    def test_search_finds_new_feasible_route_and_honors_budget(self):
        problem,result=self.prepare()
        raw=read(self.run/'state.json')
        search=read(self.run/raw['artifacts'][self.search]['object'])
        self.assertFalse(search['trials'][0]['feasible'])
        self.assertTrue(search['selected'])
        self.assertLessEqual(result['evaluations'],96)
        self.assertTrue(all(r['feasible'] for r in search['selected']))
        self.assertTrue(all(r['operation'] != 'initial' for r in search['selected']))
        self.assertGreater(len(search['trials']),len(search['selected']))

    def test_two_rounds_memory_order_idempotency_and_closure(self):
        self.prepare()
        reply,path=self.dispatch()
        workflow.reflect(self.run,reply,path)
        self.assertEqual(read(self.run/'state.json')['round'],1)
        self.complete()
        with self.assertRaises(ValueError): workflow.request(self.run)
        payload={'round':1,'disposition':'new','entries':[self.record('action','supported')]}
        memory.commit(self.run,payload)
        memory.commit(self.run,payload)
        self.refresh_search()
        req=workflow.request(self.run)
        self.assertTrue(any(m['type']=='action' for m in read(req['path'])['memory']))
        self.dispatch()
        self.complete('failed')
        memory.commit(self.run,{'round':2,'disposition':'no_new','entries':[]})
        self.dispatch('close')
        state=read(self.run/'state.json')
        self.assertEqual(state['phase'],'closed')
        self.assertEqual(sum(m['type']=='reflection' for m in state['memory']),3)
        self.assertEqual(sum(a['kind']=='candidate' for a in state['artifacts'].values()),2)

    def test_short_memory_rejects_overflow_and_false_success(self):
        self.prepare(); self.dispatch(); self.complete('failed')
        action=self.record('action','supported')
        with self.assertRaises(ValueError): memory.commit(self.run,{'round':1,'disposition':'new','entries':[action]})
        entry=self.record('experience')
        entry['observation']='x'*241
        with self.assertRaises(ValueError): memory.commit(self.run,{'round':1,'disposition':'new','entries':[entry]})
        self.assertEqual(read(self.run/'state.json')['phase'],'awaiting_memory')

    def test_supersession_retains_history_and_default_reads_current(self):
        self.prepare(); self.dispatch(); self.complete()
        first=memory.commit(self.run,{'round':1,'disposition':'new','entries':[self.record('experience')]})['ids'][0]
        self.dispatch(); self.complete()
        entry=self.record('experience','refuted')
        entry.update(supersedes=first,observation='New evidence refutes prior fixture claim')
        memory.commit(self.run,{'round':2,'disposition':'revised','entries':[entry]})
        state=read(self.run/'state.json')
        self.assertIn(first,[x['id'] for x in state['memory']])
        self.assertNotIn(first,[x['id'] for x in memory.select(state)])

    def test_context_delta_no_repeat_instructions(self):
        self.prepare()
        first=workflow.context(self.run,'reflect')
        second=workflow.context(self.run,'reflect',first['token'])
        self.assertIn('instructions',first['changed'])
        self.assertEqual(second['changed'],{})
        self.dispatch()
        third=workflow.context(self.run,'builder',first['token'])
        self.assertIn('task',third['changed'])
        self.assertNotIn('AGENTS.md',third['changed']['instructions'])
        self.assertNotIn('SKILL.md',third['changed']['instructions'])
        self.assertIn('builder.md',third['changed']['instructions'])
        self.assertNotIn('reflect.md',third['changed']['instruction_scope'])

    def test_immutable_source_and_geometry_script_reproduction(self):
        self.prepare(); self.dispatch()
        # Original reference may disappear; the retained object must remain sufficient.
        (self.root/'compiler.json').unlink()
        generated=builder.build(self.run,'retained')
        directory=Path(generated['directory'])
        self.assertEqual(generated['outcome']['returncode'],0)
        cells=read(directory/'layout.json')['cells']
        measured=bbox(cells,'candidate_top')
        selected=read(self.run/'state.json')['routes'][self.route]['plan']
        self.assertAlmostEqual(measured[2],selected['width_um'])
        self.assertAlmostEqual(measured[3],selected['height_um'])
        self.assertTrue((directory/'draw.py').is_file())
        self.assertTrue((directory/'layout.svg').is_file())
        with self.assertRaises(ValueError): builder.build(self.run,'retained')

    def test_changed_evidence_rejected(self):
        self.prepare(); self.dispatch()
        state=read(self.run/'state.json')
        path=self.run/state['artifacts'][self.ids[0]]['object']
        path.write_text('changed')
        with self.assertRaises(ValueError): builder.build(self.run,'tampered')

    def test_wrong_reply_round_and_digest_rejected(self):
        self.prepare()
        reply,path=self.dispatch()
        reply['request_digest']='wrong'
        with self.assertRaises(ValueError): workflow.reflect(self.run,reply,path)

    def test_atomic_init_rolls_back(self):
        with patch('init_run.shutil.copytree',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError): initialize(self.config,'interrupted')
        self.assertFalse((self.root/'runs/interrupted').exists())
        self.assertTrue(initialize(self.config,'interrupted').is_dir())

    def test_ai_plan_uses_same_geometry_validation_and_idempotency(self):
        self.prepare()
        req=workflow.request(self.run)
        payload={'request_id':req['id'],'request_digest':req['request_digest'],'author':'ai',
                 'comparison':'Fixture AI proposal evaluation','evidence':[self.search],
                 'reflection':self.record(),'decision':'close',
                 'self_proposal':'ai-control',
                 'proposals':[{'id':'ai-control','source':'ai','mechanism':'Explicit order',
                     'difference':'Fixed orientation control for the measured plan',
                     'expected':'Known geometry','minimal_test':'Check envelope','stop':'one trial',
                     'evidence':[self.search], 'plan_spec':{'search':self.search,
                     'order':[0,2,1],'cuts':[1,2],'rotations':[0,0,0]}}]}
        path=self.root/'ai-reply.json'
        atomic(path,payload)
        workflow.reflect(self.run,payload,path)
        workflow.reflect(self.run,payload,path)
        route=read(self.run/'state.json')['routes']['ai-control']
        self.assertTrue(route['plan']['feasible'])
        self.assertEqual(route['plan']['area_um2'],68)

    def test_reflect_requires_ai_point_even_on_closure(self):
        self.prepare()
        for decision in ('build','close'):
            payload=self.reply_payload(decision)
            payload.pop('self_proposal')
            path=self.root/'missing-point.json'
            atomic(path,payload)
            with self.assertRaisesRegex(ValueError,'self_proposal'):
                workflow.reflect(self.run,payload,path)
            self.assertEqual(read(self.run/'state.json')['phase'],'awaiting_reflect')
        payload=self.reply_payload('close')
        payload['proposals']=[]
        atomic(path,payload)
        with self.assertRaisesRegex(ValueError,'new AI self-proposal'):
            workflow.reflect(self.run,payload,path)

    def test_human_and_fake_algorithm_proposals_rejected(self):
        self.prepare()
        for source in ('human','algorithm'):
            payload=self.reply_payload('close')
            payload['proposals'][0]['source']=source
            path=self.root/'wrong-source.json'
            atomic(path,payload)
            with self.assertRaisesRegex(ValueError,'AI-authored'):
                workflow.reflect(self.run,payload,path)
        request=read(workflow.request(self.run)['path'])
        self.assertNotIn('human_feedback',request)
        self.assertEqual(request['allowed_sources'],['ai','algorithm'])

    def test_self_point_must_have_difference_and_test(self):
        self.prepare()
        for key in ('difference','minimal_test'):
            payload=self.reply_payload('close')
            payload['proposals'][0][key]='   '
            path=self.root/'empty-point.json'
            atomic(path,payload)
            with self.assertRaises(ValueError): workflow.reflect(self.run,payload,path)

    def test_renaming_old_mechanism_does_not_count_as_new_point(self):
        self.prepare()
        first,_=self.dispatch()
        self.complete()
        memory.commit(self.run,{'round':1,'disposition':'no_new','entries':[]})
        payload=self.reply_payload('close')
        payload['proposals'][0]['mechanism']='  '+first['proposals'][0]['mechanism'].upper()+'  '
        path=self.root/'repeated-point.json'
        atomic(path,payload)
        with self.assertRaisesRegex(ValueError,'repeats'):
            workflow.reflect(self.run,payload,path)

    def test_feedback_channel_is_removed(self):
        import subprocess
        command=[sys.executable,'-B',str(self.run/'scripts/workflow.py'),
                 '--run',str(self.run),'request','--feedback','unused.json']
        response=subprocess.run(command,capture_output=True,text=True)
        self.assertNotEqual(response.returncode,0)
        self.assertIn('unrecognized arguments',response.stderr)
        self.prepare()
        payload=self.reply_payload('close')
        payload['human_feedback']='obsolete input'
        path=self.root/'feedback.json'
        atomic(path,payload)
        with self.assertRaisesRegex(ValueError,'Unknown Reflect reply field'):
            workflow.reflect(self.run,payload,path)

    def test_open_request_freezes_search_inputs(self):
        problem,_=self.prepare()
        workflow.request(self.run)
        with self.assertRaises(ValueError): planner.plan(self.run,problem,{'evaluations':2})

    def test_history_helper_compatible_with_new_run(self):
        import history
        bundle=self.run/'prompt-bundle'
        bundle.mkdir()
        (bundle/'visible.txt').write_text('Visible AI instructions')
        record=history.record_prompt(self.run,'prompt1',bundle,'Compatibility test')
        self.assertEqual(history.read_record(record)['kind'],'prompt-history')
        (bundle/'visible.txt').write_text('Revised visible AI instructions')
        record2=history.record_prompt(self.run,'prompt2',bundle,'Correction',parent='prompt1')
        self.assertIn('Revised visible',(record2/'changes.diff').read_text())
        self.assertEqual((record/'snapshot/visible.txt').read_text(),'Visible AI instructions')

    def test_pinned_run_entry_is_executable(self):
        self.assertTrue((self.run/'scripts/workflow.py').is_file())
        self.assertTrue((self.run/'assets/tools/layout_tools.py').is_file())
        import subprocess
        result=subprocess.run([sys.executable,'-B',str(self.run/'scripts/workflow.py'),
                               '--run',str(self.run),'status'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['phase'],'learning')

    def test_previous_round_actual_layout_is_first_trial_even_after_failed_review(self):
        self.prepare(); self.dispatch(); generated=self.complete('failed')
        memory.commit(self.run,{'round':1,'disposition':'no_new','entries':[]})
        snapshot=read(Path(generated['directory'])/'placement_state.json')
        result=self.refresh_search()
        state=read(self.run/'state.json')
        raw=read(self.run/state['artifacts'][result['artifact']]['object'])
        self.assertEqual(raw['baseline']['candidate'],'candidate1')
        self.assertEqual(raw['baseline']['verdict'],'failed')
        ctx=workflow.context(self.run,'reflect')
        self.assertTrue(ctx['changed']['prior_routes'])
        self.assertLessEqual(len(ctx['changed']['prior_routes']),8)
        self.assertEqual(raw['trials'][0]['placements'],snapshot['placements'])
        self.assertEqual(raw['trials'][0]['operation'],'initial')
        self.dispatch(); self.complete()
        memory.commit(self.run,{'round':2,'disposition':'no_new','entries':[]})
        with self.assertRaises(ValueError):
            planner.plan(self.run,baseline='candidate1')
        latest=self.refresh_search()
        self.assertEqual(latest['baseline']['candidate'],'candidate2')

    def test_new_search_requires_memory_and_preserves_instance_set(self):
        problem,_=self.prepare(); self.dispatch(); self.complete()
        with self.assertRaises(ValueError): planner.plan(self.run)
        memory.commit(self.run,{'round':1,'disposition':'no_new','entries':[]})
        changed=copy.deepcopy(problem)
        changed['blocks'][0]['id']='replacement'
        with self.assertRaisesRegex(ValueError,'preserve'):
            planner.plan(self.run,changed)

    def test_missing_previous_layout_does_not_fall_back(self):
        self.prepare(); self.dispatch()
        payload={'round':1,'task_id':'task-1','outcome':'incomplete','summary':'No produced layout','evidence':[self.search]}
        path=self.root/'result.json'; atomic(path,payload)
        workflow.result(self.run,payload,path)
        review={'round':1,'result_id':'result-1','verdict':'incomplete','scope':'no geometry',
                'summary':'Interrupted construction','checks':{'geometry':'not_run'},'evidence':[self.search,'result-1'],
                'learning_checks':self.learning_check(['result-1'],'inconclusive')}
        atomic(path,review); workflow.review(self.run,review,path)
        memory.commit(self.run,{'round':1,'disposition':'no_new','entries':[]})
        with self.assertRaisesRegex(ValueError,'no layout baseline'):
            planner.plan(self.run)

    def test_baseline_tampering_rejected(self):
        self.prepare(); self.dispatch(); generated=self.complete()
        memory.commit(self.run,{'round':1,'disposition':'no_new','entries':[]})
        state=read(self.run/'state.json')
        manifest=read(self.run/state['artifacts'][generated['candidate']]['object'])
        key=manifest['files']['placement_state.json']
        (self.run/state['artifacts'][key]['object']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'Changed evidence'):
            planner.plan(self.run)

    def test_unmeasured_plan_cannot_be_smuggled_into_ai_proposal(self):
        self.prepare()
        payload=self.reply_payload('close')
        payload['proposals'][0]['plan']={'feasible':True}
        path=self.root/'bad-plan.json'; atomic(path,payload)
        with self.assertRaisesRegex(ValueError,'plan_spec'):
            workflow.reflect(self.run,payload,path)

    def test_multiple_candidates_require_explicit_baseline_and_review_binding(self):
        self.prepare(); self.dispatch()
        a=builder.build(self.run,'one'); b=builder.build(self.run,'two')
        payload={'round':1,'task_id':'task-1','outcome':'passed','summary':'Two retained candidates',
                 'evidence':a['evidence']+b['evidence']}
        path=self.root/'result.json'; atomic(path,payload)
        with self.assertRaisesRegex(ValueError,'baseline_candidate'):
            workflow.result(self.run,payload,path)
        payload['baseline_candidate']='two'; atomic(path,payload)
        workflow.result(self.run,payload,path)
        review={'round':1,'result_id':'result-1','verdict':'passed','scope':'geometry',
                'summary':'Check both candidates','checks':{'geometry':'passed'},'evidence':a['evidence'],
                'learning_checks':self.learning_check([a['candidate']])}
        atomic(path,review)
        with self.assertRaisesRegex(ValueError,'baseline'):
            workflow.review(self.run,review,path)
        review['evidence']+=b['evidence']; atomic(path,review)
        workflow.review(self.run,review,path)
        memory.commit(self.run,{'round':1,'disposition':'no_new','entries':[]})
        self.assertEqual(planner.plan(self.run,budget={'evaluations':1})['baseline']['candidate'],'two')
        self.assertEqual(planner.plan(self.run,budget={'evaluations':1,'seed':1},baseline='one')['baseline']['candidate'],'one')

    def test_ai_coordinate_plan_obeys_same_frozen_geometry_contract(self):
        problem,_=self.prepare(); self.dispatch(); generated=self.complete()
        memory.commit(self.run,{'round':1,'disposition':'no_new','entries':[]})
        problem['movable_ids']=[]
        result=planner.plan(self.run,problem,{'evaluations':1})
        self.search=result['artifact']; self.route=result['routes'][0]['id']
        payload=self.reply_payload('close')
        placements=read(Path(generated['directory'])/'placement_state.json')['placements']
        payload['proposals'][0]['plan_spec']={'search':self.search,'placements':placements}
        path=self.root/'reply-coordinates.json'
        placements[0]['x_um']+=1
        atomic(path,payload)
        with self.assertRaisesRegex(ValueError,'Frozen'):
            workflow.reflect(self.run,payload,path)
        placements[0]['x_um']-=1; atomic(path,payload)
        workflow.reflect(self.run,payload,path)

    def test_identical_search_reuses_evidence_without_reexecution(self):
        problem,first=self.prepare()
        with patch('planner.search',side_effect=AssertionError('must not rerun')):
            second=planner.plan(self.run,problem,{'evaluations':96,'beam':8,'seconds':2,'seed':4})
        self.assertTrue(second['already_recorded'])
        self.assertEqual(first['artifact'],second['artifact'])

    def test_different_initial_coordinates_do_not_hit_the_same_search_cache(self):
        problem,first=self.prepare()
        state=read(self.run/'state.json')
        positions=copy.deepcopy(state['routes'][self.route]['plan']['placements'])
        problem['initial_placements']=positions
        second=planner.plan(self.run,problem,{'evaluations':96,'beam':8,'seconds':2,'seed':4})
        self.assertNotEqual(first['artifact'],second['artifact'])
        state=read(self.run/'state.json')
        raw=read(self.run/state['artifacts'][second['artifact']]['object'])
        self.assertEqual(raw['trials'][0]['placements'],positions)

    def test_actual_transform_roundoff_does_not_invalidate_generated_state(self):
        ids=[]
        for kind,module in [('compiler','sram'),('digital_flow','adder')]:
            source=layout(4,6)
            for point in source['cells']['leaf']['polygons'][0]['points_um']:
                point[0]+=1.1; point[1]+=2.2
            path=self.root/(kind+'-offset.json'); atomic(path,source)
            ids.append(learn.learn(self.run,kind,path,'leaf',{'module':module,'process':'TEST','release':'r1',
                                                          'stack':'m1','source_run':'offset-fixture'})['id'])
        problem={'blocks':[{'id':'offset','cell':'leaf','source':ids[0],'width_um':4,'height_um':6,'orientations':[0,90]}],
                 'gap_um':0,'max_width_um':20,'max_height_um':20,'nets':[],'movable_ids':[]}
        problem['initial_placements']=[dict(problem['blocks'][0],x_um=.2,y_um=.3,rotation_deg=90,width_um=6,height_um=4)]
        result=planner.plan(self.run,problem,{'evaluations':1})
        self.ids=ids; self.route=result['routes'][0]['id']; self.search=result['artifact']
        self.dispatch(); generated=self.complete()
        snapshot=read(Path(generated['directory'])/'placement_state.json')
        self.assertAlmostEqual(snapshot['placements'][0]['x_um'],.2)
        memory.commit(self.run,{'round':1,'disposition':'no_new','entries':[]})
        next_result=planner.plan(self.run,budget={'evaluations':1})
        self.assertEqual(next_result['baseline']['candidate'],'candidate1')

    def test_round_search_limits_do_not_create_extra_phases(self):
        problem,_=self.prepare()
        phase=read(self.run/'state.json')['phase']
        for i in range(7):
            planner.plan(self.run,problem,{'evaluations':1,'seed':i})
        with self.assertRaisesRegex(ValueError,'call budget'):
            planner.plan(self.run,problem,{'evaluations':1,'seed':99})
        self.assertEqual(read(self.run/'state.json')['phase'],phase)

    def test_reflect_guide_pinned_and_role_scoped(self):
        first=workflow.context(self.run,'reflect')
        self.assertIn('reflect.md',first['changed']['instructions'])
        self.assertEqual(workflow.context(self.run,'reflect',first['token'])['changed'],{})
        self.prepare(); self.dispatch()
        packet=workflow.context(self.run,'builder')
        self.assertNotIn('reflect.md',packet['changed']['instructions'])
        self.assertTrue((self.run/'scripts/search/algorithms.py').is_file())
        self.assertFalse((self.run/'design').exists())

    def test_initialization_and_pinned_roles_exclude_developer_history(self):
        packet=roles.initialization(self.config)
        self.assertFalse(packet['eda_launched'])
        self.assertIn('open_items',packet)
        first=workflow.context(self.run,'initialize')
        self.assertIn('initialize.md',first['changed']['instructions'])
        self.assertEqual(workflow.context(self.run,'initialize',first['token'])['changed'],{})
        self.assertFalse((self.run/'instructions/HANDOFF.md').exists())
        self.assertFalse((self.run/'instructions/workspace-HANDOFF.md').exists())
        self.assertFalse((self.run/'instructions/framework-history.md').exists())
        import subprocess
        result=subprocess.run([sys.executable,str(self.run/'scripts/roles.py'),'--config',str(self.run/'config.json')],
                              capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Initialization',json.loads(result.stdout)['instructions'])

    def test_learning_targets_required_and_bind_both_reference_kinds(self):
        self.prepare()
        payload=self.reply_payload(); path=self.root/'learning-reply.json'
        for change in ('missing','wrong_module','missing_check','one_source','process'):
            bad=copy.deepcopy(payload)
            if change=='missing': bad['task'].pop('learning_goals')
            if change=='wrong_module': bad['learning_updates'][0]['module']='sram'
            if change=='missing_check': bad['learning_updates'][0]['checks']=['connectivity']
            if change=='one_source': bad['learning_updates'][0]['evidence']=self.ids[:1]
            if change=='process':
                bad['learning_updates'][0].update(scope='process',technology={'process':'OTHER','release':'r1','stack':'m1'})
            atomic(path,bad)
            with self.assertRaises(ValueError): workflow.reflect(self.run,bad,path)
        self.assertEqual(read(self.run/'state.json')['learning_goals'],[])
        atomic(path,payload); workflow.reflect(self.run,payload,path)
        generated=self.complete()
        binding=read(Path(generated['directory'])/'learning_contract.json')
        self.assertEqual(binding['goals'][0]['id'],'goal-layout')
        self.assertEqual(binding['goals'][0]['round'],0)

    def test_foundational_learning_survives_recent_memory_and_corrections(self):
        self.prepare(); self.dispatch(); self.complete()
        memory.commit(self.run,{'round':1,'entries':[],'disposition':'no_new'})
        state=read(self.run/'state.json')
        # Long-run retrieval fixture: newer ordinary records must not crowd out a goal.
        for i in range(20):
            entry=self.record('experience'); entry['id']='later-'+str(i)
            state['memory'].append(entry)
        packet=workflow.context_data(self.run,state,'reflect')
        self.assertEqual(len(packet['memory']),8)
        self.assertEqual(packet['learning_focus'][0]['id'],'goal-layout')
        self.assertEqual(packet['learning_focus'][0]['latest_check']['conclusion'],'supported')
        corrected=self.learning_goal()
        corrected.update(id='goal-revised',supersedes='goal-layout',observation='Apply only to the observed boundary')
        corrected['evidence']=self.ids+['review-1']
        learning_contract.update(self.run,state,[corrected])
        self.assertEqual(len(state['learning_goals']),2)
        self.assertEqual([g['id'] for g in learning_contract.focus(state)],['goal-revised'])
        task=copy.deepcopy(state['task'])
        with self.assertRaisesRegex(ValueError,'superseded'): learning_contract.bind_task(state,task)
        task['learning_goals']=['goal-revised']
        self.assertEqual(learning_contract.bind_task(state,task)[0]['id'],'goal-revised')
        changed=copy.deepcopy(state)
        changed['learning_goals'][-1].update(scope='process',technology=changed['project']['technology'])
        changed['project']['technology']={'process':'NEXT','release':'r2','stack':'m2'}
        self.assertEqual(learning_contract.focus(changed),[])

    def test_analyst_learning_evidence_is_current_and_required(self):
        self.prepare(); self.dispatch()
        generated=builder.build(self.run,'current')
        result={'round':1,'task_id':'task-1','outcome':'passed','summary':'Fixture',
                'evidence':generated['evidence']}
        path=self.root/'check.json'; atomic(path,result); workflow.result(self.run,result,path)
        review={'round':1,'result_id':'result-1','verdict':'passed','scope':'geometry',
                'summary':'Fixture','checks':{'geometry':'passed'},'evidence':generated['evidence']+self.ids}
        for outcomes in ({},self.learning_check(self.ids),
                         {'unbound':{'conclusion':'supported','observation':'bad','evidence':generated['evidence']}}):
            review['learning_checks']=outcomes; atomic(path,review)
            with self.assertRaises(ValueError): workflow.review(self.run,review,path)
        review.update(verdict='incomplete',checks={'geometry':'not_run'},
                      learning_checks=self.learning_check([generated['candidate']]))
        atomic(path,review)
        with self.assertRaisesRegex(ValueError,'completed checks'): workflow.review(self.run,review,path)
        review.update(verdict='failed',checks={'geometry':'failed'},
                      learning_checks=self.learning_check([generated['candidate']],'refuted'))
        atomic(path,review); workflow.review(self.run,review,path)
        self.assertEqual(read(self.run/'state.json')['learning_outcomes'][0]['conclusion'],'refuted')

    def test_reflect_request_reuses_consumed_instructions(self):
        self.prepare()
        context=workflow.context(self.run,'reflect')
        req=workflow.request(self.run,context['token'])
        packet=read(req['path'])
        self.assertEqual(packet['instructions'],{})
        self.assertEqual(set(packet['instruction_hashes']),{'AGENTS.md','SKILL.md','reflect.md'})
        self.assertIn('context_token',req)
        self.dispatch(); self.complete()
        memory.commit(self.run,{'round':1,'entries':[],'disposition':'no_new'})
        fresh=read(workflow.request(self.run)['path'])
        self.assertEqual(set(fresh['instructions']),{'AGENTS.md','SKILL.md','reflect.md'})

    def test_optional_gds_export_preserves_label_attributes(self):
        try: import gdspy
        except ImportError: self.skipTest('gdspy unavailable')
        from layout_tools import export_gds
        cells=layout(2,3)['cells']
        cells['leaf']['labels'][0].update(anchor=10,rotation_deg=90,magnification=2,x_reflection=True)
        output=self.root/'roundtrip.gds'
        mapping=export_gds(cells,'leaf',output,5e-10)
        label=gdspy.GdsLibrary(infile=str(output)).cells[mapping['leaf']].labels[0]
        self.assertEqual((label.anchor,label.rotation,label.magnification,label.x_reflection),(10,90,2,True))
        self.prepare()
        payload=self.reply_payload();payload['task']['export_gds_precision_m']=5e-10
        path=self.root/'export-reply.json';atomic(path,payload);workflow.reflect(self.run,payload,path)
        generated=builder.build(self.run,'exported')
        self.assertEqual(generated['outcome']['returncode'],0)
        self.assertTrue((Path(generated['directory'])/'layout.gds').is_file())
        self.assertIn('exported-layout.gds',generated['evidence'])

    def test_reviewed_experience_publication_and_cross_run_scope(self):
        self.prepare(); self.dispatch(); generated=self.complete()
        entry=self.record('experience','supported');entry['evidence']=[generated['candidate']]
        key=memory.commit(self.run,{'round':1,'entries':[entry],'disposition':'new'})['ids'][0]
        output=self.run/'exports/method'
        exported=experience.promote(self.run,[key],output)
        with self.assertRaisesRegex(ValueError,'immutable'): experience.promote(self.run,[key],output)
        config=self.root/'next.json'
        atomic(config,{'work_root':'next-runs','experience_root':str(self.run/'exports'),
                      'input_files':{'experience_root':['method/experience.json']},
                      'project':{'technology':{'process':'NEW','release':'r2','stack':'m2'}}})
        new=initialize(config,'next')
        state=read(new/'state.json'); retrieved=experience.select(new,state,module='adder')
        self.assertEqual(len(retrieved),1)
        self.assertEqual(retrieved[0]['status'],'uncertain')
        self.assertEqual(retrieved[0]['source_status'],'supported')
        self.assertEqual(experience.select(new,state,module='sram'),[])
        manifest=read(output/'experience.json')
        artifact=next(iter(manifest['artifacts'].values()))
        (output/artifact['object']).write_text('tampered')
        # Existing receiver is pinned; a new receiver must reject changed evidence.
        self.assertEqual(len(experience.select(new,state)),1)
        with self.assertRaisesRegex(ValueError,'Changed experience'): initialize(config,'bad')

    def test_uncertain_experience_cannot_be_promoted(self):
        self.prepare(); self.dispatch(); self.complete('failed')
        entry=self.record('experience','uncertain')
        key=memory.commit(self.run,{'round':1,'entries':[entry],'disposition':'new'})['ids'][0]
        with self.assertRaisesRegex(ValueError,'supported/refuted'):
            experience.promote(self.run,[key],self.run/'exports/uncertain')

    def test_config_relative_paths_and_input_keys(self):
        settings=load_config(self.config)
        self.assertEqual(settings.path('work_root'),self.root/'runs')
        with self.assertRaises(ValueError): settings.ensure_output(self.root/'outside')


if __name__=='__main__':
    unittest.main()
