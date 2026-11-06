"""Budgeted SA, hill climbing, large-neighborhood repair and beam search."""
import math
import random
import time
from runtime import identity, require
from .model import evaluate, from_shelf, number, rank, validate_problem
from .operators import OPERATORS, movable, propose, reinsert
from .adaptive import Selection, destroy_members, repair

VERSIONS = {'anneal':'anneal-v1','local':'local-v1','lns':'lns-v1','beam':'coordinate-beam-v2','adaptive':'adaptive-lns-v1'}


def catalog():
    return {'implemented':VERSIONS,'operators':list(OPERATORS),
            'state':'coordinate-placement-v1','objective':'geometry_and_center_hpwl_proxy',
            'unsupported':['standard_cell_engine','routing','transistor_topology'],
            'selection':'Reflect chooses from task, reviewed memory and budget; default anneal',
            'qualification':'proxy_only'}


def search(problem, budget, initial=None):
    validate_problem(problem)
    require(not set(budget)-{'algorithm','evaluations','seconds','seed','beam','steps','operators',
                            'temperature','cooling','patience','neighborhood','repair_candidates','repair_beam','adaptation_decay'}, 'Unknown search budget field')
    algorithm = budget.get('algorithm','anneal')
    require(algorithm in VERSIONS, 'Unsupported algorithm; inspect --catalog')
    limit = budget.get('evaluations',128)
    beam_width = budget.get('beam',8)
    seconds = number(budget.get('seconds',5),'seconds',True)
    steps = budget.get('steps',limit*8)
    require(type(limit) is int and 1 <= limit <= 10000, 'Evaluation budget must be 1..10000')
    require(type(steps) is int and 1 <= steps <= 100000, 'Step budget must be 1..100000')
    require(type(beam_width) is int and 1 <= beam_width <= 64, 'Beam width must be 1..64')
    require(seconds <= 60, 'Planning call must finish within 60 seconds')
    require(type(budget.get('seed',0)) is int, 'Seed must be an integer')
    temperature = number(budget.get('temperature',1),'temperature',True)
    cooling = number(budget.get('cooling',.99),'cooling',True)
    require(cooling <= 1, 'Cooling must be <=1')
    patience = budget.get('patience',100)
    size = budget.get('neighborhood',3)
    require(type(patience) is int and 1 <= patience <= 100000, 'Invalid patience')
    require(type(size) is int and 1 <= size <= 64, 'Invalid neighborhood')
    allowed = budget.get('operators',list(OPERATORS))
    require(isinstance(allowed,list) and allowed and len(set(allowed)) == len(allowed)
            and all(o in OPERATORS for o in allowed), 'Invalid operators')
    if algorithm in ('lns','adaptive'):
        require('reinsert' in allowed, 'LNS requires the reinsert operation')
    repair_candidates=budget.get('repair_candidates',8)
    repair_beam=budget.get('repair_beam',2)
    decay=number(budget.get('adaptation_decay',.8),'adaptation decay')
    require(decay<=1 and type(repair_candidates) is int and 1<=repair_candidates<=32 and
            type(repair_beam) is int and 1<=repair_beam<=4,'Invalid adaptive repair settings')
    selection=Selection(decay)
    initial = tuple(tuple(v) for v in initial) if initial is not None else from_shelf(problem)
    started = time.monotonic()
    rng = random.Random(budget.get('seed',0))
    visited, trace = {}, []
    cache_hits=0
    best=None
    class BudgetStop(Exception):
        pass
    def measure(key, parent, operation, parameters):
        nonlocal cache_hits,best
        cached = key in visited
        if visited and time.monotonic()-started>=seconds:
            raise BudgetStop('time_budget')
        if not cached:
            if len(visited)>=limit:
                raise BudgetStop('evaluation_budget')
            visited[key] = dict(evaluate(problem,key,initial),id='p-'+identity(key)[:16],
                                state=key,parent=parent,operation=operation,parameters=parameters)
        else:
            cache_hits+=1
        if best is None or rank(visited[key])<rank(best):
            best=visited[key]
        return visited[key],cached
    current,_ = measure(initial,None,'initial',{})
    best = current
    baseline = dict(current)
    stagnant = 0
    reason = 'step_budget'
    ids = movable(problem)
    for step in range(steps):
        if len(visited) >= limit:
            reason='evaluation_budget'; break
        if time.monotonic()-started >= seconds:
            reason='time_budget'; break
        if not ids:
            reason='all_instances_frozen'; break
        if algorithm == 'beam':
            ranked = sorted(visited.values(),key=rank)
            # Include spatially distinct states, rather than a single greedy parent.
            pool = ranked[:beam_width]
            current = rng.choice(pool)
        best_before=best
        try:
            if algorithm=='adaptive':
                destroy,repair_kind=selection.choose(rng)
                members=destroy_members(problem,current['state'],destroy,size,rng)
                trial,cached,parameters=repair(problem,current,members,repair_kind,measure,rng,
                                               repair_candidates,repair_beam,destroy)
                key=trial['state']; operation='adaptive_'+repair_kind
            elif algorithm == 'lns':
                members = rng.sample(ids,min(size,len(ids)))
                key = current['state']
                for i in members:
                    key = reinsert(problem,key,i,rng)
                operation='destroy_reinsert'
                parameters={'instances':[problem['blocks'][i]['id'] for i in members]}
                trial,cached=measure(key,current['id'],operation,parameters)
            else:
                key,operation,parameters = propose(problem,current['state'],rng,allowed)
                trial,cached=measure(key,current['id'],operation,parameters)
        except BudgetStop as error:
            reason=str(error)
            trace.append({'step':step,'parent':current['id'],'operation':'interrupted_repair',
                          'candidate':None,'accepted':False,'stop':reason,'cached':False})
            break
        improved = rank(trial) < rank(current)
        accepted = improved
        probability = 1.0 if improved else 0.0
        temp = max(temperature*(cooling**step),1e-12)
        if algorithm in ('anneal','adaptive') and not improved and key != current['state']:
            # Once feasible, never leave the cheap hard-constraint feasible set.
            if trial['feasible'] == current['feasible']:
                delta = (trial['score']-current['score'] if trial['feasible'] else
                         trial['violation']-current['violation'])
                probability=math.exp(-max(0,delta)/temp)
                accepted=rng.random() < probability
        trace.append({'step':step,'parent':current['id'],'candidate':trial['id'],
                      'operation':operation,'parameters':parameters,'cached':cached,
                      'accepted':accepted,'probability':probability,
                      'temperature':temp if algorithm in ('anneal','adaptive') else None,
                      'best':best['id']})
        if algorithm=='adaptive':
            reward=5 if rank(best)<rank(best_before) else 2 if improved else 1 if accepted and key!=current['state'] else 0
            selection.update(destroy,repair_kind,reward)
            trace[-1]['reward']=reward
        if accepted:
            current=trial
        if rank(best) < rank(best_before):
            stagnant=0
        else:
            stagnant+=1
        if algorithm in ('local','lns','adaptive') and stagnant >= patience:
            reason='sampled_neighborhood_stalled'; break
    if len(visited) >= limit:
        reason='evaluation_budget'
    ranked = sorted(visited.values(),key=rank)
    selected = [p for p in ranked if p['feasible']][:4]
    return {'algorithm':VERSIONS[algorithm], 'budget':dict(budget,algorithm=algorithm),
            'evaluations':len(visited),'attempts':len(trace),'cache_hits':cache_hits,
            'elapsed_seconds':time.monotonic()-started,'stop':reason,
            'objective_kind':'geometry_and_center_hpwl_proxy','qualification':'not_run',
            'baseline_evaluation':baseline,'best':ranked[0],
            'adaptation':selection.result() if algorithm=='adaptive' else None,
            'improved':bool(selected and rank(selected[0]) < rank(baseline)),
            'selected':selected,'trials':list(visited.values()),'trace':trace}
