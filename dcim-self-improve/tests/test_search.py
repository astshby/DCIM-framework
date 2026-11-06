"""Independent small placement invariants; no PDK, EDA, or claimed physical gains."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from search import search
from search.model import evaluate, rank
from search.operators import propose, OPERATORS
import random


def problem():
    return {'blocks':[{'id':i,'source':'synthetic','cell':'unit','width_um':2,'height_um':2,
                       'orientations':[0,90]} for i in ('fixed','moving')],
            'gap_um':1,'max_width_um':20,'max_height_um':10,'step_um':1,'grid_um':1,
            'movable_ids':['moving'],'nets':[['fixed','moving']]}


class SearchTests(unittest.TestCase):
    def test_all_strategies_start_exactly_at_baseline_and_improve_fixture(self):
        p=problem(); initial=((0,0,0),(12,0,0))
        for algorithm in ('anneal','local','lns','beam','adaptive'):
            with self.subTest(algorithm=algorithm):
                r=search(p,{'algorithm':algorithm,'seed':7,'evaluations':100,'steps':300,'seconds':5},initial)
                self.assertEqual(r['trials'][0]['state'],initial)
                self.assertLess(r['best']['score'],r['baseline_evaluation']['score'])
                self.assertTrue(r['improved'])
                self.assertLessEqual(r['evaluations'],100)
                self.assertLessEqual(r['attempts'],300)
                for trial in r['trials']:
                    self.assertEqual(trial['state'][0],initial[0])
                for selected in r['selected']:
                    a,b=selected['placements']
                    # Independent rectangle separation oracle.
                    self.assertTrue(a['x_um']+2+1<=b['x_um'] or b['x_um']+2+1<=a['x_um'] or
                                    a['y_um']+2+1<=b['y_um'] or b['y_um']+2+1<=a['y_um'])
                    self.assertLessEqual(max(x['x_um']+2 for x in (a,b)),20)
                    self.assertLessEqual(max(x['y_um']+2 for x in (a,b)),10)

    def test_frozen_baseline_and_budget_one_do_not_repack(self):
        p=problem(); p['movable_ids']=[]
        initial=((3,4,90),(9,4,0))
        for algorithm in ('anneal','local','lns','beam','adaptive'):
            r=search(p,{'algorithm':algorithm},initial)
            self.assertEqual(r['evaluations'],1)
            self.assertEqual(r['best']['state'],initial)
            self.assertFalse(r['improved'])
        p['movable_ids']=['moving']
        r=search(p,{'evaluations':1},initial)
        self.assertEqual(r['best']['state'],initial)
        self.assertEqual(r['stop'],'evaluation_budget')

    def test_hard_geometry_and_missing_measurements(self):
        p=problem()
        for key in (((0,0,0),(1,1,0)),((0,0,0),(19,0,0)),((0,0,0),(4.5,0,0))):
            self.assertFalse(evaluate(p,key)['feasible'])
        result=evaluate(p,((0,0,0),(3,0,0)))
        self.assertTrue(result['feasible'])
        self.assertNotIn('delay',result)
        self.assertEqual(result['routing'],'not_generated')

    def test_sa_retains_best_even_when_current_accepts_worse(self):
        p=problem(); p['movable_ids']=['fixed','moving']
        r=search(p,{'algorithm':'anneal','seed':11,'temperature':20,'cooling':1,
                    'evaluations':80,'steps':200},((0,0,0),(3,0,0)))
        trials={t['id']:t for t in r['trials']}
        self.assertTrue(any(t['accepted'] and rank(trials[t['candidate']])>rank(trials[t['parent']]) for t in r['trace']))
        self.assertLessEqual(rank(r['best']),rank(r['baseline_evaluation']))
        self.assertTrue(all(not trials[t['parent']]['feasible'] or trials[t['candidate']]['feasible']
                            for t in r['trace'] if t['accepted']))

    def test_cache_and_fixed_evaluation_count_reproducibility(self):
        p=problem(); initial=((0,0,0),(12,0,0))
        options={'algorithm':'anneal','seed':2,'evaluations':40,'steps':200}
        a=search(p,options,initial); b=search(p,options,initial)
        self.assertEqual(a['trials'],b['trials'])
        self.assertEqual(a['trace'],b['trace'])
        self.assertEqual(len({t['id'] for t in a['trials']}),a['evaluations'])
        self.assertGreater(a['cache_hits'],0)

    def test_operators_never_move_frozen_instances(self):
        p=problem(); state=((4,0,0),(12,0,0)); rng=random.Random(9)
        for op in OPERATORS:
            for _ in range(30):
                candidate,_,_=propose(p,state,rng,[op])
                self.assertEqual(candidate[0],state[0])

    def test_adaptive_nested_repair_counts_every_evaluation_and_keeps_best(self):
        p=problem(); initial=((0,0,0),(12,0,0))
        for limit in (1,2,7,80):
            r=search(p,{'algorithm':'adaptive','seed':7,'evaluations':limit,
                        'steps':100,'repair_candidates':16,'repair_beam':4},initial)
            self.assertLessEqual(r['evaluations'],limit)
            self.assertEqual(r['evaluations'],len(r['trials']))
            self.assertEqual(rank(r['best']),min(map(rank,r['trials'])))
            self.assertEqual(sum(r['adaptation']['pair_uses'].values()),
                             sum(t['candidate'] is not None for t in r['trace']))
            self.assertTrue(all(t['state'][0]==initial[0] for t in r['trials']))
            self.assertEqual(r['qualification'],'not_run')
        self.assertTrue(any(t['operation']=='adaptive_repair' for t in r['trials']))
        self.assertTrue(any(w!=1 for w in r['adaptation']['pair_weights'].values()))

    def test_adaptive_deterministic_budget_and_selection_rewards(self):
        from search.adaptive import Selection
        choice=Selection(.8)
        choice.update('edge','greedy',5)
        self.assertAlmostEqual(choice.weights['edge:greedy'],1.8)
        self.assertEqual(choice.weights['random:sampled'],1)
        p=problem(); initial=((0,0,0),(12,0,0))
        budget={'algorithm':'adaptive','seed':4,'evaluations':50,'steps':100,'seconds':10}
        a=search(p,budget,initial); b=search(p,budget,initial)
        self.assertEqual(a['trials'],b['trials'])
        self.assertEqual(a['trace'],b['trace'])
        self.assertEqual(a['adaptation'],b['adaptation'])
        self.assertTrue(a['cache_hits'])
        for options in ({'repair_candidates':0},{'repair_beam':5},{'adaptation_decay':1.1},
                        {'operators':['translate']}):
            with self.assertRaises(ValueError): search(p,dict(budget,**options),initial)

    def test_invalid_algorithms_parameters_and_orientation_fail(self):
        p=problem()
        for options in ({'algorithm':'router'},{'evaluations':True},{'seconds':float('nan')},
                        {'operators':['unsupported']},{'neighborhood':0},{'cooling':2},
                        {'algorithm':'lns','operators':['rotate']},{'steps':0}):
            with self.assertRaises(ValueError): search(p,options)
        with self.assertRaises(ValueError): evaluate(p,((0,0,180),(4,0,0)))


if __name__=='__main__':
    unittest.main()
