"""One role/reference registry and a read-only initialization context."""
import argparse
from pathlib import Path
from dcim_config import load_config
from project_config import open_items
from runtime import cli, require

REFERENCES = {role: role+'.md' for role in ('initialize','reflect','builder','analyst')}


def names(role):
    require(role in REFERENCES,'Unknown role')
    return ['AGENTS.md','SKILL.md',REFERENCES[role]]


def instructions(root, role):
    result={}
    for name in names(role):
        path=root/'instructions'/name
        require(path.is_file(),'Missing pinned role instruction: '+name)
        result[name]=path.read_text(encoding='utf-8')
    return result


def initialization(config):
    settings=load_config(config)
    skill=Path(__file__).resolve().parents[1]
    guide=skill/('instructions' if (skill/'instructions').is_dir() else 'references')/'initialize.md'
    result={'role':'initialize','project':settings.project,'open_items':open_items(settings.project),
            'reference':str(guide),'eda_launched':False,
            'instructions':guide.read_text(encoding='utf-8'),
            'memory_order':'newest applicable first; no previous-run claims imported automatically'}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True)
    return initialization(p.parse_args().config)


if __name__=='__main__':
    cli(main)
