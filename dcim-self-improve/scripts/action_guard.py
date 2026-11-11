"""Identity/coverage admission for opt-in physical adapters; no physical oracle.

The captured adapter, not the mutable proposal, fixes exact actions and conditions.
Checks must identify immutable JSON records and separately captured observations.
"""
import hashlib
import re
from pathlib import Path
from runtime import atomic, evidence, identity, read, require

BASELINE = {'layout.gds', 'source.cdl', 'routed.def'}
PARENT_TOKENS = {'layout.gds': 'PARENT_GDS', 'source.cdl': 'PARENT_CDL',
                 'routed.def': 'PARENT_DEF'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fields(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected),
            'Invalid action guard ' + label + ' fields')


def name(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,95}', value),
            'Invalid action guard identifier')
    return value


def binding(root, state, value):
    fields(value, {'artifact', 'sha256'}, 'artifact binding')
    name(value['artifact'])
    evidence(root, state, [value['artifact']])
    item = state['artifacts'][value['artifact']]
    require(value['sha256'] == item['sha256'], 'Action guard artifact identity differs')
    path = root / item['object']
    require(not path.is_symlink(), 'Action guard artifact must not be a symlink')
    return path


def baseline(root, state, value):
    fields(value, BASELINE, 'baseline')
    for item in value.values():
        binding(root, state, item)


def pointer(value, location):
    require(isinstance(location, str) and 1 <= len(location) <= 512 and location.startswith('/'),
            'Action guard needs a JSON observation pointer')
    try:
        for token in location[1:].split('/'):
            require(not re.search(r'~(?![01])', token), 'Invalid JSON pointer escape')
            token = token.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                require(re.fullmatch(r'0|[1-9][0-9]*', token), 'Invalid JSON pointer index')
                value = value[int(token)]
            else:
                require(isinstance(value, dict), 'JSON pointer traverses a scalar')
                value = value[token]
    except (KeyError, IndexError):
        raise ValueError('Action guard observation pointer does not resolve')
    require(isinstance(value, (dict, list)) and value,
            'Action guard observation must locate structured data, not a pass boolean or report string')
    return value


def check_action(value):
    fields(value, {'id', 'operation', 'object', 'parameters'}, 'action')
    name(value['id']); name(value['operation'])
    obj = value['object']
    require((isinstance(obj, str) and 1 <= len(obj) <= 512) or
            (isinstance(obj, dict) and obj), 'Action guard needs an exact object')
    require(isinstance(value['parameters'], dict), 'Action guard parameters must be an object')
    # Canonical encoding also rejects NaN/Infinity. Private payload semantics are
    # not interpreted here; exact bytes/values are bound to the captured contract.
    require(len(str(value)) <= 32768, 'Action guard action exceeds bound')
    identity(value)


def admit(root, state, task, spec):
    """Revalidate immutable inputs at task admission AND every physical entry."""
    guard = spec['action_guard']
    fields(guard, {'schema', 'baseline', 'required'}, 'capability')
    require(guard['schema'] == 'physical-action-guard-v1', 'Unsupported action guard schema')
    require('construction_plan' in spec, 'Action guard requires a captured construction plan')
    baseline(root, state, guard['baseline'])
    required = guard['required']
    require(isinstance(required, dict) and 1 <= len(required) <= 64,
            'Action guard needs bounded fixed actions')
    expected = {}
    for action_id, entry in required.items():
        name(action_id)
        require(isinstance(entry, dict) and {'operation', 'object', 'parameters', 'conditions'} <= set(entry)
                and not set(entry) - {'operation', 'object', 'parameters', 'conditions', 'frozen_conditions'},
                'Invalid action guard required action fields')
        action = dict(id=action_id, **{k: entry[k] for k in ('operation', 'object', 'parameters')})
        check_action(action)
        affected, frozen = entry['conditions'], entry.get('frozen_conditions', [])
        for items, minimum in ((affected, 1), (frozen, 0)):
            require(isinstance(items, list) and minimum <= len(items) <= 64,
                    'Action guard conditions must be bounded lists')
            for condition in items: name(condition)
            require(len(set(items)) == len(items), 'Duplicate action guard condition')
        require(not set(affected) & set(frozen), 'Affected condition cannot be frozen')
        for condition in affected: expected[(action_id, condition)] = 'affected'
        for condition in frozen: expected[(action_id, condition)] = 'frozen_unaffected'
    plan_path = binding(root, state, spec['construction_plan'])
    plan = read(plan_path)
    fields(plan, {'schema', 'baseline', 'actions', 'checks'}, 'construction plan')
    require(plan['schema'] == 'physical-action-plan-v1', 'Unsupported action plan schema')
    require(plan['baseline'] == guard['baseline'], 'Action plan baseline differs from fixed parent')
    actions = plan['actions']
    require(isinstance(actions, list) and len(actions) == len(required), 'Missing fixed action')
    found = {}
    for action in actions:
        check_action(action)
        aid = action['id']
        require(aid in required and aid not in found, 'Unknown or duplicate action')
        fixed = dict(id=aid, **{k: required[aid][k] for k in ('operation', 'object', 'parameters')})
        require(identity(action) == identity(fixed), 'Action differs from fixed adapter contract')
        found[aid] = action
    checks = plan['checks']
    require(isinstance(checks, list) and len(checks) == len(expected),
            'Action plan cannot omit or add conditions')
    seen = set()
    for check in checks:
        fields(check, {'action_id', 'condition', 'artifact', 'sha256', 'record'}, 'check reference')
        aid, condition = check['action_id'], check['condition']
        name(aid); name(condition); name(check['record'])
        pair = (aid, condition)
        require(pair in expected and pair not in seen, 'Unknown or duplicate action condition')
        seen.add(pair)
        report_path = binding(root, state, {k: check[k] for k in ('artifact', 'sha256')})
        report = read(report_path)
        fields(report, {'schema', 'records'}, 'check report')
        require(report['schema'] == 'physical-action-checks-v1' and isinstance(report['records'], dict),
                'Unsupported action check report')
        require(check['record'] in report['records'], 'Missing action check record')
        record = report['records'][check['record']]
        fields(record, {'action', 'condition', 'baseline', 'scope', 'status', 'observation'}, 'check record')
        require(identity(record['action']) == identity(found[aid]) and record['condition'] == condition
                and record['baseline'] == guard['baseline'], 'Action check action/baseline binding differs')
        require(record['scope'] == expected[pair], 'Action check affected/frozen scope differs')
        require(record['status'] in ('passed', 'unknown'), 'Action condition failed or invalid')
        require(expected[pair] != 'affected' or record['status'] == 'passed',
                'Affected action condition is unknown')
        observation = record['observation']
        fields(observation, {'artifact', 'sha256', 'pointer'}, 'observation')
        require(observation['artifact'] != check['artifact'], 'Separate source observation required')
        raw_path = binding(root, state, {k: observation[k] for k in ('artifact', 'sha256')})
        pointer(read(raw_path), observation['pointer'])
    require(seen == set(expected), 'Incomplete affected action coverage')
    # Standalone path placeholders make the actual recipe invocation reviewable.
    argv = spec['commands']['prepare']
    for token in ('PLAN', 'ADMISSION', *PARENT_TOKENS.values()):
        require('{' + token + '}' in argv, 'Guarded prepare must receive {' + token + '}')
    return {'schema': 'physical-action-admission-v1',
            'adapter_sha256': state['artifacts'][task['physical_adapter']]['sha256'],
            'plan_sha256': spec['construction_plan']['sha256'],
            'baseline': guard['baseline'], 'actions': actions, 'checks': checks,
            'required': required}


def capture(root, state, directory, admission):
    (directory / 'baseline').mkdir()
    for label, item in admission['baseline'].items():
        source = binding(root, state, item)
        (directory / 'baseline' / label).write_bytes(source.read_bytes())
    atomic(directory / 'action-admission.json', admission)


def verify_copies(directory, spec, admission):
    pairs = [(directory / 'action-admission.json', identity(admission)),
             (directory / 'adapter.json', identity(spec))]
    pairs.extend((directory / 'baseline' / label, item['sha256'])
                 for label, item in admission['baseline'].items())
    pairs.extend((directory / 'dependencies' / ('%04d-%s' % (i, Path(dep['path']).name)), dep['sha256'])
                 for i, dep in enumerate(spec['dependencies']))
    for path, sha in pairs:
        require(path.is_file() and not path.is_symlink() and digest(path) == sha,
                'Consumed action guard copy changed: ' + path.name)


def values(directory):
    return dict(ADMISSION=str(directory / 'action-admission.json'),
                **{token: str(directory / 'baseline' / label) for label, token in PARENT_TOKENS.items()})


def witness(actual, spec, admission):
    record = read(actual['construction_witness'])
    fields(record, {'schema', 'plan_sha256', 'admission_sha256', 'outputs'}, 'consumption witness')
    require(record['schema'] == 'physical-action-witness-v1'
            and record['plan_sha256'] == spec['construction_plan']['sha256']
            and record['admission_sha256'] == identity(admission),
            'Physical output does not witness the admitted action plan')
    fields(record['outputs'], BASELINE, 'witness outputs')
    require(record['outputs'] == {label: digest(actual[label]) for label in BASELINE},
            'Physical output differs from action witness')
