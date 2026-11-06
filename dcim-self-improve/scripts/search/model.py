"""Coordinate-preserving placement state and a fixed, inexpensive proxy evaluator."""
import math
from runtime import require


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
        require(isinstance(b['source'], str) and isinstance(b['cell'], str), 'Explicit block source/cell')
    number(problem['gap_um'], 'gap')
    for k in ('max_width_um', 'max_height_um'):
        number(problem[k], k, True)
    number(problem.get('wire_weight', 1), 'wire weight')
    number(problem.get('step_um', 1), 'search move step', True)
    if 'grid_um' in problem:
        number(problem['grid_um'], 'declared placement grid', True)
    movable = problem.get('movable_ids', ids)
    require(isinstance(movable, list) and len(set(movable)) == len(movable) and
            all(i in ids for i in movable), 'Invalid movable_ids')
    for net in problem.get('nets', []):
        require(isinstance(net, list) and len(net) >= 2 and all(n in ids for n in net),
                'Net refers to unknown block')


def dimensions(block, angle):
    w, h = block['width_um'], block['height_um']
    return (h, w) if angle == 90 else (w, h)


def state_from_placements(problem, placements):
    require(isinstance(placements, list) and len(placements) == len(problem['blocks']), 'Missing placement instances')
    by_id = {p['id']: p for p in placements}
    require(len(by_id) == len(placements) and set(by_id) == {b['id'] for b in problem['blocks']}, 'Placement identity mismatch')
    result = []
    for b in problem['blocks']:
        p = by_id[b['id']]
        x, y, angle = p['x_um'], p['y_um'], p['rotation_deg']
        number(x, 'x'); number(y, 'y')
        require(type(angle) is int and angle in b.get('orientations', [0]), 'Disallowed orientation')
        w, h = dimensions(b, angle)
        require(p['source'] == b['source'] and p['cell'] == b['cell'] and
                abs(p['width_um']-w) < 1e-8 and abs(p['height_um']-h) < 1e-8,
                'Placement master/dimensions mismatch')
        result.append((x, y, angle))
    return tuple(result)


def states_match(left, right):
    """Allow only arithmetic roundoff when checking generated reference transforms."""
    return len(left)==len(right) and all(a[2]==b[2] and abs(a[0]-b[0])<=1e-8 and
                                       abs(a[1]-b[1])<=1e-8 for a,b in zip(left,right))


def from_shelf(problem, spec=None):
    """Reflect0/legacy explicit-plan adapter only; never re-pack a saved baseline."""
    n = len(problem['blocks'])
    order, cuts, rotations = spec if spec is not None else (list(range(n)), [], [0]*n)
    require(len(order) == n and all(type(i) is int for i in order) and sorted(order) == list(range(n)), 'Invalid permutation')
    require(len(set(cuts)) == len(cuts) and all(type(c) is int and 0 < c < n for c in cuts), 'Invalid row cuts')
    require(len(rotations) == n and all(type(a) is int and a in b.get('orientations',[0])
                                      for a,b in zip(rotations,problem['blocks'])), 'Invalid rotations')
    states = [None]*n
    x = y = row_h = 0
    for k, i in enumerate(order):
        if k in cuts:
            y += row_h + problem['gap_um']; x = row_h = 0
        w,h = dimensions(problem['blocks'][i],rotations[i])
        states[i] = (x,y,rotations[i])
        x += w + problem['gap_um']; row_h = max(row_h,h)
    return tuple(states)


def rank(item):
    return (not item['feasible'], item['violation'], item['score'])


def evaluate(problem, state, fixed_reference=None):
    require(len(state) == len(problem['blocks']), 'Wrong state size')
    placed = []
    movable = set(problem.get('movable_ids', [b['id'] for b in problem['blocks']]))
    violations = []
    for i,(b, values) in enumerate(zip(problem['blocks'],state)):
        x,y,angle = values
        number(x,'x'); number(y,'y')
        require(type(angle) is int and angle in b.get('orientations',[0]), 'Disallowed orientation')
        if fixed_reference is not None:
            require(b['id'] in movable or tuple(values) == tuple(fixed_reference[i]), 'Frozen instance moved')
        w,h = dimensions(b,angle)
        placed.append(dict(id=b['id'],cell=b['cell'],source=b['source'],x_um=x,y_um=y,
                           width_um=w,height_um=h,rotation_deg=angle))
        grid = problem.get('grid_um')
        if grid and (abs(x/grid-round(x/grid)) > 1e-7 or abs(y/grid-round(y/grid)) > 1e-7):
            violations.append('off_grid:'+b['id'])
    # Envelope is anchored at the declared origin, preserving boundary whitespace.
    width = max(p['x_um']+p['width_um'] for p in placed)
    height = max(p['y_um']+p['height_um'] for p in placed)
    excess = max(0,width/problem['max_width_um']-1)+max(0,height/problem['max_height_um']-1)
    gap = problem['gap_um']
    for i,a in enumerate(placed):
        for b in placed[i+1:]:
            separated = (a['x_um']+a['width_um']+gap <= b['x_um']+1e-9 or
                         b['x_um']+b['width_um']+gap <= a['x_um']+1e-9 or
                         a['y_um']+a['height_um']+gap <= b['y_um']+1e-9 or
                         b['y_um']+b['height_um']+gap <= a['y_um']+1e-9)
            if not separated:
                violations.append('spacing:'+a['id']+':'+b['id'])
    centers = {p['id']:(p['x_um']+p['width_um']/2,p['y_um']+p['height_um']/2) for p in placed}
    hpwl = 0
    for net in problem.get('nets',[]):
        xs,ys = zip(*(centers[i] for i in net))
        hpwl += max(xs)-min(xs)+max(ys)-min(ys)
    footprint = sum(b['width_um']*b['height_um'] for b in problem['blocks'])
    area = width*height
    score = area/footprint + problem.get('wire_weight',1)*hpwl/math.sqrt(footprint)
    require(math.isfinite(score), 'Nonfinite objective')
    return dict(placements=placed,width_um=width,height_um=height,area_um2=area,
                hpwl_proxy_um=hpwl,score=score,feasible=not violations and excess <= 1e-9,
                violation=excess+len(violations),violations=violations,
                qualification='proxy_only',routing='not_generated')
