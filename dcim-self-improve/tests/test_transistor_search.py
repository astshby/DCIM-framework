"""Synthetic transistor-order checks; independent named-terminal and seam oracles."""
import copy
import itertools
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import transistor_search as ts


def problem():
    devices = []
    for prefix, kind, body in [('P', 'pmos', 'VDD'), ('N', 'nmos', 'VSS')]:
        for suffix, gate, source, drain in [('A', 'a', body, prefix+'x'),
                                          ('B', 'b', prefix+'y', 'out'),
                                          ('C', 'c', prefix+'x', prefix+'y')]:
            devices.append({'id': prefix+suffix, 'row': prefix, 'kind': kind, 'model': 'synthetic-'+kind,
                            'width_um': 2, 'height_um': 2, 'terminals': {'g': gate, 's': source,
                            'd': drain, 'b': body}, 'sd_swap': True, 'share_group': kind+'-h2'})
    return {'schema': ts.SCHEMA, 'technology': {'process': 'SYNTHETIC', 'release': 'r1', 'stack': 'test'},
            'sources': {'netlist': 'synthetic-circuit', 'rules': 'synthetic-rules'},
            'rows': [{'id': 'P', 'kind': 'pmos', 'y_um': 3, 'height_um': 2, 'body_net': 'VDD'},
                     {'id': 'N', 'kind': 'nmos', 'y_um': 0, 'height_um': 2, 'body_net': 'VSS'}],
            'devices': devices, 'rules': {'diffusion_gap_um': 1, 'allow_diffusion_sharing': True, 'grid_um': 1},
            'ports': [{'name': 'Q', 'net': 'out', 'x_um': 0, 'y_um': 0}],
            'obstacles': [], 'reserved_access': [],
            'constraints': {'max_width_um': 20, 'max_height_um': 10, 'width_strict': True, 'height_strict': True},
            'objective': {'wire_weight': 0.05, 'break_weight': 1}}


class TransistorTests(unittest.TestCase):
    def test_exact_chain_break_width_and_terminal_hpwl(self):
        p = problem(); state = ts.initial_state(p)
        baseline = ts.evaluate(p, state)
        self.assertEqual(baseline['diffusion_breaks'], 4)
        self.assertEqual(baseline['width_um'], 8)
        self.assertEqual(baseline['height_um'], 5)
        for row in state['rows']:
            prefix = row['id']; row['order'] = [prefix+'A', prefix+'C', prefix+'B']
        candidate = ts.evaluate(p, state)
        self.assertEqual(candidate['diffusion_breaks'], 0)
        self.assertEqual(candidate['width_um'], 6)
        self.assertEqual(candidate['area_um2'], 30)
        points = {}
        for d in candidate['placements']:
            for t in d['terminals'].values():
                points.setdefault(t['net'], []).append((t['x_um'], t['y_um']))
        points['out'].append((0, 0))
        expected = sum(max(x for x, y in values)-min(x for x, y in values)+
                       max(y for x, y in values)-min(y for x, y in values)
                       for values in points.values())
        self.assertEqual(candidate['hpwl_proxy_um'], expected)
        self.assertEqual(candidate['routing'], 'not_generated')
        self.assertEqual(candidate['terminal_geometry'], 'nominal_anchors_not_mask_pins')
        self.assertNotIn('delay', candidate)

    def test_no_netlist_or_transistor_membership_changes(self):
        p = problem(); original = copy.deepcopy(p)
        r = ts.search(p, {'seed': 7, 'evaluations': 60, 'steps': 150})
        intended = {d['id']: d['terminals'] for d in p['devices']}
        signature = ts.netlist_signature(p)
        for trial in r['trials']:
            actual = {d['id']: {pin: record['net'] for pin, record in d['terminals'].items()}
                      for d in trial['placements']}
            self.assertEqual(actual, intended)
            self.assertEqual(trial['netlist_signature'], signature)
            for row in trial['state']['rows']:
                self.assertEqual(set(row['order']), {d['id'] for d in p['devices'] if d['row'] == row['id']})
        self.assertEqual(p, original)

    def test_both_strategies_baseline_budget_determinism_and_improvement(self):
        for algorithm in ('anneal', 'local'):
            budget = {'algorithm': algorithm, 'seed': 7, 'evaluations': 80, 'steps': 400, 'seconds': 10}
            a = ts.search(problem(), budget); b = ts.search(problem(), budget)
            self.assertEqual(a['trials'], b['trials']); self.assertEqual(a['trace'], b['trace'])
            self.assertEqual(a['trials'][0]['state'], ts.initial_state(problem()))
            self.assertLessEqual(a['evaluations'], 80); self.assertLessEqual(a['attempts'], 400)
            self.assertEqual(len({v['id'] for v in a['trials']}), a['evaluations'])
            self.assertLess(a['best']['score'], a['baseline_evaluation']['score'])
            self.assertTrue(a['improved']); self.assertEqual(a['qualification'], 'not_run')
            self.assertEqual(a['best']['score'], min(t['score'] for t in a['trials'] if t['feasible']))
            self.assertTrue(all(t['feasible'] for t in a['selected']))
        for count in (1, 2, 5):
            a = ts.search(problem(), {'evaluations': count, 'steps': 20})
            self.assertLessEqual(a['evaluations'], count)
            self.assertEqual(a['stop'], 'evaluation_budget')

    def test_state_does_not_repack_initial_order_or_flips(self):
        p = problem(); state = ts.initial_state(p)
        state['rows'][0]['order'].reverse(); state['flips'] = ['PA', 'NB']
        saved = copy.deepcopy(state)
        r = ts.search(p, {'evaluations': 1}, state)
        self.assertEqual(r['baseline_evaluation']['state'], dict(saved, flips=sorted(saved['flips'])))
        self.assertEqual(state, saved)
        layout = ts.build_abstract(p, saved)
        self.assertEqual(layout['metrics']['netlist_signature'], ts.netlist_signature(p))
        self.assertEqual(layout['schema'], ts.LAYOUT_SCHEMA)
        self.assertEqual(layout, ts.build_abstract(p, saved))

    def test_shared_edges_only_for_explicit_compatible_terminal_and_technology(self):
        p = problem(); state = ts.initial_state(p)
        for row in state['rows']:
            prefix = row['id']; row['order'] = [prefix+'A', prefix+'C', prefix+'B']
        self.assertEqual(ts.evaluate(p, state)['diffusion_breaks'], 0)
        for key, value in [('model', 'different'), ('share_group', None), ('height_um', 1)]:
            altered = copy.deepcopy(p); altered['devices'][2][key] = value
            c = ts.evaluate(altered, state)
            self.assertEqual(c['diffusion_breaks'], 2)
        altered = copy.deepcopy(p); altered['rules']['allow_diffusion_sharing'] = False
        self.assertEqual(ts.evaluate(altered, state)['diffusion_breaks'], 4)
        altered = copy.deepcopy(p); altered['devices'][2]['terminals']['s'] = 'other'
        self.assertEqual(ts.evaluate(altered, state)['diffusion_breaks'], 1)
        for seam in ts.evaluate(p, state)['seams']:
            self.assertEqual(seam['facing_nets'][0], seam['facing_nets'][1])
            self.assertEqual(seam['gap_um'], 0)
            self.assertEqual(seam['qualification'], 'abstract_predicate_only')

    def test_named_terminal_orientation_and_flip_permissions(self):
        p = problem(); state = ts.initial_state(p)
        state['flips'] = ['PA']
        actual = next(d for d in ts.evaluate(p, state)['placements'] if d['id'] == 'PA')
        self.assertEqual(actual['terminals']['s']['x_um'], actual['x_um']+actual['width_um'])
        self.assertEqual(actual['terminals']['d']['x_um'], actual['x_um'])
        self.assertEqual(actual['terminals']['s']['net'], 'VDD')
        p['devices'][0]['sd_swap'] = False
        with self.assertRaises(ValueError): ts.evaluate(p, state)
        for d in p['devices']:
            d['sd_swap'] = False
        r = ts.search(p, {'operators': ['sd_flip'], 'steps': 10})
        self.assertEqual(r['evaluations'], 1)
        self.assertTrue(all(t['state']['flips'] == [] for t in r['trials']))

    def test_hard_bounds_are_not_objective_penalties_and_strict_is_exact(self):
        p = problem(); state = ts.initial_state(p)
        p['constraints']['max_width_um'] = 8
        self.assertIn('width_bound', ts.evaluate(p, state)['violations'])
        p['constraints']['width_strict'] = False
        self.assertTrue(ts.evaluate(p, state)['feasible'])
        p['constraints']['max_height_um'] = 5
        self.assertIn('height_bound', ts.evaluate(p, state)['violations'])
        p['constraints']['height_strict'] = False
        self.assertTrue(ts.evaluate(p, state)['feasible'])
        p['constraints']['max_width_um'] = 7
        p['objective']['wire_weight'] = 0; p['objective']['break_weight'] = 0
        self.assertFalse(ts.evaluate(p, state)['feasible'])
        r = ts.search(p, {'seed': 3, 'evaluations': 80, 'steps': 200})
        trials = {t['id']: t for t in r['trials']}
        self.assertTrue(all(not trials[t['parent']]['feasible'] or trials[t['candidate']]['feasible']
                            for t in r['trace'] if t['accepted']))

    def test_obstacles_reserved_access_and_resource_envelopes(self):
        p = problem(); state = ts.initial_state(p)
        region = {'id': 'keepout', 'x_um': 0, 'y_um': 0, 'width_um': 1, 'height_um': 1}
        p['obstacles'] = [region]
        self.assertIn('obstacles:NA:keepout', ts.evaluate(p, state)['violations'])
        p['obstacles'] = []
        p['reserved_access'] = [dict(region, net='out')]
        self.assertIn('reserved_access:NA:keepout', ts.evaluate(p, state)['violations'])
        p['reserved_access'][0]['x_um'] = 8
        self.assertTrue(ts.evaluate(p, state)['feasible'])
        self.assertEqual(ts.evaluate(p, state)['width_um'], 9)
        p['reserved_access'][0]['x_um'] = 20
        self.assertFalse(ts.evaluate(p, state)['feasible'])

    def test_every_operator_preserves_device_rows_and_supports_complete_trace(self):
        import random
        p = problem(); state = ts.initial_state(p)
        for op in ts.OPERATORS:
            rng = random.Random(4)
            for _ in range(20):
                candidate, name, _ = ts._proposal(state, p, rng, [op])
                self.assertEqual(name, op)
                trial = ts.evaluate(p, candidate)
                self.assertEqual(trial['netlist_signature'], ts.netlist_signature(p))
            r = ts.search(p, {'operators': [op], 'steps': 30, 'evaluations': 20})
            self.assertTrue(all(t['operation'] == op for t in r['trace']))
            self.assertEqual(r['attempts'], len(r['trace']))
            self.assertEqual(r['evaluations'], len(r['trials']))

    def test_complete_small_search_space_oracle_bounds_the_heuristic(self):
        p = problem()
        # Exhaustively enumerate the 36 no-flip row orders as a separate comparator.
        state = ts.initial_state(p)
        scores = []
        for a, b in itertools.product(itertools.permutations(state['rows'][0]['order']),
                                      itertools.permutations(state['rows'][1]['order'])):
            trial = {'rows': [{'id': 'P', 'order': list(a)}, {'id': 'N', 'order': list(b)}], 'flips': []}
            scores.append(ts.evaluate(p, trial)['score'])
        r = ts.search(p, {'seed': 7, 'evaluations': 150, 'steps': 500,
                         'operators': ['adjacent_swap', 'reinsert', 'pair_swap']})
        self.assertGreaterEqual(r['best']['score']+1e-12, min(scores))
        self.assertAlmostEqual(r['best']['score'], min(scores))

    def test_state_and_schema_errors_reject_unknown_or_missing_semantics(self):
        p = problem()
        for missing in p:
            bad = copy.deepcopy(p); del bad[missing]
            with self.assertRaises(ValueError): ts.validate_problem(bad)
        for field in ('nets', 'scale', 'ignore_drc'):
            bad = copy.deepcopy(p); bad[field] = []
            with self.assertRaises(ValueError): ts.validate_problem(bad)
        for bad in [dict(rows=[], flips=[]), dict(rows=ts.initial_state(p)['rows'], flips=['absent']),
                    dict(ts.initial_state(p), flips=['PA', 'PA'])]:
            with self.assertRaises(ValueError): ts.evaluate(p, bad)
        bad = ts.initial_state(p); bad['rows'][0]['order'][0] = 'NA'
        with self.assertRaises(ValueError): ts.evaluate(p, bad)
        bad = ts.initial_state(p); bad['rows'][0]['order'] = ['PA', 'PA', 'PC']
        with self.assertRaises(ValueError): ts.evaluate(p, bad)

    def test_physical_contract_errors_reject_nonfinite_grid_row_body_and_polarity(self):
        p = problem()
        changes = [lambda x: x['devices'][0].update(kind='nmos'),
                   lambda x: x['devices'][0]['terminals'].update(b='wrong'),
                   lambda x: x['devices'][0].update(height_um=3),
                   lambda x: x['devices'][0].update(width_um=2.5),
                   lambda x: x['devices'][0].update(width_um=1e-12),
                   lambda x: x['rows'][0].update(y_um=1),
                   lambda x: x['rules'].update(grid_um=0),
                   lambda x: x['rules'].update(diffusion_gap_um=float('nan')),
                   lambda x: x['objective'].update(wire_weight=float('inf')),
                   lambda x: x['ports'][0].update(net='unknown'),
                   lambda x: x['devices'][0].update(sd_swap='yes')]
        for change in changes:
            bad = copy.deepcopy(p); change(bad)
            with self.assertRaises(ValueError): ts.validate_problem(bad)
        bad = copy.deepcopy(p); bad['devices'][0]['terminals']['extra'] = 'VDD'
        with self.assertRaises(ValueError): ts.validate_problem(bad)

    def test_invalid_search_settings(self):
        for change in ({'algorithm': 'router'}, {'evaluations': True}, {'evaluations': 10001},
                       {'seconds': float('nan')}, {'seconds': 61}, {'steps': 0}, {'seed': False},
                       {'temperature': 0}, {'cooling': 2}, {'operators': ['rotate']},
                       {'operators': []}, {'operators': ['sd_flip', 'sd_flip']}, {'eda': True}):
            with self.assertRaises(ValueError): ts.search(problem(), change)


if __name__ == '__main__':
    unittest.main()
