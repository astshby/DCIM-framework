"""Validate declared architecture and require scoped, artifact-bound measurements.

This module checks numeric intent and evidence identity. A private checker must
extract masks, functional rows, device bodies and routes from actual outputs.
"""
import math
from runtime import evidence, require

CHECKS = {'functional_rows', 'implant_continuity', 'body_power', 'interface_access'}
METHODS = {'coordinate_measurement', 'mask_extraction', 'connectivity_extraction', 'electrical_simulation'}


def number(value, label, positive=False):
    require(type(value) in (int, float) and math.isfinite(value) and
            (value > 0 if positive else value >= 0), 'Invalid architecture ' + label)
    return value


def text(value):
    require(isinstance(value, str) and value.strip() and len(value) <= 240, 'Architecture text required')


def admit(root, state, task, plan=None, required=False):
    spec = task.get('architecture')
    require(spec is not None or not required, 'Integrated Builder task requires architecture contract')
    if spec is None:
        return
    require(isinstance(spec, dict) and set(spec) == {'schema','purpose','parent','sources','functional_rows',
            'order','transforms','implant_bands','ownership','required_measurements','unresolved'},
            'Unknown or missing architecture field')
    require(spec['schema'] == 'architecture-task-v1' and spec['purpose'] in ('screen','qualification'),
            'Invalid architecture schema/purpose')
    evidence(root, state, spec['sources'])
    parent = spec['parent']
    require(isinstance(parent, dict) and set(parent) == {'width_um','height_um'}, 'Parent H/W required')
    for key in parent:
        number(parent[key], key, positive=True)
    for axis in ('width','height'):
        limit = state['project']['macro'].get('max_'+axis+'_um')
        require(limit is None or parent[axis+'_um'] <= limit, 'Parent exceeds project dimension bound')
    require(isinstance(plan, dict) and plan.get('placements'), 'Architecture needs an executable measured plan')
    require(plan['width_um'] <= parent['width_um']+1e-9 and plan['height_um'] <= parent['height_um']+1e-9,
            'Selected plan exceeds architecture H/W')
    placements = {p['id']:p for p in plan['placements']}
    order = spec['order']
    require(isinstance(order, list) and len(order) == len(placements) and set(order) == set(placements),
            'Architecture order must name every selected instance exactly once')
    require([placements[k]['x_um'] for k in order] == sorted(placements[k]['x_um'] for k in order),
            'Selected coordinates contradict architecture order')
    require(isinstance(spec['transforms'], dict) and set(spec['transforms']) == set(placements),
            'Architecture transforms must name every instance')
    for key, transform in spec['transforms'].items():
        actual = placements[key]
        expected = ({'rotation_deg':actual['rotation_deg']} if 'rotation_deg' in actual else
                    {'sd_swap':actual.get('sd_swap', False)})
        require(transform == expected, 'Selected transform differs from architecture')
    rows = spec['functional_rows']
    require(isinstance(rows, list) and rows, 'Declare common functional rows')
    known = set()
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'id','origin_um','height_um','phase','members'},
                'Invalid functional row declaration')
        text(row['id']); text(row['phase'])
        require(row['id'] not in known, 'Duplicate functional row')
        known.add(row['id'])
        number(row['origin_um'], 'row origin'); number(row['height_um'], 'row height', True)
        require(row['origin_um']+row['height_um'] <= parent['height_um']+1e-9, 'Functional row exceeds parent')
        require(isinstance(row['members'], dict) and row['members'] and set(row['members']) <= set(placements),
                'Functional row members must reference selected instances')
        for key, offset in row['members'].items():
            number(offset, 'functional row offset')
            require(offset+row['height_um'] <= placements[key]['height_um']+1e-9,
                    'Functional row extends outside instance')
            require(abs(placements[key]['y_um']+offset-row['origin_um']) <= 1e-9,
                    'Selected placement contradicts declared functional row origin')
    require(set().union(*(set(row['members']) for row in rows)) == set(placements),
            'Every instance needs a functional row declaration')
    bands = spec['implant_bands']
    require(isinstance(bands, list) and bands, 'Declare intended straight PP/NP bands')
    previous = None
    for band in bands:
        require(isinstance(band, dict) and set(band) == {'kind','y0_um','y1_um','owner'}, 'Invalid implant band')
        require(band['kind'] in ('PP','NP'), 'Implant band must be PP or NP')
        text(band['owner']); number(band['y0_um'], 'band start'); number(band['y1_um'], 'band end', True)
        require(band['y0_um'] < band['y1_um'] <= parent['height_um'], 'Invalid implant band extent')
        if previous is not None:
            require(abs(previous['y1_um']-band['y0_um']) <= 1e-9, 'Intended implant bands must directly abut')
        previous = band
    owners = spec['ownership']
    require(isinstance(owners, dict) and {'tap','body','termination','interfaces'} <= set(owners),
            'Declare TAP/body/termination/interface ownership')
    for key, owner in owners.items():
        text(key); text(owner)
    methods = spec['required_measurements']
    require(isinstance(methods, dict) and CHECKS <= set(methods) <= set(task['checks']),
            'Task must require affected architecture checks')
    require(all(method in METHODS for method in methods.values()), 'Unsupported measurement method')
    require(methods['implant_continuity'] == 'mask_extraction' and
            methods['body_power'] == 'connectivity_extraction', 'Physical bands/body require extracted observations')
    require(isinstance(spec['unresolved'], list) and len(set(spec['unresolved'])) == len(spec['unresolved']) and
            set(spec['unresolved']) <= set(methods), 'Unknown unresolved condition')
    require(spec['purpose'] == 'screen' or not spec['unresolved'],
            'Qualification admission needs resolved architecture conditions')


def review(root, state, payload):
    spec = state['task'].get('architecture')
    if spec is None:
        return
    measurements = payload.get('architecture_checks')
    require(isinstance(measurements, dict) and set(measurements) == set(spec['required_measurements']),
            'Review every architecture measurement boundary')
    for name, item in measurements.items():
        require(isinstance(item, dict) and set(item) == {'status','method','evidence','observation'},
                'Architecture measurement needs status/method/evidence/observation')
        require(item['status'] == payload['checks'][name], 'Architecture and review status differ')
        require(item['method'] == spec['required_measurements'][name], 'Measurement method differs from contract')
        text(item['observation']); evidence(root, state, item['evidence'])
        require(set(item['evidence']) <= set(payload['evidence']), 'Architecture evidence must be in review')
        if item['status'] == 'passed':
            require(any(state['artifacts'][key]['round'] == state['round'] and
                        state['artifacts'][key]['kind'] in ('candidate_file','evidence') for key in item['evidence']),
                    'Passed measurement needs actual current-output/report evidence')
    if payload['verdict'] == 'passed' and spec['purpose'] == 'screen':
        require(payload['scope'] == 'architecture_screen', 'Diagnostic screen must retain its exact review scope')
