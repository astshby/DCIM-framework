"""Persistent, scoped learning goals and their Builder/Analyst evidence bindings."""
import re
from runtime import evidence, require
from memory import TEXT_FIELDS, MAX_TEXT


def text(value, name):
    require(isinstance(value,str) and value.strip() and len(value)<=MAX_TEXT,'Invalid learning '+name)
    return value


def active(state, module=None):
    goals=state.get('learning_goals',[])
    superseded={g.get('supersedes') for g in goals}
    return [g for g in reversed(goals) if g['id'] not in superseded
            and (not module or g['module']==module)
            and (g['scope']=='general' or g['technology']==state['project']['technology'])]


def focus(state, module=None):
    """Separate from recent memory: foundational goals do not age out of retrieval."""
    result=[]
    for goal in active(state,module):
        outcomes=[o for o in state.get('learning_outcomes',[]) if o['goal']==goal['id']]
        result.append(dict(goal,latest_check=outcomes[-1] if outcomes else None))
    return result


def update(root, state, entries):
    require(isinstance(entries,list) and len(entries)<=6,'At most six learning updates')
    known={g['id']:g for g in state.get('learning_goals',[])}
    learning={r['id']:r for r in state['learning']}
    current={g['id'] for g in active(state)}
    allowed={'id','module','stage','scope','technology','evidence','checks','supersedes',*TEXT_FIELDS}
    for item in entries:
        g=dict(item)
        require(not set(g)-allowed,'Unknown learning-goal field')
        require(isinstance(g.get('id'),str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,80}',g['id'])
                and g['id'] not in known,'Unique learning-goal ID required')
        require(g.get('module') in {m['id'] for m in state['project']['modules'] if m['enabled']}|{'dcim'},'Unknown learning module')
        for field in (*TEXT_FIELDS,'stage'):
            text(g.get(field),field)
        require(g.get('scope') in ('general','process'),'Learning scope must be general or process')
        if g['scope']=='process':
            require(g.get('technology')==state['project']['technology'] and all(g['technology'].values()),
                    'Process learning needs the exact declared technology')
        else:
            require(not g.get('technology'),'General method cannot carry process-specific applicability')
        evidence(root,state,g.get('evidence'))
        require(len(g['evidence'])<=8 and any(i in learning for i in g['evidence']) and
                all(i in learning or state['artifacts'][i]['kind']=='analyst_review' for i in g['evidence']),
                'Learning goals need captured observations; corrections may also cite Analyst reviews')
        checks=g.get('checks')
        require(isinstance(checks,list) and checks and len(checks)<=8 and len(set(checks))==len(checks),
                'Explicit learning checks required')
        for c in checks: text(c,'check')
        previous=g.get('supersedes')
        if previous:
            require(previous in current,'Supersede an active learning goal')
            require(all(known[previous][k]==g[k] for k in ('module','stage','scope')),'Learning correction changes scope')
            current.remove(previous)
        g.update(round=state['round'],status='hypothesis')
        state.setdefault('learning_goals',[]).append(g)
        known[g['id']]=g; current.add(g['id'])
    require(len(active(state))<=24,'At most 24 active learning goals; revise existing goals rather than append indefinitely')
    for module in {g['module'] for g in active(state)}:
        require(len(active(state,module))<=6,'At most six active goals per module')


def bind_task(state, task):
    ids=task.get('learning_goals')
    require(isinstance(ids,list) and 1<=len(ids)<=6 and len(set(ids))==len(ids),
            'Builder task needs explicit learning_goals')
    goals={g['id']:g for g in active(state,task['module'])}
    require(set(ids)<=set(goals),'Task references unknown, superseded or incompatible learning goal')
    for key in ids:
        g=goals[key]
        require(g['stage']==task['stage'],'Learning goal stage differs from task')
        reference_ids={r['id'] for r in state['learning']}
        require(set(g['evidence']) & reference_ids <= set(task['learning_ids']),'Task must carry its learning references')
        require(set(g['checks'])<=set(task['checks']),'Task must require its learning checks')
    if state['round']==0:
        sources={r['id']:r['kind'] for r in state['learning']}
        require({sources[e] for i in ids for e in goals[i]['evidence'] if e in sources}=={'compiler','digital_flow'},
                'Reflect0 task must bind learning from compiler and digital flow')
    return [goals[i] for i in ids]


def review(root, state, payload):
    task=state['task']
    outcomes=payload.get('learning_checks')
    require(isinstance(outcomes,dict) and set(outcomes)==set(task['learning_goals']),
            'Analyst must report every task learning goal')
    goals={g['id']:g for g in active(state,task['module'])}
    for key,outcome in outcomes.items():
        require(set(outcome)=={'conclusion','observation','evidence'},'Learning check needs conclusion, observation, evidence')
        require(outcome['conclusion'] in ('supported','refuted','inconclusive'),'Invalid learning conclusion')
        text(outcome['observation'],'review observation')
        evidence(root,state,outcome['evidence'])
        require(len(outcome['evidence'])<=8 and set(outcome['evidence'])<=set(payload['evidence']),
                'Learning check evidence must be part of Analyst review')
        kinds=('candidate','candidate_file','evidence')
        if outcome['conclusion']=='inconclusive':
            kinds+=('builder_result',)
        require(any(state['artifacts'][e]['round']==state['round'] and
                    state['artifacts'][e]['kind'] in kinds
                    for e in outcome['evidence']),'Learning check needs actual current-round evidence')
        if outcome['conclusion']!='inconclusive':
            completed=('passed',) if outcome['conclusion']=='supported' else ('passed','failed')
            require(all(payload['checks'].get(c) in completed for c in goals[key]['checks']),
                    'A decisive learning conclusion requires completed checks')
        state.setdefault('learning_outcomes',[]).append(dict(outcome,goal=key,round=state['round'],
                                                              review='review-'+str(state['round'])))
