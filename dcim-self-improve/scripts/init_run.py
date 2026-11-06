"""Initialize a process-neutral learning run with atomic publication."""
import argparse
from pathlib import Path
import re
import shutil
import tempfile
from dcim_config import load_config
from runtime import atomic, cli, identity
SKILL_ROOT = Path(__file__).resolve().parents[1]


def run_destination(settings, name):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', name):
        raise ValueError('Use a simple run name beginning with a letter')
    output = settings.ensure_output(settings.path('work_root') / name)
    if output.exists():
        raise FileExistsError('Run already exists: ' + str(output))
    return output


def initialize(config, name):
    settings = load_config(config)
    output = run_destination(settings, name)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.init-', dir=str(output.parent)) as temp:
        staged = Path(temp) / 'run'
        staged.mkdir()
        for name in ('objects', 'candidates', 'requests', 'instructions'):
            (staged / name).mkdir()
        shutil.copytree(SKILL_ROOT / 'scripts', staged / 'scripts',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(SKILL_ROOT / 'assets/tools', staged / 'assets/tools',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        instructions = {}
        for path in [SKILL_ROOT / 'SKILL.md', SKILL_ROOT.parent / 'AGENTS.md',
                     SKILL_ROOT.parent / 'HANDOFF.md', *sorted((SKILL_ROOT / 'references').glob('*.md'))]:
            shutil.copyfile(path, staged / 'instructions' / path.name)
            instructions[path.name] = identity(path.read_text(encoding='utf-8'))
        reflect_skill = SKILL_ROOT / 'roles/reflect/SKILL.md'
        shutil.copyfile(reflect_skill, staged / 'instructions/reflect-SKILL.md')
        instructions['reflect-SKILL.md'] = identity(reflect_skill.read_text(encoding='utf-8'))
        for name in ('AGENTS.md', 'HANDOFF.md'):
            path = SKILL_ROOT.parent.parent / name
            if path.is_file():
                saved_name = 'workspace-' + name
                shutil.copyfile(path, staged / 'instructions' / saved_name)
                instructions[saved_name] = identity(path.read_text(encoding='utf-8'))
        local = settings.rebased(output)
        local['work_root'] = '.'
        atomic(staged / 'config.json', local)
        atomic(staged / 'state.json', {
            'schema_version': 3, 'phase': 'learning', 'round': 0, 'revision': 0,
            'project': settings.project, 'config_identity': identity(local),
            'task': None, 'artifacts': {}, 'learning': [], 'memory': [],
            'routes': {}, 'requests': {}, 'submissions': {}, 'events': [],
            'instructions': instructions, 'context_receipts': {}, 'reviews': {},
        })
        staged.rename(output)
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config')
    p.add_argument('--name', required=True)
    a = p.parse_args()
    return {'run_root': str(initialize(a.config, a.name)), 'phase': 'learning', 'eda_launched': False}


if __name__ == '__main__':
    cli(main)
