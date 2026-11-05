"""Bounded diverse beam search over learned block order, row cuts and rotations."""
import argparse
import math
import random
import time
from runtime import atomic, artifact, cli, event, identity, read, require, transaction


def number(value, name, positive=False):
    require(type(value) in (int, float) and math.isfinite(value) and
            (value > 0 if positive else value >= 0), 'Invalid ' + name)
    return value


def validate_problem(problem):
    blocks = problem['blocks']
    require(isinstance(blocks, list) and 1 <= len(blocks) <= 64, 'Need 1..64 explicit block instances')
    ids = [b['id'] for b in blocks]
    require(all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids), 'Unique block IDs required')
    for b in blocks:
        number(b['width_um'], 'width', True)
        number(b['height_um'], 'height', True)
        require(b.get('orientations', [0]) in ([0], [0, 90]), 'Explicit orientations: [0] or [0,90]')
    number(problem['gap_um'], 'gap')
    for k in ('max_width_um', 'max_height_um'):
        number(problem[k], k, True)
    number(problem.get('wire_weight', 1), 'wire weight')
    for net in problem.get('nets', []):
        require(len(net) >= 2 and all(n in ids for n in net), 'Net refers to unknown block')


def evaluate(problem, key):
    order, cuts, rotations = key
    blocks = problem['blocks']
    gap = problem['gap_um']
    placed = []
    x = y = row_height = width = 0.0
    for index, bindex in enumerate(order):
        if index in cuts:
            y += row_height + gap
            x = row_height = 0.0
        block = blocks[bindex]
        angle = rotations[bindex]
        w, h = block['width_um'], block['height_um']
        if angle:
            w, h = h, w
        placed.append({'id': block['id'], 'cell': block['cell'], 'source': block['source'],
                       'x_um': x, 'y_um': y, 'width_um': w, 'height_um': h, 'rotation_deg': angle})
        width = max(width, x + w)
        row_height = max(row_height, h)
        x += w + gap
    height = y + row_height
    centers = {b['id']: (b['x_um'] + b['width_um']/2, b['y_um'] + b['height_um']/2) for b in placed}
    hpwl = 0.0
    for net in problem.get('nets', []):
        xs, ys = zip(*(centers[n] for n in net))
        hpwl += max(xs) - min(xs) + max(ys) - min(ys)
    area = width * height
    footprint = sum(b['width_um'] * b['height_um'] for b in blocks)
    scale = math.sqrt(footprint)
    score = area / footprint + problem.get('wire_weight', 1) * hpwl / scale
    feasible = width <= problem['max_width_um'] and height <= problem['max_height_um']
    violation = max(0, width/problem['max_width_um']-1) + max(0, height/problem['max_height_um']-1)
    return {'placements': placed, 'width_um': width, 'height_um': height, 'area_um2': area,
            'hpwl_proxy_um': hpwl, 'score': score, 'feasible': feasible, 'violation': violation}


def neighbors(key, blocks, rng):
    order, cuts, angles = key
    n = len(order)
    variants = []
    if n > 1:
        i, j = rng.sample(range(n), 2)
        swap = list(order)
        swap[i], swap[j] = swap[j], swap[i]
        variants.append(((tuple(swap), cuts, angles), 'swap'))
        move = list(order)
        move.insert(j, move.pop(i))
        variants.append(((tuple(move), cuts, angles), 'relocate'))
        split = rng.randrange(1, n)
        variants.append(((order, tuple(sorted(set(cuts) ^ {split})), angles), 'split_or_merge_row'))
    rotatable = [i for i, b in enumerate(blocks) if 90 in b.get('orientations', [0])]
    if rotatable:
        i = rng.choice(rotatable)
        rot = list(angles)
        rot[i] = 90 - rot[i]
        variants.append(((order, cuts, tuple(rot)), 'rotate'))
    return variants


def search(problem, budget):
    validate_problem(problem)
    count = budget.get('evaluations', 128)
    width = budget.get('beam', 8)
    seconds = budget.get('seconds', 5)
    require(type(count) is int and 1 <= count <= 10000, 'Evaluation budget must be 1..10000')
    require(type(width) is int and 1 <= width <= 64, 'Beam width must be 1..64')
    number(seconds, 'seconds', True)
    require(seconds <= 60, 'Planning call must finish within 60 seconds')
    rng = random.Random(budget.get('seed', 0))
    n = len(problem['blocks'])
    first = (tuple(range(n)), (), (0,)*n)
    frontier = [(first, None, 'initial')]
    visited = {}
    started = time.monotonic()
    reason = 'sampled_neighborhood_stalled'
    while frontier and len(visited) < count and time.monotonic() - started < seconds:
        for key, parent, operation in frontier:
            if key in visited:
                continue
            if len(visited) >= count or time.monotonic() - started >= seconds:
                break
            item = dict(evaluate(problem, key), id='p-' + identity(key)[:16],
                        parent=parent, operation=operation, state=key)
            visited[key] = item
        ranked = sorted(visited.values(), key=lambda r: (not r['feasible'], r['violation'], r['score']))
        # Reserve half the beam for distinct row/rotation signatures: avoid pure greedy collapse.
        beam = ranked[:max(1, width//2)]
        signatures = {(r['state'][1], r['state'][2]) for r in beam}
        for item in ranked:
            sig = (item['state'][1], item['state'][2])
            if sig not in signatures and len(beam) < width:
                beam.append(item)
                signatures.add(sig)
        frontier = [(key, item['id'], operation) for item in beam
                    for key, operation in neighbors(item['state'], problem['blocks'], rng)
                    if key not in visited]
        # A random neighborhood can miss unvisited moves; bounded restarts add structural novelty.
        if not frontier and n > 1 and len(visited) < count:
            perm = list(range(n))
            rng.shuffle(perm)
            key = (tuple(perm), tuple(i for i in range(1,n) if rng.random() < .4), (0,)*n)
            if key not in visited:
                frontier = [(key, None, 'restart')]
    if len(visited) >= count:
        reason = 'evaluation_budget'
    elif time.monotonic() - started >= seconds:
        reason = 'time_budget'
    ranked = sorted(visited.values(), key=lambda r: (not r['feasible'], r['violation'], r['score']))
    selected = []
    signatures = set()
    for item in ranked:
        sig = (item['state'][1], item['state'][2])
        if item['feasible'] and sig not in signatures and len(selected) < 4:
            selected.append(item)
            signatures.add(sig)
    return {'algorithm': 'diverse-beam-v1', 'budget': budget, 'evaluations': len(visited),
            'elapsed_seconds': time.monotonic()-started, 'stop': reason,
            'objective_kind': 'geometry_and_center_hpwl_proxy',
            'qualification': 'not_run', 'selected': selected, 'trials': list(visited.values())}


def plan(run, problem, budget):
    with transaction(run) as (root, state):
        require('reflect-' + str(state['round']) not in state['requests'],
                'Finish the saved Reflect request before adding new learning/search evidence')
        require(state['phase'] in ('learning', 'awaiting_reflect'), 'Plan before Reflect dispatch')
        learning = {x['id']: x for x in state['learning']}
        technologies = set()
        for block in problem['blocks']:
            require(block['source'] in learning, 'Block must cite a learned layout')
            context = learning[block['source']]['context']
            technologies.add(tuple(context[k] for k in ('process','release','stack')))
            observed = next((b for b in learning[block['source']]['observations']['blocks']
                             if b['cell'] == block['cell']), None)
            require(observed and all(abs(observed[k]-block[k]) < 1e-9
                                     for k in ('width_um','height_um')), 'Dimensions must match learned evidence')
        require(len(technologies) == 1, 'Do not compose unmatched process/release/stack references')
        result = search(problem, budget)
        result['problem'] = problem
        name = 'search-' + identity({'problem': problem, 'budget': budget, 'round': state['round']})[:16]
        require(name not in state['artifacts'], 'Search already recorded; use its existing routes')
        path = root / 'requests' / (name + '.json')
        atomic(path, result)
        artifact(root, state, name, path, 'search')
        routes = []
        for item in result['selected']:
            rid = name + '-' + item['id']
            state['routes'][rid] = {'id': rid, 'source': 'algorithm', 'lifecycle': 'active',
                'evidence': [name], 'plan': item, 'mechanism': item['operation'],
                'validation': ['independent connectivity', 'applicable DRC/LVS', 'routed area', 'electrical checks'],
                'status': 'proxy_only', 'round': state['round']}
            routes.append({'id': rid, 'area_um2': item['area_um2'], 'hpwl_proxy_um': item['hpwl_proxy_um']})
        event(state, 'heuristic_plan', {'artifact': name, 'routes': routes})
        return {'artifact': name, 'routes': routes, 'evaluations': result['evaluations'], 'stop': result['stop']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    p.add_argument('--problem', required=True)
    p.add_argument('--budget', required=True)
    a = p.parse_args()
    return plan(a.run, read(a.problem), read(a.budget))


if __name__ == '__main__':
    cli(main)
