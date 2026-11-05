"""Run transactions, immutable artifact copies and compact status."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
from dcim_config import digest, is_within, load_config


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def identity(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def atomic(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run_root(run):
    root = Path(run).resolve()
    settings = load_config(root / 'config.json')
    require(settings.path('work_root') == root, 'Use an initialized run')
    settings.ensure_output(root / 'state.json')
    return root


@contextmanager
def transaction(run):
    root = run_root(run)
    with (root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = read(root / 'state.json')
        require(identity(read(root / 'config.json')) == state['config_identity'],
                'Configuration changed; initialize a new run for changed conditions')
        before = identity(state)
        yield root, state
        if identity(state) != before:
            state['revision'] += 1
            atomic(root / 'state.json', state)


def store(root, path):
    path = Path(path).resolve(strict=True)
    require(path.is_file(), 'Artifact must be a regular file')
    fingerprint = digest(path)
    target = root / 'objects' / fingerprint
    if not target.exists():
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == fingerprint, 'Source changed during snapshot')
        with target.open('xb') as stream:
            stream.write(data)
    require(digest(target) == fingerprint and digest(path) == fingerprint,
            'Artifact changed during snapshot')
    return {'sha256': fingerprint, 'source': str(path), 'object': str(target.relative_to(root))}


def artifact(root, state, name, path, kind):
    require(name not in state['artifacts'], 'Artifact ID already exists')
    item = dict(store(root, path), kind=kind, round=state['round'])
    state['artifacts'][name] = item
    return item


def evidence(root, state, ids):
    require(isinstance(ids, list) and ids, 'Evidence references required')
    for key in ids:
        require(key in state['artifacts'], 'Unknown evidence: ' + str(key))
        item = state['artifacts'][key]
        path = root / item['object']
        require(is_within(path.resolve(), root / 'objects') and digest(path) == item['sha256'],
                'Changed evidence: ' + key)


def event(state, operation, payload):
    state['events'].append({'at': datetime.now(timezone.utc).isoformat(),
                            'round': state['round'], 'operation': operation, 'payload': payload})


def status(state):
    return {key: state[key] for key in ('phase', 'round', 'revision', 'task')}


def cli(function):
    try:
        print(encoded(function()).decode('utf-8'), end='')
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit('error: ' + str(error))
