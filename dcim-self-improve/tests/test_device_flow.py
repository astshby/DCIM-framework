"""Integrated synthetic device rounds, independent audit and campaign admission."""
import copy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import builder, campaign, device_audit, device_flow, learn, memory, planner, workflow
from init_run import initialize
from runtime import atomic, artifact, read, transaction
from test_transistor_search import problem
from test_campaign import project
from test_runtime import layout


class DeviceFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.config=self.root/'config.json'
        self.project=project();self.camp=self.root/'campaign'
        campaign.create(self.camp,self.project,'abstract')
        atomic(self.config,{'work_root':'runs','project':self.project,'input_files':{}})
        self.run=initialize(self.config,'test')
        self.p=problem();self.p['technology']=self.project['technology']
        self.checks=['device_identity','terminal_mapping','abstract_geometry']
        with transaction(self.run) as (root,state):
            for key,payload in device_flow.source_payloads(self.p).items():
                path=self.root/(key+'.json');atomic(path,payload)
                artifact(root,state,self.p['sources'][key],path,'evidence')
        source=self.root/'compiler.json';atomic(source,layout(8,5))
        self.ref=learn.learn(self.run,'compiler',source,'leaf',dict(module='sram',source_run='synthetic',**self.project['technology']))['id']
        self.route=None;self.search=None

    def search_now(self):
        state=read(self.run/'state.json')
        result=planner.plan(self.run,self.p if state['round']==0 else None,
                            {'algorithm':'anneal','seed':7,'evaluations':50,'steps':180,'seconds':5})
        self.search=result['artifact'];self.route=result['routes'][0]['id']
        return result

    def dispatch(self,close=False):
        req=workflow.request(self.run);n=read(self.run/'state.json')['round']
        record={'type':'reflection','stage':'module','module':'sram','route':self.route,
            'scope':'general','status':'uncertain','condition':'Synthetic device plan only',
            'operation':'Compare row ordering and declared terminal anchors','observation':'No physical evidence',
            'next_test':'Independent terminal and geometry checks','evidence':[self.search]}
        proposal={'id':'idea'+str(n),'source':'ai','mechanism':'Synthetic distinct observation '+str(n),
            'difference':'Fixture tests contract, not AI novelty','expected':'Preserve named terminals',
            'minimal_test':'Inspect generated device endpoints','stop':'Bounded fixture','evidence':[self.search]}
        reply={'request_id':req['id'],'request_digest':req['request_digest'],'author':'ai',
            'comparison':'Scripted integration fixture, no AI-science claim','evidence':[self.search],
            'reflection':record,'decision':'close' if close else 'build','self_proposal':proposal['id'],'proposals':[proposal]}
        if not close:
            reply['task']={'route':self.route,'module':'sram','stage':'module','goal':'Synthetic fine-grained placement',
                'stop':'One candidate','checks':self.checks,'execution':'transistor_proxy','max_candidates':2,
                'learning_ids':[self.ref],'learning_goals':['devices'],
                'campaign_binding':campaign.binding(self.camp,'sram')}
        if n==0:
            reply['learning_updates']=[{'id':'devices','module':'sram','stage':'module','scope':'general',
                'condition':'Compiler observation and explicit synthetic source netlist',
                'operation':'Order devices under declared sharing rules','observation':'Hypothesis only',
                'next_test':'Independently check endpoints and declared geometry',
                'evidence':[self.ref],'checks':self.checks}]
        path=self.root/('reply%d.json'%n);atomic(path,reply);workflow.reflect(self.run,reply,path)
        return reply

    def build_result(self):
        n=read(self.run/'state.json')['round'];out=builder.build(self.run,'c'+str(n))
        self.assertEqual(out['outcome']['returncode'],0,out)
        d=Path(out['directory'])
        report=device_audit.audit(read(d/'input.json'),read(d/'transistor-layout.json'),read(d/'source-netlist.json'),read(d/'source-rules.json'))
        self.assertEqual(report['verdict'],'passed',report)
        self.result={'round':n,'task_id':'task-'+str(n),'outcome':'passed','summary':'Synthetic abstract output','evidence':out['evidence']}
        path=self.root/'result.json';atomic(path,self.result);workflow.result(self.run,self.result,path)
        return out,report

    def review_memory(self,out,report):
        n=read(self.run/'state.json')['round']
        review={'round':n,'result_id':'result-'+str(n),'verdict':report['verdict'],'scope':'transistor_proxy',
            'summary':'Independent abstract endpoint and interval audit','checks':report['checks'],'evidence':out['evidence'],
            'learning_checks':{'devices':{'conclusion':'supported','observation':'Only synthetic checks passed','evidence':[out['candidate']]}}}
        path=self.root/'review.json';atomic(path,review);workflow.review(self.run,review,path)
        with self.assertRaises(ValueError):workflow.request(self.run)
        memory.commit(self.run,{'round':n,'disposition':'no_new','entries':[]})

    def test_two_rounds_previous_output_closure_and_campaign(self):
        self.search_now();self.dispatch();out,report=self.build_result()
        with self.assertRaises(ValueError):planner.plan(self.run)
        with self.assertRaises(ValueError):workflow.request(self.run)
        with self.assertRaises(ValueError):campaign.accept(self.camp,'sram',self.run,'c1')
        self.review_memory(out,report);result=self.search_now()
        self.assertEqual(result['baseline']['candidate'],'c1')
        snapshot=read(Path(out['directory'])/'placement_state.json')
        st=read(self.run/'state.json');search=read(self.run/st['artifacts'][result['artifact']]['object'])
        self.assertEqual(search['baseline_evaluation']['state'],snapshot['state'])
        self.dispatch();out,report=self.build_result();self.review_memory(out,report)
        self.dispatch(close=True)
        self.assertEqual(read(self.run/'state.json')['phase'],'closed')
        accepted=campaign.accept(self.camp,'sram',self.run,'c2')
        self.assertEqual(accepted['status']['stages']['adder']['status'],'ready')
        self.assertFalse(accepted['status']['complete'])

    def test_source_mismatch_rejected_and_no_state_transition(self):
        changed=copy.deepcopy(self.p);changed['devices'][0]['terminals']['g']='silently_changed'
        with self.assertRaises(ValueError):planner.plan(self.run,changed,{'evaluations':2})
        self.assertEqual(read(self.run/'state.json')['phase'],'learning')

    def test_replay_survives_copy_and_source_run_removal(self):
        self.search_now();self.dispatch();out,report=self.build_result();self.review_memory(out,report)
        new=self.root/'relocated';shutil.copytree(self.run,new);shutil.rmtree(self.run);self.run=new
        self.assertEqual(self.search_now()['baseline']['candidate'],'c1')

    def test_audit_detects_changed_terminal_missing_device_and_overlap(self):
        self.search_now();self.dispatch();out,_=self.build_result();d=Path(out['directory'])
        original=read(d/'transistor-layout.json')
        for kind in ('terminal','missing','coordinate','seam','source','ports','rows','obstacles','reserved_access','hpwl','breaks','score','claim','identity'):
            data=copy.deepcopy(original);net=read(d/'source-netlist.json')
            if kind=='terminal':data['placements'][0]['terminals']['g']['net']='wrong'
            if kind=='missing':data['placements'].pop()
            if kind=='coordinate':data['placements'][0]['x_um']+=1
            if kind=='seam':data['seams'][0]['shared_candidate']=not data['seams'][0]['shared_candidate']
            if kind=='source':net['devices'][0]['terminals']['b']='fake-body'
            if kind=='ports':data['ports'][0]['net']='wrong'
            if kind=='rows':data['rows'][0]['body_net']='wrong'
            if kind in ('obstacles','reserved_access'):data[kind]=[{'id':'invented'}]
            if kind=='hpwl':data['metrics']['hpwl_proxy_um']=0
            if kind=='breaks':data['metrics']['diffusion_breaks']+=1
            if kind=='score':data['metrics']['score']=0
            if kind=='claim':data['metrics']['body_supply']='physically_verified'
            if kind=='identity':data['problem_identity']='wrong'
            self.assertEqual(device_audit.audit(read(d/'input.json'),data,net,read(d/'source-rules.json'))['verdict'],'failed',kind)

    def test_physical_pass_cannot_be_smuggled_into_proxy_review(self):
        self.search_now();self.dispatch();out,report=self.build_result();report['checks']['drc']='passed'
        with self.assertRaises(ValueError):self.review_memory(out,report)
        self.assertEqual(read(self.run/'state.json')['phase'],'awaiting_analyst')

    def test_changed_device_population_cannot_reset_next_round(self):
        self.search_now();self.dispatch();out,report=self.build_result();self.review_memory(out,report)
        changed=copy.deepcopy(self.p);changed['devices'][0]['model']='new-model'
        with self.assertRaises(ValueError):planner.plan(self.run,changed,{'evaluations':2})


if __name__=='__main__':unittest.main()
