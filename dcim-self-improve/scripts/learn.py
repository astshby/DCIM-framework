"""Reflect0: extract geometry observations from compiler and digital-flow layouts."""
import argparse
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'assets/tools'))
from geometry import bbox, capture_closure, hierarchy_counts, read_gds, topo_order
from runtime import artifact, cli, event, identity, read, require, transaction
from dcim_config import digest

KINDS = ("compiler", "digital_flow", "circuit", "native_device", "composition", "standard_cell")


def inspect_layout(path, top):
    path = Path(path)
    cells = (read(path)['cells'] if path.suffix.lower() == '.json'
             else capture_closure(read_gds(path), [top]))
    order = topo_order(cells, top)
    envelope = bbox(cells, top)
    require(envelope and envelope[2] > envelope[0] and envelope[3] > envelope[1], 'Nonempty layout required')
    blocks = []
    for name in order:
        box = bbox(cells, name)
        if box is not None:
            blocks.append({'cell': name, 'width_um': box[2] - box[0], 'height_um': box[3] - box[1],
                           'references': len(cells[name]['references']),
                           'pins': [l['text'] for l in cells[name]['labels']]})
    layers = Counter(str((p['layer'], p['datatype'])) for c in cells.values() for p in c['polygons'])
    return {'top': top, 'bbox_um': envelope, 'blocks': blocks,
            'hierarchy_counts': hierarchy_counts(cells, top), 'polygon_counts': dict(layers),
            'placements': cells[top]['references'],
            'interpretation': 'geometry observations; connectivity, DRC and electrical qualification not inferred'}


def learn(run, kind, layout, top, context, sources=None):
    require(kind in KINDS, "Unknown learning source")
    sources = dict(sources or {})
    require(set(sources) <= {"circuit", "metadata", "rules"}, "Unknown reference dependency role")
    context = dict(context)
    if kind not in ("compiler", "digital_flow"):
        for key in ("purpose", "observation"):
            require(isinstance(context.get(key), str) and context[key].strip(), "Reference context needs " + key)
    context.setdefault("purpose", "implementation")
    require(context["purpose"] in ("implementation", "organization_only", "circuit_intent"), "Invalid reference purpose")
    if kind in ("circuit", "native_device"):
        require("circuit" in sources, "Independent circuit source required")
    require(layout is not None or kind == "circuit", "Layout required for geometry reference")
    for key in ('module', 'process', 'release', 'stack', 'source_run'):
        require(isinstance(context.get(key), str) and context[key], 'Source context needs ' + key)
    require(isinstance(top, str) and top.strip(), 'Exact source top required')
    files = dict(sources)
    if layout is not None:
        files['layout'] = layout
    hashes = {role: digest(Path(path)) for role, path in files.items()}
    observations = (inspect_layout(layout, top) if layout is not None else
                    {'top': top, 'declared_observation': context['observation'],
                     'interpretation': 'source capture only; circuit parsing and validation not performed'})
    require(all(digest(Path(path)) == hashes[role] for role, path in files.items()),
            'Reference changed during inspection')
    with transaction(run) as (root, state):
        require('reflect-' + str(state['round']) not in state['requests'],
                'Finish the saved Reflect request before adding new learning/search evidence')
        require(state['phase'] in ('learning', 'awaiting_reflect'), 'Learn before Reflect dispatch')
        require(context['module'] in {m['id'] for m in state['project']['modules'] if m['enabled']} | {'dcim'}, 'Unknown learning module')
        for key in ('process', 'release', 'stack'):
            declared = state['project']['technology'][key]
            require(context['purpose'] == 'organization_only' or not declared or declared == context[key],
                    'Reference technology mismatch: ' + key)
        name = 'learn-' + identity({'hashes': hashes, 'top': top, 'context': context, 'kind': kind})[:18]
        if any(item['id'] == name for item in state['learning']):
            return next(item for item in state['learning'] if item['id'] == name)
        captured = {}
        for role, source in files.items():
            key = name if role == 'layout' else name+'-'+role
            artifact(root, state, key, source, 'reference_layout' if role == 'layout' else 'reference_source')
            require(state['artifacts'][key]['sha256'] == hashes[role], 'Reference changed during inspection')
            captured[role] = {'artifact': key, 'sha256': hashes[role]}
        if layout is None:
            # A circuit-only learning ID aliases its captured independent netlist.
            state['artifacts'][name] = dict(state['artifacts'][captured['circuit']['artifact']])
        result = {'id': name, 'kind': kind, 'context': context, 'observations': observations,
                  'evidence': list(dict.fromkeys([name] + [v['artifact'] for v in captured.values()])),
                  'sources': captured, 'status': 'observed_reference'}
        state['learning'].append(result)
        event(state, 'learn', {'id': name, 'kind': kind})
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    p.add_argument('--kind', choices=KINDS, required=True)
    p.add_argument('--layout')
    p.add_argument('--sources', help='JSON mapping circuit/metadata/rules to authorized files')
    p.add_argument('--top', required=True)
    p.add_argument('--context', required=True, help='JSON with module/process/release/stack/source_run')
    a = p.parse_args()
    return learn(a.run, a.kind, a.layout, a.top, read(a.context), read(a.sources) if a.sources else None)


if __name__ == '__main__':
    cli(main)
