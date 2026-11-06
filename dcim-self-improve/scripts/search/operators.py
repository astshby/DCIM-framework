"""Bounded coordinate moves shared by every placement search strategy."""
from .model import dimensions

OPERATORS = ('translate', 'swap', 'rotate', 'reinsert', 'cluster_shift')


def movable(problem):
    ids = problem.get('movable_ids', [b['id'] for b in problem['blocks']])
    return [i for i,b in enumerate(problem['blocks']) if b['id'] in ids]


def snapped(problem, value):
    grid = problem.get('grid_um')
    value = max(0,value)
    return round(round(value/grid)*grid, 12) if grid else round(value,12)


def reinsert(problem, state, index, rng):
    """Place beside another block or at an origin/outline anchor; no global repacking."""
    b = problem['blocks'][index]
    angle = rng.choice(b.get('orientations',[0]))
    w,h = dimensions(b,angle)
    gap = problem['gap_um']
    xs = [0, max(0,problem['max_width_um']-w)]
    ys = [0, max(0,problem['max_height_um']-h)]
    for j,(x,y,a) in enumerate(state):
        if j == index:
            continue
        ow,oh = dimensions(problem['blocks'][j],a)
        xs.extend([x,x+ow+gap,max(0,x-w-gap)])
        ys.extend([y,y+oh+gap,max(0,y-h-gap)])
    out = list(state)
    out[index] = (snapped(problem,rng.choice(xs)),snapped(problem,rng.choice(ys)),angle)
    return tuple(out)


def propose(problem, state, rng, allowed):
    ids = movable(problem)
    if not ids:
        return state, 'frozen', {}
    op = rng.choice(allowed)
    i = rng.choice(ids)
    out = list(state)
    x,y,a = state[i]
    step = problem.get('step_um',1)
    detail = {'instances':[problem['blocks'][i]['id']]}
    if op == 'translate':
        dx,dy = rng.choice(((step,0),(-step,0),(0,step),(0,-step)))
        out[i] = (snapped(problem,x+dx),snapped(problem,y+dy),a)
        detail.update(dx_um=dx,dy_um=dy)
    elif op == 'swap' and len(ids)>1:
        j = rng.choice([j for j in ids if j != i])
        out[i] = (*state[j][:2], a)
        out[j] = (x,y,state[j][2])
        detail['instances'].append(problem['blocks'][j]['id'])
    elif op == 'rotate':
        if 90 in problem['blocks'][i].get('orientations',[0]):
            out[i] = (x,y,90-a)
    elif op == 'reinsert':
        return reinsert(problem,state,i,rng),op,detail
    elif op == 'cluster_shift':
        # A connected neighborhood when explicit nets exist; otherwise a local random subset.
        linked = {n for net in problem.get('nets',[]) if problem['blocks'][i]['id'] in net for n in net}
        members = [j for j in ids if problem['blocks'][j]['id'] in linked] or [i]
        dx,dy = rng.choice(((step,0),(-step,0),(0,step),(0,-step)))
        dx=max(dx,-min(state[j][0] for j in members)); dy=max(dy,-min(state[j][1] for j in members))
        for j in members:
            out[j]=(snapped(problem,state[j][0]+dx),snapped(problem,state[j][1]+dy),state[j][2])
        detail={'instances':[problem['blocks'][j]['id'] for j in members],'dx_um':dx,'dy_um':dy}
    return tuple(out),op,detail
