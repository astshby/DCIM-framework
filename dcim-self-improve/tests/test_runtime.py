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

    def dispatch(self,decision='build'):
        req=workflow.request(self.run)
        payload={'request_id':req['id'],'request_digest':req['request_digest'],'author':'ai',
                 'comparison':'Synthetic test reply; not an AI evaluation', 'evidence':[self.search],
                 'reflection':self.record(),'decision':decision,
                 'task':{'route':self.route,'module':'adder','stage':'module','goal':'Synthetic composition',
                         'stop':'One geometry candidate','checks':['geometry'], 'execution':'geometry_only',
                         'max_candidates':2,'learning_ids':self.ids}}
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
                'summary':'Fixture checks', 'checks':{'geometry':verdict},'evidence':generated['evidence']}
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
        self.assertAlmostEqual(measured[2]-measured[0],selected['width_um'])
        self.assertAlmostEqual(measured[3]-measured[1],selected['height_um'])
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

    def test_human_plan_uses_same_geometry_validation_and_idempotency(self):
        self.prepare()
        req=workflow.request(self.run)
        payload={'request_id':req['id'],'request_digest':req['request_digest'],'author':'ai',
                 'comparison':'Fixture human proposal evaluation','evidence':[self.search],
                 'reflection':self.record(),'decision':'close',
                 'proposals':[{'id':'human-control','source':'human','mechanism':'Explicit order',
                     'expected':'Known geometry','minimal_test':'Check envelope','stop':'one trial',
                     'evidence':[self.search], 'plan_spec':{'search':self.search,
                     'order':[0,2,1],'cuts':[1,2],'rotations':[0,0,0]}}]}
        path=self.root/'human-reply.json'
        atomic(path,payload)
        workflow.reflect(self.run,payload,path)
        workflow.reflect(self.run,payload,path)
        route=read(self.run/'state.json')['routes']['human-control']
        self.assertTrue(route['plan']['feasible'])
        self.assertEqual(route['plan']['area_um2'],68)

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

    def test_config_relative_paths_and_input_keys(self):
        settings=load_config(self.config)
        self.assertEqual(settings.path('work_root'),self.root/'runs')
        with self.assertRaises(ValueError): settings.ensure_output(self.root/'outside')


if __name__=='__main__':
    unittest.main()
