"""Reflect's stable search entry: previous-round baseline, common evaluator, strategy selection."""
import argparse
import copy
from runtime import atomic, artifact, cli, event, evidence, identity, read, require, transaction
from search import catalog, search, state_from_placements, validate_problem
from search.model import evaluate as evaluate_coordinates, from_shelf, number
from search.baseline import previous


def evaluate(problem, key):
    """Compatibility adapter for explicit shelf plans; searches use coordinates."""
    return evaluate_coordinates(problem,from_shelf(problem,key))


def validate_references(state, problem):
    learning={x['id']:x for x in state['learning']}
    technologies=set()
    for block in problem['blocks']:
        require(block['source'] in learning,'Block must cite a learned layout')
        context=learning[block['source']]['context']
        technologies.add(tuple(context[k] for k in ('process','release','stack')))
        observed=next((b for b in learning[block['source']]['observations']['blocks'] if b['cell']==block['cell']),None)
        require(observed and all(abs(observed[k]-block[k])<1e-9 for k in ('width_um','height_um')),
                'Dimensions must match learned evidence')
    require(len(technologies)==1,'Do not compose unmatched process/release/stack references')


def plan(run, problem=None, budget=None, baseline=None):
    budget=budget or {}
    with transaction(run) as (root,state):
        require(state.get('schema_version')==4,'Use a new run for the coordinate search contract')
        require('reflect-'+str(state['round']) not in state['requests'],
                'Finish the saved Reflect request before adding search evidence')
        require(state['phase'] in ('learning','awaiting_reflect'),'Search belongs inside Reflect after memory commit')
        if state['round']:
            snapshot,origin=previous(root,state,baseline)
            base=snapshot['problem']
            problem=copy.deepcopy(problem if problem is not None else base)
            # Objective/bounds/movable scope may change explicitly, instance/net identity may not.
            require(problem['blocks']==base['blocks'] and problem.get('nets',[])==base.get('nets',[]),
                    'Search must preserve previous-round instances and nets; structural redesign belongs to Builder')
            initial=state_from_placements(problem,snapshot['placements'])
        else:
            require(baseline is None,'Reflect0 cannot name a prior candidate')
            require(problem is not None,'Reflect0 requires an explicit reference-derived problem')
            problem=copy.deepcopy(problem)
            validate_problem(problem)
            initial=state_from_placements(problem,problem.pop('initial_placements')) if 'initial_placements' in problem else from_shelf(problem)
            origin={'kind':'reference_initialization','round':0}
        validate_problem(problem)
        validate_references(state,problem)
        evidence(root,state,list(dict.fromkeys(b['source'] for b in problem['blocks'])))
        name='search-'+identity({'problem':problem,'budget':budget,'baseline':origin,'initial':initial,'round':state['round']})[:16]
        if name in state['artifacts']:
            evidence(root,state,[name])
            recorded=next(e['payload'] for e in state['events']
                          if e['operation']=='heuristic_plan' and e['payload']['artifact']==name)
            return dict(recorded,already_recorded=True)
        used=[e['payload'] for e in state['events'] if e['round']==state['round'] and e['operation']=='heuristic_plan']
        require(len(used)<8,'Reflect search call budget exhausted')
        remaining_evaluations=10000-sum(e['evaluations'] for e in used)
        remaining_steps=100000-sum(e['attempts'] for e in used)
        remaining_seconds=60-sum(e['elapsed_seconds'] for e in used)
        require(remaining_evaluations>0 and remaining_steps>0 and remaining_seconds>0,'Reflect search budget exhausted')
        # Validate the requested budget before applying the aggregate round cap.
        effective=dict(budget)
        for k,default,remaining in [('evaluations',128,remaining_evaluations),
                                     ('steps',budget.get('evaluations',128)*8,remaining_steps),
                                     ('seconds',5,remaining_seconds)]:
            value=budget.get(k,default)
            number(value,k,True)
            if k!='seconds':
                require(type(value) is int,'Integer '+k+' required')
            require(value <= {'evaluations':10000,'steps':100000,'seconds':60}[k], 'Search budget too large: '+k)
            effective[k]=min(value,remaining)
        result=search(problem,effective,initial)
        result.update(problem=problem,baseline=origin,objective_identity=identity(problem))
        path=root/'requests'/(name+'.json')
        atomic(path,result)
        artifact(root,state,name,path,'search')
        routes=[]
        for item in result['selected']:
            rid=name+'-'+item['id']
            state['routes'][rid]={'id':rid,'source':'algorithm','lifecycle':'active','evidence':[name],
                'plan':item,'search':name,'baseline':origin,'mechanism':result['algorithm']+':'+item['operation'],
                'validation':['independent connectivity','applicable DRC/LVS','routed area','electrical checks'],
                'status':'proxy_only','round':state['round']}
            routes.append({'id':rid,'area_um2':item['area_um2'],'hpwl_proxy_um':item['hpwl_proxy_um']})
        summary={'artifact':name,'algorithm':result['algorithm'],'baseline':origin,'routes':routes,
                 'evaluations':result['evaluations'],'attempts':result['attempts'],'cache_hits':result['cache_hits'],
                 'improved_proxy':result['improved'],'elapsed_seconds':result['elapsed_seconds'],'stop':result['stop']}
        event(state,'heuristic_plan',summary)
        return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True)
    p.add_argument('--problem')
    p.add_argument('--budget')
    p.add_argument('--baseline',help='Explicit candidate from the immediately preceding reviewed round')
    p.add_argument('--catalog',action='store_true')
    a=p.parse_args()
    if a.catalog:
        return catalog()
    return plan(a.run,read(a.problem) if a.problem else None,read(a.budget) if a.budget else {},a.baseline)


if __name__=='__main__':
    cli(main)
