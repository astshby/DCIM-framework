"""Typed placement relations and exact, evidence-bound native seams.

These are conditional geometric screens. A captured seam report must be verified
against run-owned immutable evidence by verify_contract_evidence at runtime; this
module does not parse foundry decks or certify mask/body correctness by itself.
"""
import math
import re
from runtime import evidence, read, require

SCHEMA = 'block-physical-contract-v1'
CERTIFICATE_SCHEMA = 'native-seam-evidence-v1'
CHECKS = {'seam_geometry', 'source_connectivity', 'body_supply'}
TOL = 1e-8


def fields(value, required, name, optional=()):
    require(isinstance(value, dict), name+' must be an object')
    require(set(required)<=set(value) and not set(value)-set(required)-set(optional),
            'Missing or unsupported '+name+' fields')


def finite(value, name, positive=False):
    require(type(value) in (int,float) and math.isfinite(value) and
            (value>0 if positive else True),'Invalid '+name)
    return value


def text(value, name):
    require(isinstance(value,str) and value.strip() and len(value)<=240,'Invalid '+name)
    return value


def rectangle(value, name):
    require(isinstance(value,list) and len(value)==4,'Invalid '+name)
    for v in value: finite(v,name)
    require(value[0]>=0 and value[1]>=0 and value[2]>value[0] and value[3]>value[1],
            'Invalid '+name+' bounds')
    return value


def binding(value):
    fields(value,('artifact','sha256'),'evidence binding')
    text(value['artifact'],'evidence artifact')
    require(isinstance(value['sha256'],str) and re.fullmatch(r'[0-9a-f]{64}',value['sha256']),
            'Evidence requires a lowercase SHA256')


def anchors(value, ids):
    require(isinstance(value,list) and value,'Explicit anchors required')
    known=[]
    for a in value:
        fields(a,('id','at'),'anchor')
        require(a['id'] in ids and a['at'] in ('min','center','max'),'Unknown anchor')
        known.append((a['id'],a['at']))
    require(len(set(known))==len(known),'Duplicate anchors')


def validate_contract(problem):
    contract=problem.get('physical_contract')
    if contract is None: return None
    fields(contract,('schema','boundaries','alignments','tracks','repetitions','regions'),'physical contract',('seam_options',))
    require(contract['schema']==SCHEMA,'Unsupported physical contract schema')
    blocks={b['id']:b for b in problem['blocks']};ids=set(blocks)
    require(isinstance(contract['boundaries'],list) and len(contract['boundaries'])==len(ids),
            'Declare one placement boundary per block')
    seen=[]
    for b in contract['boundaries']:
        fields(b,('id','rect_um'),'placement boundary')
        require(b['id'] in ids,'Unknown boundary block')
        seen.append(b['id']);box=rectangle(b['rect_um'],'placement boundary')
        require(box[2]<=blocks[b['id']]['width_um'] and box[3]<=blocks[b['id']]['height_um'],
                'Placement boundary must lie inside retained full-mask envelope')
    require(len(set(seen))==len(ids),'Duplicate placement boundary')
    for name in ('alignments','tracks','repetitions','regions'):
        require(isinstance(contract[name],list) and len(contract[name])<=256,'Bounded '+name+' list required')
    for a in contract['alignments']:
        fields(a,('axis','anchors'),'alignment')
        require(a['axis'] in ('x','y'),'Unknown alignment axis')
        anchors(a['anchors'],ids);require(len(a['anchors'])>=2,'Alignment requires at least two anchors')
    for t in contract['tracks']:
        fields(t,('axis','pitch_um','offset_um','anchors'),'track relation')
        require(t['axis'] in ('x','y'),'Unknown track axis')
        finite(t['pitch_um'],'track pitch',True);finite(t['offset_um'],'track offset')
        require(0<=t['offset_um']<t['pitch_um'],'Track offset must be within pitch')
        anchors(t['anchors'],ids)
    require(isinstance(contract.get('seam_options',[]),list) and len(contract.get('seam_options',[]))<=256,'Bound finite native seam alternatives')
    require(len({tuple(sorted((r['first'],r['second']))) for r in contract['repetitions']})==len(contract['repetitions']),'Duplicate native pair')
    pairs=[]
    for r in contract['repetitions']+contract.get('seam_options',[]):
        fields(r,('first','second','delta_um','rotations','evidence'),'native repetition')
        require(r['first'] in ids and r['second'] in ids and r['first']!=r['second'],'Unknown native pair')
        pair=(r['first'],r['second'],tuple(r['delta_um']) if isinstance(r['delta_um'],list) else ());pairs.append(pair)
        require(isinstance(r['delta_um'],list) and len(r['delta_um'])==2,'Explicit native displacement required')
        for v in r['delta_um']:finite(v,'native displacement')
        require(isinstance(r['rotations'],list) and len(r['rotations'])==2,'Explicit native orientations required')
        for i,key in enumerate(('first','second')):
            angle=r['rotations'][i]
            require(type(angle) is int and angle in blocks[r[key]].get('orientations',[0]),
                    'Native seam uses an unsupported orientation')
        binding(r['evidence'])
    require(len(set(pairs))==len(pairs),'Duplicate native pair')
    regions=[]
    for region in contract['regions']:
        fields(region,('id','rect_um','members'),'region')
        text(region['id'],'region ID');regions.append(region['id']);rectangle(region['rect_um'],'region')
        members=region['members']
        require(isinstance(members,list) and members and len(set(members))==len(members) and set(members)<=ids,
                'Unknown or duplicate region members')
    require(len(set(regions))==len(regions),'Duplicate region IDs')
    return contract


def transformed_boundary(block, placement, rectangle_um):
    x0,y0,x1,y1=rectangle_um
    if placement['rotation_deg']==90:
        x0,y0,x1,y1=block['height_um']-y1,x0,block['height_um']-y0,x1
    return [placement['x_um']+x0,placement['y_um']+y0,
            placement['x_um']+x1,placement['y_um']+y1]


def touching(a,b):
    horizontal=(abs(a[2]-b[0])<=TOL or abs(b[2]-a[0])<=TOL) and min(a[3],b[3])-max(a[1],b[1])>TOL
    vertical=(abs(a[3]-b[1])<=TOL or abs(b[3]-a[1])<=TOL) and min(a[2],b[2])-max(a[0],b[0])>TOL
    return horizontal or vertical


def _anchor(rect,axis,at):
    i=0 if axis=='x' else 1
    return rect[i] if at=='min' else rect[i+2] if at=='max' else (rect[i]+rect[i+2])/2


def evaluate_contract(problem, placements):
    """Return violated relations and conditionally permitted exact seam pairs."""
    c=validate_contract(problem)
    if c is None: return {'violations':[],'seam_pairs':set(),'placement_boundaries':{},'evidence':[]}
    blocks={b['id']:b for b in problem['blocks']};placed={p['id']:p for p in placements}
    boxes={b['id']:transformed_boundary(blocks[b['id']],placed[b['id']],b['rect_um']) for b in c['boundaries']}
    violations=[];pairs=set()
    for index,a in enumerate(c['alignments']):
        values=[_anchor(boxes[v['id']],a['axis'],v['at']) for v in a['anchors']]
        if max(values)-min(values)>TOL:violations.append('alignment:'+str(index))
    for index,t in enumerate(c['tracks']):
        values=[(_anchor(boxes[v['id']],t['axis'],v['at'])-t['offset_um'])/t['pitch_um'] for v in t['anchors']]
        if any(abs(v-round(v))>TOL for v in values):violations.append('track:'+str(index))
    for index,r in enumerate(c['repetitions']):
        a,b=placed[r['first']],placed[r['second']]
        exact=(a['rotation_deg']==r['rotations'][0] and b['rotation_deg']==r['rotations'][1] and
               abs(b['x_um']-a['x_um']-r['delta_um'][0])<=TOL and
               abs(b['y_um']-a['y_um']-r['delta_um'][1])<=TOL)
        if not exact:violations.append('native_pitch:'+str(index))
        elif not touching(boxes[r['first']],boxes[r['second']]):violations.append('native_boundary:'+str(index))
        else:pairs.add(frozenset((r['first'],r['second'])))
    for index,r in enumerate(c.get('seam_options',[])):
        a,b=placed[r['first']],placed[r['second']]
        exact=(a['rotation_deg']==r['rotations'][0] and b['rotation_deg']==r['rotations'][1] and
               abs(b['x_um']-a['x_um']-r['delta_um'][0])<=TOL and
               abs(b['y_um']-a['y_um']-r['delta_um'][1])<=TOL)
        if exact and touching(boxes[r['first']],boxes[r['second']]):
            pairs.add(frozenset((r['first'],r['second'])))
    for region in c['regions']:
        x0,y0,x1,y1=region['rect_um']
        for key in region['members']:
            # Region containment uses retained masks, never just the smaller placement boundary.
            p=placed[key]
            if not (p['x_um']>=x0-TOL and p['y_um']>=y0-TOL and
                    p['x_um']+p['width_um']<=x1+TOL and p['y_um']+p['height_um']<=y1+TOL):
                violations.append('region:'+region['id']+':'+key)
    return {'violations':violations,'seam_pairs':pairs,'placement_boundaries':boxes,
            'evidence':[r['evidence'] for r in c['repetitions']+c.get('seam_options',[])]}


def master(problem, block_id, sha256):
    b=next(b for b in problem['blocks'] if b['id']==block_id)
    c=problem['physical_contract'];box=next(x['rect_um'] for x in c['boundaries'] if x['id']==block_id)
    return {'source':b['source'],'source_sha256':sha256,'cell':b['cell'],
            'width_um':b['width_um'],'height_um':b['height_um'],'placement_boundary_um':box}


def verify_contract_evidence(root,state,problem,allow_construction=False):
    """Bind exact seam reports to immutable sources and dependency objects.

    Captured report check names are required and scoped; actual report parsing and
    scientific independence remain Analyst duties. No signoff is inferred here.
    """
    c=validate_contract(problem)
    if c is None:return []
    bindings=[]
    for r in c['repetitions']+c.get('seam_options',[]):
        key=r['evidence']['artifact'];evidence(root,state,[key]);item=state['artifacts'][key]
        require(item['kind']=='evidence' and item['sha256']==r['evidence']['sha256'],
                'Native seam certificate identity differs')
        certificate=read(root/item['object'])
        conditional=certificate.get('schema')=='native-seam-construction-v1'
        if r in c.get('seam_options',[]):
            require(conditional,'Finite construction seam options cannot substitute accepted seam certificates')
        fields(certificate,('schema','scope','masters','delta_um','rotations','checks','dependencies'),'native seam certificate',
               ('required_postchecks',) if conditional else ())
        if conditional:
            require(allow_construction and r in c.get('seam_options',[]),
                    'Conditional native seam requires an opted-in bounded physical construction')
            require(certificate['scope']=='exact_pair_construction' and
                    certificate['checks']=={'seam_geometry':'passed','source_connectivity':'passed','body_supply':'unknown'},
                    'Conditional seam cannot claim body or accepted qualification')
            require(isinstance(certificate.get('required_postchecks'),list) and
                    {'drc','source_lvs','erc','power_body','pp_np_seams'}<=set(certificate['required_postchecks']),
                    'Conditional seam requires full seam/body postchecks')
        else:
            require(certificate['schema']==CERTIFICATE_SCHEMA and certificate['scope']=='exact_pair_transform',
                    'Unsupported native seam certificate scope')
        require(certificate['delta_um']==r['delta_um'] and certificate['rotations']==r['rotations'],
                'Native seam certificate transform differs')
        require(isinstance(certificate['masters'],list) and len(certificate['masters'])==2,
                'Native seam needs two exact source masters')
        expected=[]
        for name in ('first','second'):
            b=next(b for b in problem['blocks'] if b['id']==r[name]);source=b['source']
            evidence(root,state,[source]);expected.append(master(problem,b['id'],state['artifacts'][source]['sha256']))
        require(certificate['masters']==expected,'Native seam source/placement boundary differs')
        if not conditional:
            require(isinstance(certificate['checks'],dict) and set(certificate['checks'])==CHECKS and
                    all(v=='passed' for v in certificate['checks'].values()),'Native seam checks are missing or incomplete')
        dependencies=certificate['dependencies']
        require(isinstance(dependencies,list) and dependencies,'Native seam needs supporting report dependencies')
        seen=[]
        for dep in dependencies:
            binding(dep);dkey=dep['artifact'];seen.append(dkey)
            require(dkey!=key and dkey not in [x['source'] for x in expected],
                    'Supporting evidence must be distinct from certificate and geometry sources')
            evidence(root,state,[dkey]);d=state['artifacts'][dkey]
            require(d['kind']=='evidence' and d['sha256']==dep['sha256'],
                    'Native seam supporting report differs')
        require(len(set(seen))==len(seen),'Duplicate supporting evidence')
        bindings.append({'artifact':key,'sha256':item['sha256'],'scope':certificate['scope'],
                         'dependencies':dependencies,
                          'required_postchecks':certificate.get('required_postchecks',[]),
                          'qualification':'construction_only_body_unknown' if conditional else 'source_bound_native_evidence'})
    return bindings
