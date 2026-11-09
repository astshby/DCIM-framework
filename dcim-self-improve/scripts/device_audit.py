"""Independent abstract-output audit; never imports the search/generation evaluator."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def audit(spec, layout, netlist, rules):
    issues={'device_identity':[], 'terminal_mapping':[], 'abstract_geometry':[]}
    def check(condition,group,message):
        if not condition: issues[group].append(message)
    try:
        p=spec['problem']; grid=p['rules']['grid_um']
        expected_net={k:p[k] for k in ('technology','devices','ports')}
        expected_net['schema']='transistor-netlist-v1'
        expected_rules={k:p[k] for k in ('technology','rows','rules','obstacles','reserved_access')}
        expected_rules['schema']='transistor-rules-v1'
        check(netlist==expected_net,'device_identity','Captured netlist differs from execution input')
        check(rules==expected_rules,'abstract_geometry','Captured rules differ from execution input')
        check(layout['schema']=='transistor-abstract-layout-v1' and layout['routing']=='not_generated',
              'abstract_geometry','Wrong output representation')
        check(layout['state']==spec['state'],'abstract_geometry','Executed state differs from selected state')
        expected_fields={'schema','problem_identity','netlist_signature','state','rows','placements','seams',
                         'ports','obstacles','reserved_access','metrics','routing','qualification'}
        check(set(layout)==expected_fields,'abstract_geometry','Unexpected or missing output contract fields')
        for key in ('rows','ports','obstacles','reserved_access'):
            check(layout[key]==p[key],'abstract_geometry','Emitted '+key+' differs from captured contract')
        check(layout['qualification']=='abstract_placement_only','abstract_geometry','Wrong qualification')
        def digest(value):
            return hashlib.sha256((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')).hexdigest()
        check(layout['problem_identity']==digest(p),'device_identity','Problem identity differs')
        signature=digest([{'id':d['id'],'kind':d['kind'],'model':d['model'],
            'width_grid_units':int(round(d['width_um']/grid)),
            'height_grid_units':int(round(d['height_um']/grid)),'terminals':d['terminals']}
            for d in sorted(netlist['devices'],key=lambda x:x['id'])])
        check(layout['netlist_signature']==signature and layout['metrics']['netlist_signature']==signature,
              'device_identity','Circuit signature differs')
        devices={d['id']:d for d in netlist['devices']}
        actual={d['id']:d for d in layout['placements']}
        check(len(actual)==len(layout['placements'])==len(devices) and set(actual)==set(devices),
              'device_identity','Missing, duplicate or extra device')
        rows={r['id']:r for r in rules['rows']}
        order={r['id']:r['order'] for r in layout['state']['rows']}
        check(set(order)==set(rows),'abstract_geometry','Row population differs')
        check(set(layout['state']['flips'])<=set(devices),'terminal_mapping','Unknown flipped device')
        flips=set(layout['state']['flips'])
        width=0; height=max(r['y_um']+r['height_um'] for r in rows.values())
        equal=lambda a,b: type(a) in (int,float) and math.isfinite(a) and abs(a-b)<=1e-8
        for did,d in devices.items():
            a=actual[did];row=rows[d['row']]
            check(all(a[k]==d[k] for k in ('row','kind','model','width_um','height_um')),
                  'device_identity','Device properties changed: '+did)
            check(a['kind']==row['kind'] and d['terminals']['b']==row['body_net'],
                  'terminal_mapping','Row/body mismatch: '+did)
            check(a['sd_flipped']==(did in flips) and (did not in flips or d['sd_swap']),
                  'terminal_mapping','Illegal S/D flip: '+did)
            check(set(a['terminals'])=={'s','d','g','b'} and
                  all(a['terminals'][t]['net']==d['terminals'][t] for t in d['terminals']),
                  'terminal_mapping','Terminal identity changed: '+did)
            x,y,w,h=a['x_um'],a['y_um'],a['width_um'],a['height_um']
            check(equal(y,row['y_um']) and h<=row['height_um'] and x>=0 and y>=0 and
                  all(equal(z/grid,round(z/grid)) for z in (x,y,w,h)),
                  'abstract_geometry','Off-row/grid or oversized device: '+did)
            left,right=('d','s') if a['sd_flipped'] else ('s','d')
            points={left:(x,y+h/2),right:(x+w,y+h/2),'g':(x+w/2,y+h),'b':(x+w/2,y)}
            for t,(px,py) in points.items():
                check(equal(a['terminals'][t]['x_um'],px) and equal(a['terminals'][t]['y_um'],py),
                      'terminal_mapping','Nominal terminal anchor changed: '+did+':'+t)
            width=max(width,x+w)
        seen=[];seams=[]
        for rowid,ids in order.items():
            cursor=0; previous=None
            for did in ids:
                seen.append(did);d=devices[did];a=actual[did]
                check(d['row']==rowid,'abstract_geometry','Device in wrong ordered row')
                shared=False
                if previous is not None:
                    prev=devices[previous]
                    right='s' if previous in flips else 'd';left='d' if did in flips else 's'
                    shared=bool(rules['rules']['allow_diffusion_sharing'] and d['share_group'] is not None and
                        prev['share_group']==d['share_group'] and prev['model']==d['model'] and
                        prev['kind']==d['kind'] and prev['height_um']==d['height_um'] and
                        prev['terminals']['b']==d['terminals']['b'] and prev['terminals'][right]==d['terminals'][left])
                    gap=0 if shared else rules['rules']['diffusion_gap_um']
                    cursor+=gap
                    seams.append((previous,did,shared,gap))
                check(equal(a['x_um'],cursor),'abstract_geometry','Unexpected gap or overlap at '+did)
                cursor+=d['width_um']; previous=did
        check(len(seen)==len(devices) and set(seen)==set(devices),'device_identity','Ordered device identity differs')
        found=[(s['left'],s['right'],s['shared_candidate'],s['gap_um']) for s in layout['seams']]
        check(found==seams,'abstract_geometry','Seam declarations differ')
        for area in rules['obstacles']+rules['reserved_access']:
            width=max(width,area['x_um']+area['width_um']);height=max(height,area['y_um']+area['height_um'])
            for a in actual.values():
                overlap=(a['x_um']<area['x_um']+area['width_um']-1e-9 and area['x_um']<a['x_um']+a['width_um']-1e-9 and
                         a['y_um']<area['y_um']+area['height_um']-1e-9 and area['y_um']<a['y_um']+a['height_um']-1e-9)
                check(not overlap,'abstract_geometry','Reserved resource overlap')
        for port in netlist['ports']:
            width=max(width,port['x_um']);height=max(height,port['y_um'])
        for axis,value in [('width',width),('height',height)]:
            limit=p['constraints']['max_'+axis+'_um']
            check(value<limit-1e-9 if p['constraints'][axis+'_strict'] else value<=limit+1e-9,
                  'abstract_geometry',axis+' bound violated')
            check(equal(layout['metrics'][axis+'_um'],value),'abstract_geometry',axis+' metric differs')
        check(equal(layout['metrics']['area_um2'],width*height),'abstract_geometry','Area metric differs')
        points={}
        for a in actual.values():
            for endpoint in a['terminals'].values():
                points.setdefault(endpoint['net'],[]).append((endpoint['x_um'],endpoint['y_um']))
        for port in netlist['ports']:
            points.setdefault(port['net'],[]).append((port['x_um'],port['y_um']))
        hpwl=sum(max(x for x,y in v)-min(x for x,y in v)+max(y for x,y in v)-min(y for x,y in v)
                 for v in points.values())
        breaks=sum(not item[2] for item in seams)
        area=sum(d['width_um']*d['height_um'] for d in devices.values())
        score=width*height/area+p['objective']['wire_weight']*hpwl/math.sqrt(area)+p['objective']['break_weight']*breaks/len(devices)
        for key,value in [('hpwl_proxy_um',hpwl),('diffusion_breaks',breaks),('score',score)]:
            check(equal(layout['metrics'][key],value),'abstract_geometry',key+' metric differs')
        for key,value in [('routing','not_generated'),('qualification','proxy_only'),
                          ('terminal_geometry','nominal_anchors_not_mask_pins'),
                          ('body_supply','declared_net_only'),('pin_access','reserved_regions_screen_only')]:
            check(layout['metrics'][key]==value,'abstract_geometry','Unsupported claim in '+key)
        check(layout['metrics']['feasible'] is True and layout['metrics']['violation']==0 and
              layout['metrics']['violations']==[],'abstract_geometry','Inconsistent feasibility report')
    except (KeyError,TypeError,ValueError,ZeroDivisionError,OverflowError) as error:
        for group in issues: issues[group].append('Malformed abstract output: '+str(error))
    checks={k:'failed' if v else 'passed' for k,v in issues.items()}
    return {'scope':'transistor_proxy','checks':checks,'verdict':'passed' if all(v=='passed' for v in checks.values()) else 'failed',
            'issues':issues,'physical_verification':'not_run','routing':'not_generated',
            'limits':'Nominal terminal anchors and row intervals only; no mask DRC, LVS, well/tap connectivity, timing or electrical proof'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('input','layout','netlist','rules'): parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    load=lambda name:json.loads(Path(getattr(args,name)).read_text())
    result=audit(load('input'),load('layout'),load('netlist'),load('rules'))
    print(json.dumps(result,indent=2,allow_nan=False))
    return 0 if result['verdict']=='passed' else 1


if __name__=='__main__':
    raise SystemExit(main())
