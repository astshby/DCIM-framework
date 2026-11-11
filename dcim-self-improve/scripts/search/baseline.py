"""Bind search to actual, reviewed output of the immediately preceding round."""
from pathlib import Path
import sys
from runtime import evidence, read, require
from .model import dimensions, state_from_placements
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'assets/tools'))
from geometry import bbox, transform


def measured_placements(problem, layout):
    """Recover positions from generated references and child geometry, not the plan."""
    cells=layout['cells']
    top=cells[layout['top']]
    require(not top['polygons'] and not top['labels'], 'Unexpected top-level geometry')
    refs={r['instance_id']:r for r in top['references']}
    require(len(refs)==len(top['references']) and set(refs)=={b['id'] for b in problem['blocks']},
            'Actual layout instance identities differ')
    placements=[]
    for b in problem['blocks']:
        r=refs[b['id']]
        require(r['child']==b['source']+'__'+b['cell'] and not r.get('x_reflection') and
                r.get('columns',1)==1 and r.get('rows',1)==1, 'Actual instance/master transform differs')
        angle=r.get('rotation_deg',0)
        box=bbox(cells,r['child'])
        require(abs(box[2]-box[0]-b['width_um'])<1e-8 and abs(box[3]-box[1]-b['height_um'])<1e-8,
                'Actual child dimensions differ from reference')
        points=[transform(p,angle) for p in ((box[0],box[1]),(box[0],box[3]),(box[2],box[1]),(box[2],box[3]))]
        w,h=dimensions(b,angle)
        placements.append(dict(id=b['id'],source=b['source'],cell=b['cell'],
            x_um=r['origin_um'][0]+min(p[0] for p in points),
            y_um=r['origin_um'][1]+min(p[1] for p in points),rotation_deg=angle,width_um=w,height_um=h))
    state_from_placements(problem,placements)
    return placements


def previous(root, state, requested=None):
    require(state['round'] > 0, 'Reflect0 has references, not a previous Builder round')
    current=state.get('last_result',{})
    require(current.get('round')==state['round'] and str(state['round']) in state['reviews'],
            'Previous round needs a result and Analyst review')
    candidate=requested or current.get('baseline_candidate')
    require(candidate, 'Previous round has no layout baseline; repair its output, never fall back to older rounds')
    review=state['reviews'][str(state['round'])]
    require(candidate in current['evidence'] and candidate in review['evidence'],
            'Baseline must be retained in previous result and review evidence')
    evidence(root,state,[candidate])
    item=state['artifacts'][candidate]
    require(item['kind']=='candidate' and item['round']==state['round'], 'Baseline must come from the immediately previous round')
    manifest=read(root/item['object'])
    files=manifest['files']
    if manifest.get('physical_outputs'):
        require(manifest.get('physical_hierarchy')=='physical-hierarchy-consumer-v1',
                'Physical construction has no declared search decoder; close/review it and initialize an explicitly linked physical task, never fall back to reference boxes')
        from physical_scope import previous as previous_physical
        return previous_physical(root,state,candidate,manifest,review)
    if 'transistor-layout.json' in files:
        from device_flow import previous_devices
        return previous_devices(root,state,candidate,files,review)
    require('placement_state.json' in files and 'layout.json' in files, 'Previous candidate has no usable placement output')
    evidence(root,state,[files['placement_state.json'],files['layout.json']])
    snapshot=read(root/state['artifacts'][files['placement_state.json']]['object'])
    require(snapshot['round']==state['round'] and snapshot['candidate']==candidate, 'Baseline snapshot round/identity differs')
    from physical_contract import verify_contract_evidence
    verify_contract_evidence(root,state,snapshot['problem'])
    actual=measured_placements(snapshot['problem'],read(root/state['artifacts'][files['layout.json']]['object']))
    actual_state=state_from_placements(snapshot['problem'],actual)
    saved_state=state_from_placements(snapshot['problem'],snapshot['placements'])
    require(actual_state==saved_state,'Saved placement state differs from actual layout')
    if 'hierarchy_state.json' in files:
        evidence(root,state,[files['hierarchy_state.json']])
        from hierarchy import flatten
        tree=read(root/state['artifacts'][files['hierarchy_state.json']]['object'])
        require(state_from_placements(snapshot['problem'],flatten(tree,snapshot['problem']))==actual_state, 'Retained hierarchy differs from actual leaf geometry')
        snapshot=dict(snapshot,hierarchy=tree,hierarchy_artifact=files['hierarchy_state.json'])
    return snapshot,{'candidate':candidate,'round':state['round'],'artifact':files['placement_state.json'],
                     'layout':files['layout.json'],'sha256':state['artifacts'][files['placement_state.json']]['sha256'],
                     'review':review['id'],'verdict':review['verdict'],'qualification':review['scope']}
