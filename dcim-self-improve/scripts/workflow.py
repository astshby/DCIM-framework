"""Enforce Reflect0 -> Builder -> Analyst -> memory -> Reflect using saved packets."""
import argparse
from pathlib import Path
import re
from runtime import atomic, artifact, cli, event, evidence, identity, read, require, status, store, transaction
import memory

REFLECT_CONTRACT = 'ai-self-proposal-v1'


def short(value, label, maximum=500):
    require(isinstance(value, str) and value.strip() and len(value) <= maximum, 'Missing/oversized ' + label)
    return value


def context_data(root, state, role):
    task = state['task'] or {}
    instructions = ['AGENTS.md', 'SKILL.md', role + '.md']
    return {
        'instructions': {n: (root/'instructions'/n).read_text(encoding='utf-8')
                         for n in instructions if (root/'instructions'/n).exists()},
        'task': task, 'phase': state['phase'], 'round': state['round'],
        'project': state['project'],
        'learning': state['learning'] if state['round'] == 0 else [
            x for x in state['learning'] if x['context']['module'] == task.get('module')],
        'memory': memory.select(state, task.get('stage'), task.get('module')),
        'review': state['reviews'].get(str(state['round'])),
        'artifacts': {k:v for k,v in state['artifacts'].items() if v['round'] == state['round']},
        'routes': [dict({k:v for k,v in r.items() if k != 'plan'},
                        measurements={k:r['plan'][k] for k in ('area_um2','hpwl_proxy_um','width_um','height_um','feasible')}
                        if 'plan' in r else {}) for r in state['routes'].values()
                   if r['lifecycle'] == 'active' and r['source'] in ('ai', 'algorithm')],
    }


def context(run, role, since=None):
    with transaction(run) as (root, state):
        expected = {'learning': 'reflect', 'awaiting_reflect': 'reflect',
                    'awaiting_builder': 'builder', 'awaiting_analyst': 'analyst',
                    'awaiting_memory': 'analyst', 'closed': 'reflect'}
        require(role == expected[state['phase']], 'Role cannot act at this stage')
        data = context_data(root, state, role)
        signatures = {k: identity(v) for k,v in data.items()}
        token = identity(signatures)
        old = state['context_receipts'].get(since, {})
        state['context_receipts'][token] = signatures
        changed = {k:v for k,v in data.items() if old.get(k) != signatures[k]}
        event(state, 'context', {'role': role, 'token': token, 'sections': list(changed)})
        return {'token': token, 'changed': changed}


def request(run):
    with transaction(run) as (root, state):
        require(state['phase'] in ('learning', 'awaiting_reflect'), 'Reflect follows learning or memory commit')
        if state['round'] == 0:
            require({x['kind'] for x in state['learning']} == {'compiler', 'digital_flow'},
                    'Reflect0 needs compiler and digital-flow layout observations')
        key = 'reflect-' + str(state['round'])
        # Open request is immutable. New evidence requires an explicit new round, not silent prompt replacement.
        if key in state['requests']:
            require(read(state['requests'][key]['path']).get('reflect_contract') == REFLECT_CONTRACT,
                    'Saved request uses an earlier Reflect contract; use its pinned runtime or initialize a new run')
            return state['requests'][key]
        packet = context_data(root, state, 'reflect')
        packet.update(id=key, source='real_ai_reply_required', reflect_contract=REFLECT_CONTRACT,
                      allowed_sources=['ai', 'algorithm'],
                      self_proposal_required=True)
        packet['request_digest'] = identity(packet)
        path = root / 'requests' / (key + '.json')
        atomic(path, packet)
        artifact(root, state, key, path, 'reflect_request')
        state['requests'][key] = {'id': key, 'request_digest': packet['request_digest'], 'path': str(path)}
        state['phase'] = 'awaiting_reflect'
        event(state, 'reflect_request', state['requests'][key])
        return state['requests'][key]


def reflect(run, payload, response_path):
    with transaction(run) as (root, state):
        key = payload['request_id']
        require(read(response_path) == payload, 'Saved reply must match submitted payload')
        fingerprint = identity(payload)
        if key in state['submissions']:
            require(state['submissions'][key] == fingerprint, 'Conflicting Reflect retry')
            return status(state)
        require(state['phase'] == 'awaiting_reflect', 'Not awaiting Reflect')
        require(key == 'reflect-' + str(state['round']) and key in state['requests'], 'Wrong Reflect round')
        require(payload['request_digest'] == state['requests'][key]['request_digest'], 'Stale Reflect request')
        require(payload.get('author') == 'ai', 'Reflect requires an actual AI response')
        require(not set(payload) - {'request_id', 'request_digest', 'author', 'comparison',
                    'evidence', 'reflection', 'self_proposal', 'proposals', 'route_updates',
                    'decision', 'task'}, 'Unknown Reflect reply field')
        packet = read(state['requests'][key]['path'])
        require(packet.get('reflect_contract') == REFLECT_CONTRACT, 'Wrong Reflect contract')
        short(payload['comparison'], 'comparison', 1200)
        evidence(root, state, payload['evidence'])
        # Make the full visible AI reply part of immutable history before its short memory record.
        reply_id = key + '-reply'
        artifact(root, state, reply_id, response_path, 'reflect_reply')
        reflection = dict(payload['reflection'])
        reflection['evidence'] = list(dict.fromkeys(reflection['evidence'] + [reply_id]))
        entries = memory.validate(root, state, [reflection], reflection=True)
        new_routes = payload.get('proposals', [])
        require(isinstance(new_routes, list) and 1 <= len(new_routes) <= 6,
                'Every Reflect, including closure, needs a new AI self-proposal')
        require(all(isinstance(p, dict) for p in new_routes), 'Proposals must be objects')
        own_id = payload.get('self_proposal')
        require(isinstance(own_id, str) and any(p.get('id') == own_id for p in new_routes),
                'self_proposal must identify a newly submitted AI proposal')
        own = next(p for p in new_routes if p.get('id') == own_id)
        short(own.get('difference'), 'self-proposal difference')
        mechanism = short(own.get('mechanism'), 'self-proposal mechanism')
        normalized = ' '.join(mechanism.casefold().split())
        require(all(normalized != ' '.join(r['mechanism'].casefold().split())
                    for r in state['routes'].values()),
                'Self-proposal repeats an existing mechanism verbatim')
        for original_proposal in new_routes:
            proposal = dict(original_proposal)
            rid = proposal['id']
            require(re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,80}', rid) and rid not in state['routes'], 'Unique route ID required')
            require(proposal['source'] == 'ai',
                    'Reflect proposals must be AI-authored; algorithm routes come from planner.py')
            for field in ('mechanism', 'expected', 'minimal_test', 'stop'):
                short(proposal[field], field)
            evidence(root, state, proposal['evidence'])
            if 'plan_spec' in proposal:
                from planner import evaluate
                spec = proposal['plan_spec']
                evidence(root, state, [spec['search']])
                require(state['artifacts'][spec['search']]['kind'] == 'search', 'Plan must bind a search problem')
                base = read(root/state['artifacts'][spec['search']]['object'])['problem']
                n = len(base['blocks'])
                order, cuts, rotations = spec['order'], spec['cuts'], spec['rotations']
                require(sorted(order) == list(range(n)), 'Plan order must be a permutation')
                require(len(set(cuts)) == len(cuts) and all(type(c) is int and 0 < c < n for c in cuts), 'Invalid row cuts')
                require(len(rotations) == n and all(r in b.get('orientations',[0]) for r,b in zip(rotations,base['blocks'])), 'Invalid rotations')
                proposal['plan'] = evaluate(base,(tuple(order),tuple(sorted(cuts)),tuple(rotations)))
                require(proposal['plan']['feasible'], 'Proposed placement exceeds geometry contract')
            state['routes'][rid] = dict(proposal, lifecycle='active', round=state['round'], status='hypothesis')
        for rid, lifecycle in payload.get('route_updates', {}).items():
            require(rid in state['routes'] and lifecycle in ('active','deferred','refuted-in-scope','superseded'), 'Invalid route update')
            state['routes'][rid]['lifecycle'] = lifecycle
        # Explicit closure still commits a reflection.
        if payload['decision'] == 'close':
            state['phase'] = 'closed'
            state['task'] = None
        else:
            require(payload['decision'] == 'build', 'Reflect decision must be build or close')
            task = dict(payload['task'])
            require(task['route'] in state['routes'] and state['routes'][task['route']]['lifecycle'] == 'active'
                    and state['routes'][task['route']]['source'] in ('ai', 'algorithm'), 'Select an active AI/algorithm route')
            for field in ('module', 'stage', 'goal', 'stop'):
                short(task[field], field)
            require(task['module'] in {m['id'] for m in state['project']['modules'] if m['enabled']} | {'dcim'}, 'Unknown module')
            require(task.get('execution') == 'geometry_only', 'This runner supports geometry-only tasks; EDA adapter not installed')
            require(isinstance(task['checks'], list) and task['checks'], 'Task checks required')
            require(isinstance(task['learning_ids'], list) and task['learning_ids'], 'Builder must receive specific learned observations')
            require(set(task['learning_ids']) <= {x['id'] for x in state['learning']}, 'Unknown learning reference')
            require(type(task['max_candidates']) is int and 1 <= task['max_candidates'] <= 20, 'Bound candidate budget')
            task['round'] = state['round'] + 1
            task['id'] = 'task-' + str(task['round'])
            task['request'] = key
            state['round'] += 1
            state['task'] = task
            state['phase'] = 'awaiting_builder'
        state['memory'].extend(entries)
        state['submissions'][key] = fingerprint
        event(state, 'reflect_commit', {'reply': reply_id, 'self_proposal': own_id,
              'comparison': payload['comparison'], 'decision': payload['decision']})
        return dict(status(state), revision=state['revision'] + 1)


def result(run, payload, path):
    with transaction(run) as (root, state):
        token = 'result-' + str(payload['round'])
        require(read(path) == payload, 'Saved result must match submitted payload')
        fingerprint = identity(payload)
        if token in state['submissions']:
            require(state['submissions'][token] == fingerprint, 'Conflicting result retry')
            return status(state)
        require(state['phase'] == 'awaiting_builder' and state['round'] == payload['round'], 'Wrong Builder stage/round')
        require(payload['task_id'] == state['task']['id'], 'Wrong task')
        require(payload['outcome'] in ('passed','failed','incomplete'), 'Explicit outcome required')
        short(payload['summary'], 'summary')
        evidence(root, state, payload['evidence'])
        require(any(state['artifacts'][k]['kind'] == 'candidate' and state['artifacts'][k]['round'] == state['round']
                    for k in payload['evidence']) or payload['outcome'] == 'incomplete', 'Retain actual candidate before review')
        artifact(root, state, token, path, 'builder_result')
        state['submissions'][token] = fingerprint
        state['phase'] = 'awaiting_analyst'
        event(state, 'builder_result', {'id': token, 'outcome': payload['outcome']})
        return dict(status(state), revision=state['revision'] + 1)


def review(run, payload, path):
    with transaction(run) as (root, state):
        token = 'review-' + str(payload['round'])
        require(read(path) == payload, 'Saved review must match submitted payload')
        signature = identity(payload)
        if token in state['submissions']:
            require(state['submissions'][token] == signature, 'Conflicting review retry')
            return status(state)
        require(state['phase'] == 'awaiting_analyst' and state['round'] == payload['round'], 'Wrong Analyst stage/round')
        require(payload['result_id'] == 'result-' + str(state['round']), 'Review must bind this Builder result')
        evidence(root, state, payload['evidence'])
        require(payload['verdict'] in ('passed','failed','incomplete'), 'Explicit verdict required')
        short(payload['scope'], 'scope')
        short(payload['summary'], 'summary')
        require(isinstance(payload['checks'], dict) and set(state['task']['checks']) <= set(payload['checks']), 'Review all required checks')
        require(all(v in ('passed','failed','incomplete','not_run') for v in payload['checks'].values()), 'Invalid check status')
        if payload['verdict'] == 'passed':
            require(all(payload['checks'][k] == 'passed' for k in state['task']['checks']), 'Cannot pass missing checks')
        artifact(root, state, token, path, 'analyst_review')
        state['reviews'][str(state['round'])] = dict(payload, id=token)
        state['submissions'][token] = signature
        state['phase'] = 'awaiting_memory'
        event(state, 'analyst_review', {'id': token, 'verdict': payload['verdict']})
        return dict(status(state), revision=state['revision'] + 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    c = sub.add_parser('context')
    c.add_argument('--role', choices=('reflect','builder','analyst'), required=True)
    c.add_argument('--since')
    sub.add_parser('request')
    for name in ('reflect','result','review'):
        c = sub.add_parser(name)
        c.add_argument('--input', required=True)
    c = sub.add_parser('evidence')
    c.add_argument('--id', required=True)
    c.add_argument('--path', required=True)
    a = p.parse_args()
    if a.command == 'context':
        return context(a.run, a.role, a.since)
    if a.command == 'request':
        return request(a.run)
    if a.command in ('reflect','result','review'):
        return globals()[a.command](a.run, read(a.input), a.input)
    with transaction(a.run) as (root, state):
        if a.command == 'evidence':
            return artifact(root, state, a.id, a.path, 'evidence')
        return dict(status(state), learning_sources=sorted({x['kind'] for x in state['learning']}),
                    memory_records=len(state['memory']), routes=len(state['routes']), eda_launched=False)


if __name__ == '__main__':
    cli(main)
