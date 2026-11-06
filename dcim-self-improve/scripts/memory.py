"""One bounded format for actions, experience and reflections; revision-aware reads."""
import argparse
from runtime import cli, event, evidence, identity, read, require, transaction

TEXT_FIELDS = ('condition', 'operation', 'observation', 'next_test')
MAX_RECORDS = 6
MAX_TEXT = 240
FIELDS = {'type', 'stage', 'module', 'route', 'scope', 'technology', 'status',
          'evidence', 'supersedes', *TEXT_FIELDS}


def validate(root, state, entries, reflection=False):
    require(isinstance(entries, list) and len(entries) <= MAX_RECORDS, 'At most six concise records')
    prepared = []
    known = {entry['id']: entry for entry in state['memory']}
    revised = set()
    for original in entries:
        entry = dict(original)
        require(not set(entry) - FIELDS, 'Unknown memory field')
        require(entry.get('type') in (('reflection',) if reflection else ('action', 'experience')),
                'Wrong memory type for this stage')
        for key in (*TEXT_FIELDS, 'stage', 'module', 'route'):
            require(isinstance(entry.get(key), str) and 0 < len(entry[key]) <= MAX_TEXT,
                    'Missing or oversized memory field: ' + key)
        require(entry.get('scope') in ('general', 'process'), 'Memory scope must be general or process')
        require(entry.get('status') in ('supported', 'uncertain', 'refuted'), 'Invalid evidence status')
        if entry['type'] == 'action':
            require(entry['status'] == 'supported', 'Actions must be supported in the reviewed scope')
        if entry['scope'] == 'process':
            require(entry.get('technology') == state['project']['technology'] and
                    all(entry['technology'].values()), 'Process memory needs exact declared technology')
        else:
            require(not entry.get('technology'), 'General memory cannot smuggle process applicability')
        evidence(root, state, entry.get('evidence'))
        require(len(entry['evidence']) <= 8, 'At most eight evidence references')
        previous = entry.get('supersedes')
        if previous:
            require(previous in known and previous not in revised, 'Unknown or repeated supersession')
            require(all(known[previous][k] == entry[k] for k in ('type', 'stage', 'module', 'scope')),
                    'Correction must keep its knowledge scope')
            revised.add(previous)
        review = state['reviews'].get(str(state['round']))
        entry.update(round=state['round'], review=review['id'] if review else None)
        route=state['routes'].get(entry['route'],{})
        if route.get('search'):
            entry['search_context']={'artifact':route['search'],'baseline':route.get('baseline')}
        if entry['type'] == 'action':
            require(review and review['verdict'] == 'passed',
                    'Successful actions require a passed Analyst review')
        entry['id'] = 'm-' + identity(entry)[:20]
        require(entry['id'] not in known, 'Duplicate memory record')
        known[entry['id']] = entry
        prepared.append(entry)
    return prepared


def select(state, stage=None, module=None, route=None, limit=8):
    require(type(limit) is int and 1 <= limit <= 20, 'Memory read limit must be 1..20')
    superseded = {e.get('supersedes') for e in state['memory']}
    result = []
    for entry in reversed(state['memory']):
        if entry['id'] in superseded:
            continue
        if any(value and entry[key] != value for key, value in
               (('stage', stage), ('module', module), ('route', route))):
            continue
        if entry['scope'] == 'process' and entry['technology'] != state['project']['technology']:
            continue
        route_info = state['routes'].get(entry['route'], {})
        if not route and route_info.get('lifecycle', 'active') != 'active':
            continue
        result.append(entry)
        if len(result) == limit:
            break
    return result


def commit(run, payload):
    with transaction(run) as (root, state):
        token = 'memory:' + str(payload['round'])
        signature = identity(payload)
        if token in state['submissions']:
            require(state['submissions'][token] == signature, 'Conflicting memory retry')
            return {'already_committed': True}
        require(state['phase'] == 'awaiting_memory' and payload['round'] == state['round'],
                'Memory must follow this round Analyst review')
        require(payload.get('disposition') in ('new', 'revised', 'no_new'), 'Explicit disposition required')
        entries = validate(root, state, payload['entries'])
        require(bool(entries) == (payload['disposition'] != 'no_new'), 'Disposition and entries disagree')
        state['memory'].extend(entries)
        state['submissions'][token] = signature
        state['phase'] = 'awaiting_reflect'
        event(state, 'memory_commit', {'disposition': payload['disposition'], 'ids': [e['id'] for e in entries]})
        return {'phase': state['phase'], 'ids': [e['id'] for e in entries]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('read')
    for key in ('stage', 'module', 'route'):
        c.add_argument('--' + key)
    c.add_argument('--limit', type=int, default=8)
    c = sub.add_parser('commit')
    c.add_argument('--input', required=True)
    a = p.parse_args()
    if a.command == 'commit':
        return commit(a.run, read(a.input))
    with transaction(a.run) as (_, state):
        return select(state, a.stage, a.module, a.route, a.limit)


if __name__ == '__main__':
    cli(main)
