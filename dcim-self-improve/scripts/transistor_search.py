"""Bounded row-order/device-flip search with declared abstract diffusion rules.

This engine places immutable transistor records. Coordinates are nominal terminal
anchors and abstract device rectangles, not masks, extracted pins, routing or
foundry qualification. The diffusion predicate is a candidate hypothesis only.
Inspired by SA/diffusion-aware cell synthesis (BonnCell; NVCell), not a paper
reproduction. No EDA, model calls, folding, device sizing or topology synthesis.
"""
import copy
import math
import hashlib
import json
import random
import time


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(value):
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode('utf-8')
    return hashlib.sha256(data).hexdigest()

SCHEMA = 'transistor-placement-v1'
LAYOUT_SCHEMA = 'transistor-abstract-layout-v1'
VERSION = 'transistor-row-search-v1'
OPERATORS = ('adjacent_swap', 'reinsert', 'sd_flip', 'pair_swap')


def _object(value, fields, name):
    require(isinstance(value, dict) and set(value) == set(fields),
            name + ' needs exactly: ' + ', '.join(sorted(fields)))


def _text(value, name):
    require(isinstance(value, str) and value.strip() and len(value) <= 240, 'Invalid ' + name)


def _number(value, name, positive=False):
    require(type(value) in (int, float) and math.isfinite(value) and
            (value > 0 if positive else value >= 0), 'Invalid ' + name)


def _ticks(value, grid):
    return int(round(value / grid))


def _on_grid(value, grid, name):
    ratio = value / grid
    require(math.isfinite(ratio) and abs(ratio-round(ratio)) <= 1e-7 and
            (value == 0 or round(ratio) >= 1),
            'Off declared grid: ' + name)
    return int(round(ratio))


def _rect(value, grid, name, access=False):
    _object(value, ('id', 'x_um', 'y_um', 'width_um', 'height_um', 'net') if access else
            ('id', 'x_um', 'y_um', 'width_um', 'height_um'), name)
    _text(value['id'], name + ' ID')
    for key in ('x_um', 'y_um', 'width_um', 'height_um'):
        _number(value[key], name + ' ' + key, key in ('width_um', 'height_um'))
        _on_grid(value[key], grid, name + ' ' + key)
    if access:
        _text(value['net'], name + ' net')


def validate_problem(problem):
    """Reject absent/unknown semantics rather than silently skipping constraints."""
    _object(problem, ('schema', 'technology', 'sources', 'rows', 'devices', 'rules',
                     'ports', 'obstacles', 'reserved_access', 'constraints', 'objective'), 'Problem')
    require(problem['schema'] == SCHEMA, 'Unsupported transistor problem schema')
    _object(problem['technology'], ('process', 'release', 'stack'), 'Technology')
    for key, value in problem['technology'].items():
        _text(value, 'technology ' + key)
    _object(problem['sources'], ('netlist', 'rules'), 'Sources')
    for key, value in problem['sources'].items():
        _text(value, 'source ' + key)
    _object(problem['rules'], ('diffusion_gap_um', 'allow_diffusion_sharing', 'grid_um'), 'Rules')
    rule = problem['rules']
    _number(rule['grid_um'], 'grid', True)
    _number(rule['diffusion_gap_um'], 'diffusion gap')
    _on_grid(rule['diffusion_gap_um'], rule['grid_um'], 'diffusion gap')
    require(type(rule['allow_diffusion_sharing']) is bool, 'Explicit sharing permission required')
    grid = rule['grid_um']
    require(isinstance(problem['rows'], list) and 1 <= len(problem['rows']) <= 16, 'Need 1..16 rows')
    rows = {}
    for row in problem['rows']:
        _object(row, ('id', 'kind', 'y_um', 'height_um', 'body_net'), 'Row')
        _text(row['id'], 'row ID'); _text(row['body_net'], 'row body net')
        require(row['id'] not in rows, 'Duplicate row ID')
        require(row['kind'] in ('pmos', 'nmos'), 'Explicit row polarity required')
        _number(row['y_um'], 'row y'); _number(row['height_um'], 'row height', True)
        _on_grid(row['y_um'], grid, 'row y'); _on_grid(row['height_um'], grid, 'row height')
        rows[row['id']] = row
    ordered = sorted(rows.values(), key=lambda r: r['y_um'])
    for a, b in zip(ordered, ordered[1:]):
        require(_ticks(a['y_um'], grid)+_ticks(a['height_um'], grid) <= _ticks(b['y_um'], grid),
                'Abstract rows overlap')
    require(isinstance(problem['devices'], list) and 1 <= len(problem['devices']) <= 128,
            'Need 1..128 explicit transistors')
    devices = {}
    nets = set()
    for device in problem['devices']:
        _object(device, ('id', 'row', 'kind', 'model', 'width_um', 'height_um',
                         'terminals', 'sd_swap', 'share_group'), 'Device')
        for key in ('id', 'row', 'model'):
            _text(device[key], 'device ' + key)
        require(device['id'] not in devices, 'Duplicate device ID')
        require(device['row'] in rows, 'Unknown device row')
        row = rows[device['row']]
        require(device['kind'] == row['kind'], 'Device polarity differs from row')
        for key in ('width_um', 'height_um'):
            _number(device[key], 'device ' + key, True)
            _on_grid(device[key], grid, 'device ' + key)
        require(_ticks(device['height_um'], grid) <= _ticks(row['height_um'], grid),
                'Device exceeds row height')
        _object(device['terminals'], ('g', 's', 'd', 'b'), 'Device terminals')
        for net in device['terminals'].values():
            _text(net, 'terminal net'); nets.add(net)
        require(device['terminals']['b'] == row['body_net'], 'Device body differs from row supply')
        require(type(device['sd_swap']) is bool, 'Explicit source/drain swap permission required')
        require(device['share_group'] is None or
                (isinstance(device['share_group'], str) and bool(device['share_group'].strip()) and
                 len(device['share_group']) <= 240), 'Invalid share group')
        devices[device['id']] = device
    require(set(rows) == {d['row'] for d in devices.values()}, 'Empty row is not an implemented device row')
    require(isinstance(problem['ports'], list) and len(problem['ports']) <= 256, 'Ports must be a bounded list')
    port_names = set()
    for port in problem['ports']:
        _object(port, ('name', 'net', 'x_um', 'y_um'), 'Port')
        _text(port['name'], 'port name'); _text(port['net'], 'port net')
        require(port['name'] not in port_names, 'Duplicate port name'); port_names.add(port['name'])
        require(port['net'] in nets, 'Port refers to unknown circuit net')
        for key in ('x_um', 'y_um'):
            _number(port[key], 'port ' + key); _on_grid(port[key], grid, 'port ' + key)
    for name in ('obstacles', 'reserved_access'):
        values = problem[name]
        require(isinstance(values, list) and len(values) <= 128, 'Bounded ' + name + ' list required')
        seen = set()
        for item in values:
            _rect(item, grid, name, name == 'reserved_access')
            require(item['id'] not in seen, 'Duplicate ' + name + ' ID'); seen.add(item['id'])
            if name == 'reserved_access':
                require(item['net'] in nets, 'Reserved access refers to unknown circuit net')
    _object(problem['constraints'], ('max_width_um', 'max_height_um', 'width_strict', 'height_strict'), 'Constraints')
    for key in ('max_width_um', 'max_height_um'):
        _number(problem['constraints'][key], key, True)
        _on_grid(problem['constraints'][key], grid, key)
    for key in ('width_strict', 'height_strict'):
        require(type(problem['constraints'][key]) is bool, 'Explicit strict-bound flag required')
    _object(problem['objective'], ('wire_weight', 'break_weight'), 'Objective')
    for key, value in problem['objective'].items():
        _number(value, key)
    return problem


def _circuit_signature(devices, grid):
    return identity([{'id': d['id'], 'kind': d['kind'], 'model': d['model'],
                      'width_grid_units': _ticks(d['width_um'], grid),
                      'height_grid_units': _ticks(d['height_um'], grid),
                      'terminals': d['terminals']}
                     for d in sorted(devices, key=lambda d: d['id'])])


def netlist_signature(problem):
    """Exact named S/D/G/B records and declared grid dimensions, never renamed."""
    return _circuit_signature(problem['devices'], problem['rules']['grid_um'])


def initial_state(problem):
    validate_problem(problem)
    return {'rows': [{'id': row['id'], 'order': [d['id'] for d in problem['devices']
                                              if d['row'] == row['id']]}
                     for row in problem['rows']], 'flips': []}


def _state(problem, state):
    _object(state, ('rows', 'flips'), 'State')
    require(isinstance(state['rows'], list) and len(state['rows']) == len(problem['rows']),
            'State must retain every row')
    known = {d['id']: d for d in problem['devices']}
    expected = {r['id']: {d['id'] for d in problem['devices'] if d['row'] == r['id']}
                for r in problem['rows']}
    by_row = {}
    for row in state['rows']:
        _object(row, ('id', 'order'), 'State row')
        require(isinstance(row['id'], str) and row['id'] in expected and row['id'] not in by_row,
                'State has duplicate or unknown row')
        order = row['order']
        require(isinstance(order, list) and all(isinstance(i, str) for i in order) and
                len(order) == len(expected[row['id']]) and set(order) == expected[row['id']],
                'State changed transistor identity, membership or row')
        by_row[row['id']] = list(order)
    flips = state['flips']
    require(isinstance(flips, list) and all(isinstance(i, str) for i in flips) and
            len(set(flips)) == len(flips) and set(flips) <= set(known), 'Invalid flipped device IDs')
    require(all(known[i]['sd_swap'] for i in flips), 'Source/drain flip is not permitted for this device')
    return {'rows': [{'id': r['id'], 'order': by_row[r['id']]} for r in problem['rows']],
            'flips': sorted(flips)}


def _overlap(a, b, grid):
    ax, ay, aw, ah = (_ticks(a[k], grid) for k in ('x_um', 'y_um', 'width_um', 'height_um'))
    bx, by, bw, bh = (_ticks(b[k], grid) for k in ('x_um', 'y_um', 'width_um', 'height_um'))
    return ax < bx+bw and bx < ax+aw and ay < by+bh and by < ay+ah


def evaluate(problem, state):
    validate_problem(problem)
    state = _state(problem, state)
    grid = problem['rules']['grid_um']
    gap = _ticks(problem['rules']['diffusion_gap_um'], grid)
    devices = {d['id']: d for d in problem['devices']}
    rows = {r['id']: r for r in problem['rows']}
    flips = set(state['flips'])
    placed, seams, violations = [], [], []
    breaks = 0
    width_ticks = 0
    for entry in state['rows']:
        row = rows[entry['id']]
        cursor = 0
        last = None
        for did in entry['order']:
            device = devices[did]
            left, right = ('d', 's') if did in flips else ('s', 'd')
            shared = False
            if last is not None:
                previous, previous_right = last
                shared = (problem['rules']['allow_diffusion_sharing'] and
                          device['share_group'] is not None and
                          previous['share_group'] == device['share_group'] and
                          previous['model'] == device['model'] and
                          previous['kind'] == device['kind'] and
                          previous['terminals']['b'] == device['terminals']['b'] and
                          _ticks(previous['height_um'], grid) == _ticks(device['height_um'], grid) and
                          previous['terminals'][previous_right] == device['terminals'][left])
                if not shared:
                    cursor += gap; breaks += 1
                seams.append({'left': previous['id'], 'right': did, 'shared_candidate': bool(shared),
                              'gap_um': 0 if shared else gap*grid,
                              'facing_nets': [previous['terminals'][previous_right], device['terminals'][left]],
                              'qualification': 'abstract_predicate_only'})
            w = _ticks(device['width_um'], grid)
            h = _ticks(device['height_um'], grid)
            y = _ticks(row['y_um'], grid)
            anchors = {left: (cursor*grid, (y+h/2)*grid),
                       right: ((cursor+w)*grid, (y+h/2)*grid),
                       'g': ((cursor+w/2)*grid, (y+h)*grid),
                       'b': ((cursor+w/2)*grid, y*grid)}
            placement = {'id': did, 'row': row['id'], 'kind': device['kind'], 'model': device['model'],
                         'x_um': cursor*grid, 'y_um': y*grid, 'width_um': w*grid, 'height_um': h*grid,
                         'sd_flipped': did in flips,
                         'terminals': {terminal: {'net': device['terminals'][terminal],
                                      'x_um': point[0], 'y_um': point[1]}
                                       for terminal, point in anchors.items()}}
            placed.append(placement)
            cursor += w
            last = (device, right)
        width_ticks = max(width_ticks, cursor)
    # Retain the complete declared row envelope and all reserved physical resources.
    height_ticks = max(_ticks(r['y_um'], grid)+_ticks(r['height_um'], grid) for r in problem['rows'])
    for item in problem['obstacles'] + problem['reserved_access']:
        width_ticks = max(width_ticks, _ticks(item['x_um'], grid)+_ticks(item['width_um'], grid))
        height_ticks = max(height_ticks, _ticks(item['y_um'], grid)+_ticks(item['height_um'], grid))
    for port in problem['ports']:
        width_ticks = max(width_ticks, _ticks(port['x_um'], grid))
        height_ticks = max(height_ticks, _ticks(port['y_um'], grid))
    for p in placed:
        for key in ('obstacles', 'reserved_access'):
            for region in problem[key]:
                if _overlap(p, region, grid):
                    violations.append(key + ':' + p['id'] + ':' + region['id'])
    limit = problem['constraints']
    for label, ticks in (('width', width_ticks), ('height', height_ticks)):
        maximum = _ticks(limit['max_'+label+'_um'], grid)
        if ticks > maximum or (limit[label+'_strict'] and ticks == maximum):
            violations.append(label + '_bound')
    terminals = {}
    for device in placed:
        for terminal in device['terminals'].values():
            terminals.setdefault(terminal['net'], []).append((terminal['x_um'], terminal['y_um']))
    for port in problem['ports']:
        terminals.setdefault(port['net'], []).append((port['x_um'], port['y_um']))
    hpwl = 0
    for points in terminals.values():
        xs, ys = zip(*points)
        hpwl += max(xs)-min(xs)+max(ys)-min(ys)
    width, height = width_ticks*grid, height_ticks*grid
    area = width*height
    device_area = sum(d['width_um']*d['height_um'] for d in problem['devices'])
    score = (area/device_area + problem['objective']['wire_weight']*hpwl/math.sqrt(device_area) +
             problem['objective']['break_weight']*breaks/len(problem['devices']))
    require(math.isfinite(score), 'Nonfinite objective')
    retained = [dict(d, terminals={t: endpoint['net'] for t, endpoint in d['terminals'].items()})
                for d in placed]
    actual_signature = _circuit_signature(retained, grid)
    require(actual_signature == netlist_signature(problem), 'Placed transistor circuit changed')
    return {'state': state, 'placements': placed, 'seams': seams, 'width_um': width, 'height_um': height,
            'area_um2': area, 'hpwl_proxy_um': hpwl, 'diffusion_breaks': breaks, 'score': score,
            'feasible': not violations, 'violation': len(violations), 'violations': violations,
            'netlist_signature': actual_signature, 'qualification': 'proxy_only',
            'routing': 'not_generated', 'pin_access': 'reserved_regions_screen_only',
            'terminal_geometry': 'nominal_anchors_not_mask_pins', 'body_supply': 'declared_net_only'}


def build_abstract(problem, state):
    metrics = evaluate(problem, state)
    return {'schema': LAYOUT_SCHEMA, 'problem_identity': identity(problem),
            'netlist_signature': metrics['netlist_signature'], 'state': metrics['state'],
            'rows': copy.deepcopy(problem['rows']), 'placements': metrics['placements'],
            'seams': metrics['seams'], 'ports': copy.deepcopy(problem['ports']),
            'obstacles': copy.deepcopy(problem['obstacles']),
            'reserved_access': copy.deepcopy(problem['reserved_access']),
            'metrics': {k: v for k, v in metrics.items() if k not in ('state', 'placements', 'seams')},
            'routing': 'not_generated', 'qualification': 'abstract_placement_only'}


def _rank(item):
    return (not item['feasible'], item['violation'], item['score'])


def _proposal(state, problem, rng, operations):
    candidate = copy.deepcopy(state)
    op = rng.choice(operations)
    rows = candidate['rows']
    eligible = [r for r in rows if len(r['order']) > 1]
    detail = {}
    if op in ('adjacent_swap', 'reinsert') and eligible:
        row = rng.choice(eligible)
        order = row['order']
        i = rng.randrange(len(order))
        if op == 'adjacent_swap':
            i = min(i, len(order)-2)
            order[i], order[i+1] = order[i+1], order[i]
        else:
            item = order.pop(i); order.insert(rng.randrange(len(order)+1), item)
        detail = {'row': row['id'], 'index': i}
    elif op == 'sd_flip':
        choices = [d['id'] for d in problem['devices'] if d['sd_swap']]
        if choices:
            did = rng.choice(choices)
            if did in candidate['flips']:
                candidate['flips'].remove(did)
            else:
                candidate['flips'].append(did)
            candidate['flips'].sort()
            detail = {'device': did}
    elif op == 'pair_swap' and len(eligible) > 1:
        # Coupled adjacent changes retain row identities; no cross-polarity swap.
        selected = rng.sample(eligible, 2)
        indexes = []
        for row in selected:
            i = rng.randrange(len(row['order'])-1)
            row['order'][i], row['order'][i+1] = row['order'][i+1], row['order'][i]
            indexes.append(i)
        detail = {'rows': [r['id'] for r in selected], 'indexes': indexes}
    return candidate, op, detail


def search(problem, budget, initial=None):
    validate_problem(problem)
    require(isinstance(budget, dict) and not set(budget)-{'algorithm', 'evaluations', 'steps', 'seconds',
            'seed', 'temperature', 'cooling', 'operators'}, 'Unknown transistor budget field')
    algorithm = budget.get('algorithm', 'anneal')
    require(algorithm in ('anneal', 'local'), 'Transistor engine supports anneal or local')
    limit, steps = budget.get('evaluations', 128), budget.get('steps', 1024)
    for value, maximum, label in ((limit, 10000, 'evaluations'), (steps, 100000, 'steps')):
        require(type(value) is int and 1 <= value <= maximum, 'Invalid '+label+' budget')
    seconds = budget.get('seconds', 5)
    _number(seconds, 'seconds', True); require(seconds <= 60, 'Search wall limit is 60 seconds')
    seed = budget.get('seed', 0)
    require(type(seed) is int, 'Integer seed required')
    temperature, cooling = budget.get('temperature', 1), budget.get('cooling', .99)
    _number(temperature, 'temperature', True); _number(cooling, 'cooling', True)
    require(cooling <= 1, 'Cooling must be <=1')
    operations = budget.get('operators', list(OPERATORS))
    require(isinstance(operations, list) and operations and all(isinstance(o, str) for o in operations) and
            len(set(operations)) == len(operations) and
            all(o in OPERATORS for o in operations), 'Unsupported transistor operation')
    state = _state(problem, initial if initial is not None else initial_state(problem))
    rng = random.Random(seed)
    started = time.monotonic()
    trials, visited, trace = [], {}, []
    cache_hits = 0

    def measure(candidate, parent, operation, parameters):
        key = identity(candidate)
        if key in visited:
            return visited[key], True
        item = evaluate(problem, candidate)
        item.update(id='t-'+key[:16], parent=parent, operation=operation, parameters=parameters)
        trials.append(item); visited[key] = item
        return item, False

    current, _ = measure(state, None, 'initial', {})
    baseline, best = current, current
    reason = 'step_budget'
    for step in range(steps):
        if len(trials) >= limit:
            reason = 'evaluation_budget'; break
        if time.monotonic()-started >= seconds:
            reason = 'time_budget'; break
        proposed, op, parameters = _proposal(current['state'], problem, rng, operations)
        candidate, cached = measure(proposed, current['id'], op, parameters)
        if cached:
            cache_hits += 1
        accepted = _rank(candidate) < _rank(current)
        probability = 1.0 if accepted else 0.0
        temp = max(temperature*cooling**step, 1e-12)
        if algorithm == 'anneal' and not accepted and candidate['id'] != current['id']:
            # A feasible state never becomes infeasible through annealing acceptance.
            if candidate['feasible'] == current['feasible']:
                delta = (candidate['score']-current['score'] if candidate['feasible'] else
                         candidate['violation']-current['violation'])
                probability = math.exp(-max(0, delta)/temp)
                accepted = rng.random() < probability
        if _rank(candidate) < _rank(best):
            best = candidate
        trace.append({'step': step, 'parent': current['id'], 'candidate': candidate['id'],
                      'operation': op, 'parameters': parameters, 'cached': cached,
                      'accepted': accepted, 'probability': probability,
                      'temperature': temp if algorithm == 'anneal' else None, 'best': best['id']})
        if accepted:
            current = candidate
    if len(trials) >= limit:
        reason = 'evaluation_budget'
    selected = sorted((t for t in trials if t['feasible']), key=_rank)[:4]
    return {'algorithm': VERSION+'-'+algorithm, 'problem_identity': identity(problem),
            'netlist_signature': netlist_signature(problem), 'budget': dict(budget, algorithm=algorithm),
            'baseline_evaluation': baseline, 'best': best, 'selected': selected, 'trials': trials,
            'trace': trace, 'evaluations': len(trials), 'attempts': len(trace), 'cache_hits': cache_hits,
            'elapsed_seconds': time.monotonic()-started, 'stop': reason,
            'objective_kind': 'abstract_device_area_terminal_hpwl_diffusion_breaks',
            'qualification': 'not_run', 'routing': 'not_generated',
            'improved': bool(selected and _rank(selected[0]) < _rank(baseline))}
