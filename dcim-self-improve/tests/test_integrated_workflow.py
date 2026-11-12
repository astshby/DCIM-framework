"""Focused normal-entry regressions. Synthetic inputs, no AI or EDA execution."""
import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import unittest
import test_runtime as fixtures
from test_runtime import layout
from unittest.mock import patch
from runtime import atomic, read, identity
import builder
import learn
import planner
import workflow
import architecture
from test_transistor_search import problem as device_problem


class IntegratedTests(unittest.TestCase):
    setUp = fixtures.RuntimeTests.setUp
    prepare = fixtures.RuntimeTests.prepare
    record = fixtures.RuntimeTests.record
    learning_goal = fixtures.RuntimeTests.learning_goal
    learning_check = fixtures.RuntimeTests.learning_check

    def architecture(self):
        state = read(self.run/'state.json')
        plan = state['routes'][self.route]['plan']
        h = plan['height_um']
        return {'schema':'architecture-task-v1','purpose':'screen',
            'parent':{'width_um':plan['width_um'],'height_um':h},'sources':self.ids,
            'order':[p['id'] for p in sorted(plan['placements'], key=lambda p:p['x_um'])],
            'transforms':{p['id']:{'rotation_deg':p['rotation_deg']} for p in plan['placements']},
            'functional_rows':[{'id':'row-'+p['id'],'origin_um':p['y_um'],
                'height_um':p['height_um'],'phase':'declared_reference_phase',
                'members':{p['id']:0}} for p in plan['placements']],
            'implant_bands':[{'kind':'NP','y0_um':0,'y1_um':h/2,'owner':'parent'},
                {'kind':'PP','y0_um':h/2,'y1_um':h,'owner':'parent'}],
            'ownership':{k:'parent' for k in ('tap','body','termination','interfaces')},
            'required_measurements':{'functional_rows':'coordinate_measurement',
                'implant_continuity':'mask_extraction','body_power':'connectivity_extraction',
                'interface_access':'coordinate_measurement'},
            'unresolved':sorted(architecture.CHECKS)}

    def planning(self, close=False):
        task={'route':self.route,'module':'adder','stage':'module','goal':'Synthetic bounded composition',
            'stop':'One candidate','checks':['geometry']+sorted(architecture.CHECKS),'execution':'geometry_only',
            'max_candidates':2,'learning_ids':self.ids,'learning_goals':['goal-layout'],
            'architecture':self.architecture()}
        return {'comparison':'Actual fixture decision supplied by test, no generated AI response',
            'evidence':[self.search], 'reflection':self.record(),'decision':'close' if close else 'build',
            'task':task}

    def initial(self, cli=False):
        self.prepare()
        payload={'author':'ai','round':0,'planning':self.planning()}
        payload['planning']['learning_updates']=[self.learning_goal()]
        path=self.root/'initial.json';atomic(path,payload)
        if cli:
            result=subprocess.run([sys.executable,str(self.run/'scripts/workflow.py'),'--run',str(self.run),
                'initial-plan','--input',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertEqual(result.returncode,0,result.stderr.decode())
        else:
            workflow.integrated_decision(self.run,payload,path,initial=True)
        return payload,path

    def decision(self):
        generated=builder.build(self.run,'actual1')
        payload={'round':1,'task_id':'task-1','outcome':'incomplete','summary':'Only geometry generated',
                 'evidence':generated['evidence']}
        path=self.root/'result.json';atomic(path,payload);workflow.result(self.run,payload,path)
        methods=self.architecture()['required_measurements']
        review={'round':1,'result_id':'result-1','verdict':'incomplete','scope':'architecture_screen',
            'summary':'Geometry available, extraction unavailable',
            'checks':dict(geometry='passed',**{k:'incomplete' for k in methods}),
            'evidence':generated['evidence'], 'learning_checks':self.learning_check([generated['candidate']]),
            'architecture_checks':{k:{'status':'incomplete','method':v,'evidence':[generated['candidate']],
                    'observation':'No physical extraction in synthetic fixture'} for k,v in methods.items()}}
        return {'author':'ai','round':1,'review':review,'memory':{'round':1,'disposition':'no_new','entries':[]},
                'planning':self.planning(close=True)}

    def test_cli_initial_and_atomic_review_close_idempotency(self):
        self.initial(cli=True)
        payload=self.decision();path=self.root/'decision.json';atomic(path,payload)
        command=[sys.executable,str(self.run/'scripts/workflow.py'),'--run',str(self.run),
                 'reviewed-decision','--input',str(path)]
        for unused in range(2):
            result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertEqual(result.returncode,0,result.stderr.decode())
        state=read(self.run/'state.json')
        self.assertEqual(state['phase'],'closed')
        self.assertEqual(len([m for m in state['memory'] if m['type']=='reflection']),2)
        self.assertEqual(len(state['reviews']),1)
        changed=copy.deepcopy(payload);changed['planning']['comparison']='conflict';atomic(path,changed)
        with self.assertRaises(ValueError):workflow.integrated_decision(self.run,changed,path)

    def test_failed_combined_decision_keeps_review_memory_uncommitted(self):
        self.initial();payload=self.decision();path=self.root/'decision.json'
        before=identity(read(self.run/'state.json'))
        broken=copy.deepcopy(payload);broken['planning']['reflection']['observation']='';atomic(path,broken)
        with self.assertRaises(ValueError):workflow.integrated_decision(self.run,broken,path)
        self.assertEqual(identity(read(self.run/'state.json')),before)
        atomic(path,payload)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(lambda unused:workflow.integrated_decision(self.run,payload,path),range(2)))
        self.assertEqual(read(self.run/'state.json')['phase'],'closed')
        self.assertEqual(len(read(self.run/'state.json')['reviews']),1)

    def test_repair_reuses_mechanism_with_immediate_actual_baseline(self):
        self.initial();payload=self.decision();payload['planning']=self.planning()
        payload['planning']['task']['route']='$search:0'
        payload['planning']['reflection']['route']='$search:0'
        payload['search']={'budget':{'algorithm':'local','evaluations':1,'steps':1}}
        path=self.root/'next.json';atomic(path,payload)
        workflow.integrated_decision(self.run,payload,path)
        state=read(self.run/'state.json');selected=state['routes'][state['task']['route']]
        self.assertEqual(state['round'],2)
        self.assertEqual(selected['baseline']['candidate'],'actual1')
        self.assertEqual(selected['baseline']['review'],'review-1')
        self.assertEqual(builder.build(self.run,'actual2')['outcome']['returncode'],0)

    def test_profile_rejects_normal_fine_entry_and_is_pinned(self):
        state=read(self.run/'state.json')
        if state['capabilities']['fine']:
            self.skipTest('coarse-profile rejection only')
        self.assertEqual(state['capabilities']['profile'],'coarse')
        import campaign
        with self.assertRaisesRegex(ValueError,'coarse-only'):
            campaign.create(self.root/'fine-campaign',state['project'],'abstract')
        with self.assertRaisesRegex(ValueError,'coarse-only'):
            planner.plan(self.run,device_problem(),{'evaluations':1})

    def test_bad_architecture_rejected_before_task_admission(self):
        self.prepare();planning=self.planning();planning['learning_updates']=[self.learning_goal()]
        payload={'author':'ai','round':0,'planning':planning};path=self.root/'bad.json'
        for change in (lambda x:x['parent'].update(height_um=0.1),
                       lambda x:x['transforms'][x['order'][0]].update(rotation_deg=123),
                       lambda x:x['implant_bands'][1].update(y0_um=0.01),
                       lambda x:x.update(purpose='qualification'),
                       lambda x:x.update(unchecked_pass=True)):
            bad=copy.deepcopy(payload);change(bad['planning']['task']['architecture']);atomic(path,bad)
            with self.assertRaises(ValueError):workflow.integrated_decision(self.run,bad,path,initial=True)
            self.assertEqual(read(self.run/'state.json')['phase'],'learning')

    def test_reference_roles_exact_bytes_and_cross_node_purpose(self):
        path=self.root/'native.json';atomic(path,layout(2,3))
        circuit=self.root/'intent.cdl';circuit.write_text('.SUBCKT leaf A VSS\n.ENDS leaf\n')
        context={'module':'adder','process':'OTHER','release':'r1','stack':'m1','source_run':'fixture',
                 'purpose':'organization_only','observation':'Declared source organization'}
        reference=learn.learn(self.run,'native_device',path,'leaf',context,{'circuit':str(circuit)})
        self.assertEqual(reference['kind'],'native_device')
        self.assertIn('circuit',reference['sources'])
        with self.assertRaisesRegex(ValueError,'Organization-only'):
            planner.plan(self.run,{'blocks':[{'id':'x','source':reference['id'],'cell':'leaf',
                'width_um':2,'height_um':3,'orientations':[0]}],'gap_um':0,
                'max_width_um':10,'max_height_um':10})
        context.update(process='TEST',purpose='circuit_intent')
        item=learn.learn(self.run,'circuit',None,'leaf',context,{'circuit':str(circuit)})
        first=item['id'];circuit.write_text('.SUBCKT leaf A VSS\n* revised bytes\n.ENDS leaf\n')
        self.assertNotEqual(first,learn.learn(self.run,'circuit',None,'leaf',context,{'circuit':str(circuit)})['id'])

    def test_reference_drift_during_inspection_is_rejected(self):
        path=self.root/'ref.json';atomic(path,layout(2,3))
        original=learn.inspect_layout
        def changing_layout(source, top):
            observations=original(source, top)
            atomic(source,layout(5,6))
            return observations
        context={'module':'adder','process':'TEST','release':'r1','stack':'m1','source_run':'fixture'}
        with patch('learn.inspect_layout',side_effect=changing_layout):
            with self.assertRaisesRegex(ValueError,'changed during inspection'):
                learn.learn(self.run,'digital_flow',path,'leaf',context)
        self.assertEqual(read(self.run/'state.json')['learning'],[])


if __name__=='__main__':unittest.main()
