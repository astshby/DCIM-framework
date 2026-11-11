"""Synthetic identity/coverage checks through the physical Builder entry point."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from init_run import initialize
import physical_builder as pb
from runtime import artifact, atomic, read, transaction

DRIVER = """
import hashlib, json, sys
from pathlib import Path

action, stage, out, plan, admission, gds, cdl, deffile = sys.argv[1:]
out = Path(out)
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
if action == 'prepare':
    admitted = json.loads(Path(admission).read_text())
    assert digest(plan) == admitted['plan_sha256']
    outputs = {}
    for label, path in zip(('layout.gds', 'source.cdl', 'routed.def'), (gds, cdl, deffile)):
        assert digest(path) == admitted['baseline'][label]['sha256']
        outputs[label] = out / label
        outputs[label].write_bytes(Path(path).read_bytes() + b' + synthetic construction')
    (out / 'witness.json').write_text(json.dumps({
        'schema':'physical-action-witness-v1', 'plan_sha256': digest(plan),
        'admission_sha256': digest(admission),
        'outputs': {label:digest(path) for label,path in outputs.items()}}))
    print(json.dumps({'state':'prepared'}))
else:
    (out / ('called-' + action)).touch()
    print(json.dumps({'state':'submitted' if action=='submit' else 'terminal', 'stage':stage, 'job_id':123}))
"""


class ActionGuardTests(unittest.TestCase):
    def fixture(self, mutation=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        driver = base / 'driver.py'
        driver.write_text(DRIVER)
        cfg = base / 'config.json'
        atomic(cfg, {'work_root': 'runs', 'input_files': {}})
        run = initialize(cfg, 'fixture')
        full_checks = ['full_periphery', 'module_connectivity', 'drc', 'source_lvs', 'erc', 'behavioral']
        with transaction(run) as (root, state):
            def bind(key, path):
                item = artifact(root, state, key, path, 'evidence')
                return {'artifact': key, 'sha256': item['sha256']}
            def json_artifact(key, value):
                path = base / (key + '.json')
                atomic(path, value)
                return bind(key, path)
            baseline = {}
            for label in ('layout.gds', 'source.cdl', 'routed.def'):
                path = base / label
                path.write_text('synthetic parent ' + label)
                baseline[label] = bind('parent-' + label, path)
            old = base / 'old.def'
            old.write_text('different, stale parent')
            old_def = bind('old.def', old)
            proposal = {'id': 'A', 'operation': 'select_endpoint', 'object': {'net': 'data'},
                        'parameters': {'track': 7, 'point': [11, 17]}}
            policy = {'schema': 'physical-action-guard-v1', 'baseline': baseline,
                      'required': {'A': {**{k: v for k, v in proposal.items() if k != 'id'},
                                         'conditions': ['endpoint', 'track'],
                                         'frozen_conditions': ['external_load']}}}
            obs = json_artifact('measurements', {'measurements': [{'dbu': [11, 17], 'track': 7}, True]})
            records = {cond: {'action': proposal, 'condition': cond, 'baseline': baseline,
                              'scope': 'frozen_unaffected' if cond == 'external_load' else 'affected',
                              'status': 'unknown' if cond == 'external_load' else 'passed',
                              'observation': dict(obs, pointer='/measurements/0')}
                       for cond in ('endpoint', 'track', 'external_load')}
            if mutation == 'stale_report':
                records['endpoint']['baseline'] = dict(baseline, **{'routed.def': old_def})
            if mutation == 'wrong_report_action':
                records['endpoint']['action'] = dict(proposal, object='other endpoint')
            if mutation == 'wrong_scope': records['track']['scope'] = 'frozen_unaffected'
            if mutation == 'affected_unknown': records['track']['status'] = 'unknown'
            if mutation == 'affected_failed': records['track']['status'] = 'failed'
            if mutation == 'bare_pass': records['track'] = True
            if mutation == 'boolean_observation': records['track']['observation']['pointer'] = '/measurements/1'
            if mutation == 'missing_observation': records['track']['observation']['pointer'] = '/measurements/99'
            if mutation == 'wrong_observation_hash': records['track']['observation']['sha256'] = '0' * 64
            if mutation == 'unknown_record_field': records['track']['other'] = True
            report = json_artifact('checks', {'schema': 'physical-action-checks-v1', 'records': records})
            plan = {'schema': 'physical-action-plan-v1', 'baseline': baseline, 'actions': [proposal],
                    'checks': [dict(report, action_id='A', condition=cond, record=cond) for cond in records]}
            if mutation == 'stale_plan': plan['baseline'] = dict(baseline, **{'routed.def': old_def})
            if mutation == 'missing_check': plan['checks'].pop(1)
            if mutation == 'duplicate_check': plan['checks'][1] = plan['checks'][0]
            if mutation == 'unfixed_condition': plan['checks'][1]['condition'] = 'another_check'
            if mutation == 'missing_record': plan['checks'][1]['record'] = 'absent'
            if mutation == 'wrong_record_hash': plan['checks'][1]['sha256'] = '0' * 64
            if mutation == 'unknown_plan_field': plan['override'] = True
            if mutation == 'missing_action': plan['actions'] = []
            # A reissued matching check is not an authority to change the fixed action.
            if mutation in ('wrong_parameters', 'wrong_object', 'wrong_operation'):
                key = mutation.split('_', 1)[1]
                alternate = dict(proposal, **{key: {'track': 8} if key == 'parameters' else 'different'})
                plan['actions'] = [alternate]
                alternate_report = json_artifact('alternate-checks', {'schema': 'physical-action-checks-v1',
                    'records': {k: dict(v, action=alternate) for k, v in records.items()}})
                plan['checks'] = [dict(alternate_report, action_id='A', condition=cond, record=cond)
                                  for cond in records]
            plan_ref = json_artifact('plan', plan)
            tail = ['{PLAN}', '{ADMISSION}', '{PARENT_GDS}', '{PARENT_CDL}', '{PARENT_DEF}']
            spec = {'schema': 'private-physical-adapter-v1',
                    'commands': {a: [sys.executable, str(driver), a, '{STAGE}', '{OUT}', *tail]
                                 for a in ('prepare', 'submit', 'collect')},
                    'dependencies': [{'path': str(driver), 'sha256': hashlib.sha256(driver.read_bytes()).hexdigest()}],
                    'required_checks': full_checks, 'required_stages': ['materialize'], 'timeout_seconds': 5,
                    'scope': 'synthetic only', 'construction_plan': plan_ref, 'action_guard': policy,
                    'deliverables': {**{label: '{OUT}/' + label for label in baseline},
                                     'construction_witness': '{OUT}/witness.json'}}
            if mutation == 'missing_parent_arg': spec['commands']['prepare'].pop()
            if mutation == 'unknown_guard_field': policy['override'] = True
            spec_ref = json_artifact('adapter', spec)
            state.update(phase='awaiting_builder', round=1,
                         task={'id': 'task-1', 'round': 1, 'execution': 'physical_adapter',
                               'physical_adapter': spec_ref['artifact'], 'construction_plan': 'plan',
                               'checks': full_checks, 'max_candidates': 1, 'route': 'fixture'})
        return run, run / 'candidates' / 'candidate'

    def stage(self, run, action):
        return pb.action(run, 'candidate', action, 'materialize')

    def test_fixed_actions_with_frozen_unknown_complete_without_qualification(self):
        run, directory = self.fixture()
        for op in ('prepare', 'submit', 'collect'):
            self.assertEqual(self.stage(run, op)['returncode'], 0)
        self.assertEqual(self.stage(run, 'finalize')['qualification'], 'not_run')
        frozen = read(directory / 'manifest.json')['files']
        for name in ('action-admission.json', 'construction-plan.json', 'baseline/layout.gds',
                     'baseline/source.cdl', 'baseline/routed.def', 'physical/witness.json'):
            self.assertIn(name, frozen)

    def test_rejects_invalid_guard_before_private_prepare(self):
        for mutation in ('missing_action', 'wrong_object', 'wrong_operation', 'wrong_parameters',
                         'missing_check', 'duplicate_check', 'unfixed_condition', 'affected_unknown',
                         'affected_failed', 'bare_pass', 'wrong_scope', 'stale_plan', 'stale_report',
                         'wrong_report_action', 'missing_record', 'wrong_record_hash', 'boolean_observation',
                         'missing_observation', 'wrong_observation_hash', 'unknown_plan_field',
                         'unknown_record_field', 'unknown_guard_field', 'missing_parent_arg'):
            with self.subTest(mutation=mutation):
                run, directory = self.fixture(mutation)
                with self.assertRaises(ValueError): self.stage(run, 'prepare')
                self.assertFalse(directory.exists())

    def test_each_later_entry_rejects_changed_objects_and_consumed_copies(self):
        for op, changed in (('submit', 'baseline/layout.gds'), ('collect', 'construction-plan.json'),
                            ('collect', 'measurements'), ('finalize', 'action-admission.json'),
                            ('finalize', 'parent-routed.def')):
            with self.subTest(operation=op, changed=changed):
                run, directory = self.fixture()
                self.stage(run, 'prepare')
                if op != 'submit': self.stage(run, 'submit')
                if op == 'finalize': self.stage(run, 'collect')
                state = read(run / 'state.json')
                path = run / state['artifacts'][changed]['object'] if changed in state['artifacts'] else directory / changed
                path.write_text('unexpected mutation')
                journal = (directory / 'physical-execution.json').read_bytes()
                with self.assertRaises(ValueError): self.stage(run, op)
                self.assertEqual((directory / 'physical-execution.json').read_bytes(), journal)
                self.assertFalse((directory / 'manifest.json').exists())

    def test_final_witness_binds_admission_and_all_physical_outputs(self):
        for mutation in ('admission_sha256', 'source.cdl', 'routed.def'):
            with self.subTest(mutation=mutation):
                run, directory = self.fixture()
                for op in ('prepare', 'submit', 'collect'): self.stage(run, op)
                path = directory / 'physical' / mutation
                if mutation == 'admission_sha256':
                    witness_path = directory / 'physical/witness.json'
                    witness = read(witness_path)
                    witness[mutation] = '0' * 64
                    atomic(witness_path, witness)
                else:
                    path.write_text('changed actual output')
                with self.assertRaises(ValueError): self.stage(run, 'finalize')
                self.assertNotIn('candidate', read(run / 'state.json')['artifacts'])
