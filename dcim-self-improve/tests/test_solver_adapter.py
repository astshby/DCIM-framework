"""Meaningful upstream solver, exact-baseline and hard-constraint adapter checks."""
import copy
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import algorithm_portfolio as ap
import solver_adapter as sa
from test_search import problem as coarse_problem
from test_transistor_search import problem as device_problem

try:
    import scipy
    from scipy import optimize as so
except ImportError:
    scipy=None


@unittest.skipUnless(scipy,'Optional SciPy implementation not installed')
class SolverAdapterTests(unittest.TestCase):
    def numerical(self,algorithm,**change):
        budget=dict(algorithm=algorithm,evaluations=70,steps=200,seconds=5,seed=4)
        budget.update(change)
        def decoder(x):return {'position':round(x[0],8)}
        def evaluator(state):
            x=state['position'];return {'state':state,'score':(x-3)**2,
                'feasible':True,'violation':0}
        return sa.optimize([(0,5)],{'position':0},decoder,evaluator,budget,[0])

    def test_every_method_really_calls_its_upstream_function_and_improves(self):
        entries={'scipy_de':'differential_evolution','scipy_dual_annealing':'dual_annealing',
                 'scipy_basinhopping':'basinhopping','scipy_shgo':'shgo','scipy_powell':'minimize'}
        for key,entry in entries.items():
            with self.subTest(algorithm=key):
                real=getattr(so,entry)
                with patch.object(so,entry,wraps=real) as invoked:
                    result=self.numerical(key)
                self.assertTrue(invoked.called)
                self.assertTrue(result['implementation']['upstream_called'])
                self.assertEqual(result['implementation']['version'],scipy.__version__)
                self.assertEqual(result['trials'][0]['state'],{'position':0})
                self.assertEqual(result['baseline_evaluation']['score'],9)
                self.assertLess(result['best']['score'],9)
                self.assertLessEqual(result['evaluations'],70)
                self.assertLessEqual(result['attempts'],200)
                self.assertEqual(len(result['trials']),result['evaluations'])
                self.assertEqual(len({t['id'] for t in result['trials']}),result['evaluations'])

    def test_unavailable_tool_is_explicit_not_a_scipy_fallback(self):
        c=ap.catalog();self.assertEqual(len(c['options']),10)
        self.assertEqual(set(c['selectable']),set(ap.RUNNABLE))
        optional=[r for r in c['options'] if not r['adapter_implemented']]
        self.assertTrue(all(r['status']=='adapter_not_implemented' for r in optional))
        with self.assertRaises(ValueError):self.numerical('openroad_global')

    def test_all_modes_obey_single_evaluation_step_and_seed_bounds(self):
        for algorithm in ap.RUNNABLE:
            r=self.numerical(algorithm,evaluations=1)
            self.assertEqual(r['evaluations'],1);self.assertEqual(r['attempts'],0)
            self.assertFalse(r['implementation']['upstream_called'])
            r=self.numerical(algorithm,evaluations=2,steps=1)
            self.assertLessEqual(r['evaluations'],2);self.assertLessEqual(r['attempts'],1)
            a=self.numerical(algorithm,evaluations=24,steps=60)
            b=self.numerical(algorithm,evaluations=24,steps=60)
            self.assertEqual(a['trials'],b['trials']);self.assertEqual(a['trace'],b['trace'])

    def test_feasibility_dominates_arbitrary_large_objective(self):
        def evaluate(state):
            x=state[0];return {'score':1e50 if x<2.5 else -1e50,
                'feasible':x<2.5,'violation':0 if x<2.5 else 1}
        for algorithm in ap.RUNNABLE:
            r=sa.optimize([(0,5)],[1],lambda x:[round(x[0],5)],evaluate,
                          {'algorithm':algorithm,'evaluations':40,'steps':90,'seconds':5,'seed':2},[1])
            self.assertTrue(r['selected']);self.assertTrue(r['best']['feasible'])
            self.assertTrue(all(v['feasible'] for v in r['selected']))

    def test_coarse_codec_keeps_frozen_instances_grid_and_full_actual_baseline(self):
        p=coarse_problem();original=copy.deepcopy(p);initial=((3,4,90),(12,0,0))
        for algorithm in ap.RUNNABLE:
            r=sa.search(p,{'algorithm':algorithm,'evaluations':30,'steps':70,'seconds':5,'seed':7},initial)
            self.assertEqual(r['baseline_evaluation']['state'],initial)
            for trial in r['trials']:
                self.assertEqual(trial['state'][0],initial[0])
                for values in trial['state']:
                    self.assertEqual(values[0],round(values[0]));self.assertEqual(values[1],round(values[1]))
            for trial in r['selected']:
                a,b=trial['placements']
                self.assertTrue(a['x_um']+a['width_um']+1<=b['x_um'] or
                                b['x_um']+b['width_um']+1<=a['x_um'] or
                                a['y_um']+a['height_um']+1<=b['y_um'] or
                                b['y_um']+b['height_um']+1<=a['y_um'])
        self.assertEqual(p,original)

    def test_fine_codec_preserves_membership_endpoint_mapping_and_flip_permissions(self):
        p=device_problem();p['devices'][0]['sd_swap']=False;original=copy.deepcopy(p)
        import transistor_search as ts
        state=ts.initial_state(p);state['rows'][0]['order'].reverse();state['flips']=['NB']
        s=sa.codec(p,state)
        self.assertEqual(s['decoder'](s['initial_vector']),ts.evaluate(p,state)['state'])
        for algorithm in ('scipy_de','scipy_dual_annealing','scipy_basinhopping','scipy_powell'):
            r=sa.search(p,{'algorithm':algorithm,'evaluations':22,'steps':50,'seconds':5,'seed':3},state)
            self.assertEqual(r['baseline_evaluation']['state'],ts.evaluate(p,state)['state'])
            intended={d['id']:d['terminals'] for d in p['devices']}
            for trial in r['trials']:
                actual={d['id']:{t:q['net'] for t,q in d['terminals'].items()} for d in trial['placements']}
                self.assertEqual(actual,intended);self.assertNotIn(p['devices'][0]['id'],trial['state']['flips'])
        self.assertEqual(p,original)

    def test_all_frozen_states_skip_upstream_and_shgo_dimension_guard(self):
        p=coarse_problem();p['movable_ids']=[];state=((3,4,90),(12,0,0))
        for algorithm in ap.RUNNABLE:
            r=sa.search(p,{'algorithm':algorithm},state)
            self.assertEqual(r['stop'],'all_variables_frozen');self.assertEqual(r['evaluations'],1)
        with self.assertRaises(ValueError):
            sa.search(device_problem(),{'algorithm':'scipy_shgo'})

    def test_missing_nonfinite_invalid_and_unknown_contracts_are_rejected(self):
        for change in ({'evaluations':0},{'evaluations':True},{'seconds':float('nan')},
                       {'steps':0},{'seed':1.2},{'population':1},{'invisible_override':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.numerical('scipy_de',**change)
        for bounds in ([(0,float('inf'))],[(2,1)],[(0,0)]):
            with self.assertRaises(ValueError):
                sa.optimize(bounds,[0],lambda x:x,lambda x:{}, {'algorithm':'scipy_de'})
        with self.assertRaises(ValueError):
            sa.optimize([(0,1)],[0],lambda x:x,lambda x:{'feasible':True,'score':float('nan'),'violation':0},
                        {'algorithm':'scipy_de'},[0])


if __name__=='__main__':unittest.main()
