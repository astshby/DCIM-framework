"""Call existing SciPy solvers through bounded, constraint-checked EDA state codecs."""
import copy
import math
import time
from runtime import identity, require
from algorithm_portfolio import RUNNABLE


class BudgetStop(Exception):
    pass


def finite(value, name, positive=False):
    require(type(value) in (int,float) and math.isfinite(value) and
            (value>0 if positive else True),'Invalid '+name)
    return value


def rank(item):
    return (not item['feasible'],item['violation'],item['score'])


def optimize(bounds, baseline, decoder, evaluator, budget, initial_vector=None):
    """Measure baseline first, then upstream proposals; preserve raw checked results.

    `decoder` is a versioned construction-domain mapping, not a legality oracle.
    `evaluator` returns the shared feasible/violation/score contract. Neither the
    SciPy numeric objective nor solver convergence is physical qualification.
    """
    require(isinstance(budget,dict) and not set(budget)-{
        'algorithm','evaluations','steps','seconds','seed','population','temperature',
        'stepsize','local_iterations'},'Unknown external solver budget field')
    algorithm=budget.get('algorithm')
    require(algorithm in RUNNABLE,'Unsupported/unimplemented portfolio adapter')
    limit=budget.get('evaluations',128);steps=budget.get('steps',limit*8)
    seconds=finite(budget.get('seconds',5),'seconds',True)
    require(type(limit) is int and 1<=limit<=10000,'Evaluation budget must be 1..10000')
    require(type(steps) is int and 1<=steps<=100000,'Step budget must be 1..100000')
    require(seconds<=60,'External planning call must finish within 60 seconds')
    seed=budget.get('seed',0);require(type(seed) is int,'Integer seed required')
    population=budget.get('population',8);require(type(population) is int and 5<=population<=64,'Invalid population')
    local_iterations=budget.get('local_iterations',20)
    require(type(local_iterations) is int and 1<=local_iterations<=1000,'Invalid local_iterations')
    temperature=finite(budget.get('temperature',1),'temperature',True)
    stepsize=finite(budget.get('stepsize',.5),'stepsize',True)
    require(isinstance(bounds,(list,tuple)) and len(bounds)<=256,'Need at most 256 explicit variables')
    checked=[]
    for item in bounds:
        require(isinstance(item,(list,tuple)) and len(item)==2,'Each variable needs lower/upper bound')
        lo,hi=item;finite(lo,'lower');finite(hi,'upper');require(lo<hi,'Nonempty variable bounds required')
        checked.append((float(lo),float(hi)))
    bounds=checked;n=len(bounds)
    require(algorithm!='scipy_shgo' or n<=10,'SHGO is restricted to at most ten decoded variables')
    if initial_vector is None:initial_vector=[(a+b)/2 for a,b in bounds]
    require(isinstance(initial_vector,(list,tuple)) and len(initial_vector)==n,'Initial variable vector differs')
    require(all(type(x) in (int,float) and math.isfinite(x) and a<=x<=b
                for x,(a,b) in zip(initial_vector,bounds)),'Initial vector is outside variable domain')
    started=time.monotonic();trials={};trace=[];cache_hits=0;attempts=0
    def measure(state, operation, vector=None):
        nonlocal cache_hits
        key=identity(state)
        cached=key in trials
        if not cached:
            if trials and (len(trials)>=limit or time.monotonic()-started>=seconds):
                raise BudgetStop('evaluation_budget' if len(trials)>=limit else 'time_budget')
            result=copy.deepcopy(evaluator(copy.deepcopy(state)))
            require(isinstance(result,dict) and type(result.get('feasible')) is bool,'Evaluator must declare feasibility')
            finite(result.get('violation'),'violation');finite(result.get('score'),'score')
            require(result['violation']>=0,'Negative violation measure')
            # The actual canonical state emitted by the evaluator is retained.
            actual=copy.deepcopy(result.get('state',state))
            result.update(state=actual,id='u-'+identity(actual)[:16],parent=None,
                operation=operation,parameters={} if vector is None else {'vector':list(vector)})
            trials[key]=result
        else:cache_hits+=1
        return trials[key],cached
    baseline_item,_=measure(baseline,'actual_baseline')
    baseline_item=copy.deepcopy(baseline_item)
    def objective(vector):
        nonlocal attempts
        if attempts>=steps:raise BudgetStop('step_budget')
        if time.monotonic()-started>=seconds:raise BudgetStop('time_budget')
        if len(trials)>=limit:raise BudgetStop('evaluation_budget')
        attempts+=1
        # Powell and basin-local steps may leave the numerical box. Decode only
        # clamped parameter-domain values; the hard evaluator remains authoritative.
        clipped=[min(b,max(a,float(x))) for x,(a,b) in zip(vector,bounds)]
        state=decoder(clipped)
        item,cached=measure(state,'upstream_'+algorithm,clipped)
        item['parent']=baseline_item['id'] if item['id']!=baseline_item['id'] else None
        trace.append({'step':attempts-1,'candidate':item['id'],'cached':cached,
            'operation':'upstream_'+algorithm,'parameters':{'vector':clipped},
            'feasible':item['feasible'],'score':item['score'],'violation':item['violation']})
        # Bounded monotonic score maps keep every feasible state below every
        # infeasible state, regardless of arbitrary objective magnitude.
        if item['feasible']:
            return item['score']/(1+abs(item['score']))
        return 2+item['violation']/(1+item['violation'])
    reason='solver_completed';implementation_version=None
    if not bounds:
        reason='all_variables_frozen'
    elif limit==1:
        reason='evaluation_budget'
    else:
        try:
            import numpy as np
            import scipy
            from scipy import optimize as so
            implementation_version=scipy.__version__
            x0=np.array(initial_vector,dtype=float);rng=np.random.RandomState(seed)
            if algorithm=='scipy_de':
                init=np.array([[rng.uniform(a,b) for a,b in bounds] for _ in range(population)],dtype=float)
                init[0]=x0
                so.differential_evolution(objective,bounds,maxiter=steps,popsize=population,
                    seed=seed,polish=False,init=init,workers=1,updating='immediate',tol=0,atol=0)
            elif algorithm=='scipy_dual_annealing':
                so.dual_annealing(objective,bounds,maxiter=steps,maxfun=max(1,limit),seed=seed,
                    no_local_search=True,x0=x0,initial_temp=temperature)
            elif algorithm=='scipy_basinhopping':
                so.basinhopping(objective,x0,niter=steps,seed=seed,T=temperature,stepsize=stepsize,
                    minimizer_kwargs={'method':'Powell','options':{'maxiter':local_iterations,'maxfev':max(1,steps)}})
            elif algorithm=='scipy_shgo':
                so.shgo(objective,bounds,n=min(64,max(2,limit-1)),iters=1,
                    minimizer_kwargs={'method':'Powell','options':{'maxiter':local_iterations}},
                    options={'maxev':max(1,limit-1),'maxiter':1},sampling_method='simplicial')
            else:
                so.minimize(objective,x0,method='Powell',options={
                    'maxiter':local_iterations,'maxfev':steps,'xtol':1e-5,'ftol':1e-5})
        except BudgetStop as error:
            reason=str(error)
        except ImportError as error:
            raise ValueError('Requested upstream solver dependency unavailable: '+str(error))
    if len(trials)>=limit:reason='evaluation_budget'
    elif attempts>=steps:reason='step_budget'
    ranked=sorted(trials.values(),key=rank);selected=[p for p in ranked if p['feasible']][:4]
    return {'algorithm':algorithm+'@'+str(implementation_version or 'not_invoked'),
        'implementation':{'package':'scipy','version':implementation_version,'adapter':'scipy-codec-v1',
                          'upstream_called':bool(bounds and limit>1)},
        'budget':dict(budget),'evaluations':len(trials),'attempts':attempts,'cache_hits':cache_hits,
        'elapsed_seconds':time.monotonic()-started,'stop':reason,'qualification':'not_run',
        'baseline_evaluation':baseline_item,'best':ranked[0],
        'improved':bool(selected and rank(selected[0])<rank(baseline_item)),
        'selected':selected,'trials':list(trials.values()),'trace':trace,
        'objective_kind':'shared_hard_checked_proxy',
        'solver_claim':'No physical qualification or global optimum claim, including SHGO on decoded discrete states'}


def codec(problem, initial=None):
    """Return the finite parameter domain and versioned state decoder."""
    if problem.get('schema')=='transistor-placement-v1':
        import transistor_search as ts
        ts.validate_problem(problem)
        baseline=copy.deepcopy(initial if initial is not None else ts.initial_state(problem))
        baseline=ts.evaluate(problem,baseline)['state']
        devices={d['id']:d for d in problem['devices']};bounds=[];vector=[];keys=[]
        for row in baseline['rows']:
            order=row['order']
            if len(order)>1:
                for i,did in enumerate(order):
                    keys.append(('order',row['id'],did));bounds.append((0.,1.));vector.append(i/(len(order)-1))
        for device in problem['devices']:
            if device['sd_swap']:
                keys.append(('flip',device['id']));bounds.append((0.,1.));vector.append(float(device['id'] in baseline['flips']))
        def decode(values):
            state=copy.deepcopy(baseline);scores={};flips=set(baseline['flips'])
            for key,value in zip(keys,values):
                if key[0]=='order':scores[key[2]]=value
                elif value>=.5:flips.add(key[1])
                else:flips.discard(key[1])
            for row in state['rows']:
                # Stable ties preserve the reviewed baseline order.
                row['order']=sorted(row['order'],key=lambda did:scores.get(did,0))
            state['flips']=sorted(flips);return state
        return {'bounds':bounds,'baseline':baseline,'initial_vector':vector,'decoder':decode,
                'evaluator':lambda state:ts.evaluate(problem,state),'representation':'transistor'}
    from search.model import validate_problem,from_shelf,state_from_placements,evaluate
    validate_problem(problem)
    if initial is None:
        baseline=state_from_placements(problem,problem['initial_placements']) if 'initial_placements' in problem else from_shelf(problem)
    else:baseline=tuple(tuple(v) for v in initial)
    evaluate(problem,baseline,baseline)
    movable=set(problem.get('movable_ids',[b['id'] for b in problem['blocks']]))
    bounds=[];vector=[];keys=[]
    for i,(block,state) in enumerate(zip(problem['blocks'],baseline)):
        if block['id'] not in movable:continue
        for axis in (0,1):
            maximum=problem['max_width_um' if axis==0 else 'max_height_um']
            # Preserve even an out-of-outline repair baseline inside the parameter
            # domain; infeasible proposals are never selected by the hard evaluator.
            high=max(maximum,float(state[axis]))
            keys.append((i,axis));bounds.append((0.,high));vector.append(float(state[axis]))
        if block.get('orientations',[0])==[0,90]:
            keys.append((i,2));bounds.append((0.,1.));vector.append(float(state[2]==90))
    def decode(values):
        state=[list(v) for v in baseline];grid=problem.get('grid_um')
        for (i,axis),value in zip(keys,values):
            if axis==2:state[i][axis]=90 if value>=.5 else 0
            else:state[i][axis]=round(round(value/grid)*grid,12) if grid else round(value,12)
        return tuple(tuple(v) for v in state)
    return {'bounds':bounds,'baseline':baseline,'initial_vector':vector,'decoder':decode,
            'evaluator':lambda state:evaluate(problem,state,baseline),'representation':'blocks'}


def search(problem,budget,initial=None):
    spec=codec(problem,initial)
    result=optimize(spec['bounds'],spec['baseline'],spec['decoder'],spec['evaluator'],budget,spec['initial_vector'])
    result['representation']=spec['representation']
    result['codec']='device-random-keys-v1' if spec['representation']=='transistor' else 'fixed-instance-coordinates-v1'
    return result
