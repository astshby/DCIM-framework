"""Build and draw a hierarchy from explicit measured blocks. No process rules."""
import html
import json
from pathlib import Path
from geometry import bbox, expanded_refs, topo_order, transform


def compose(spec):
    cells = {}
    references = []
    for source, data in spec['sources'].items():
        prefix = source + '__'
        for name, original in data.items():
            entry = json.loads(json.dumps(original))
            for ref in entry['references']:
                ref['child'] = prefix + ref['child']
            cells[prefix + name] = entry
    for block in spec['placements']:
        child = block['source'] + '__' + block['cell']
        box = bbox(cells, child)
        corners = [transform(p, block['rotation_deg']) for p in
                   ((box[0],box[1]), (box[0],box[3]), (box[2],box[1]), (box[2],box[3]))]
        origin = [block['x_um']-min(x for x,y in corners), block['y_um']-min(y for x,y in corners)]
        references.append({'instance_id': block['id'], 'child': child, 'origin_um': origin,
                           'rotation_deg': block['rotation_deg'], 'x_reflection': False,
                           'columns': 1, 'rows': 1, 'spacing_um': None})
    cells['candidate_top'] = {'polygons': [], 'labels': [], 'references': references}
    topo_order(cells, 'candidate_top')
    return cells


def draw_svg(cells, top, path):
    box = bbox(cells, top)
    x0,y0,x1,y1 = box
    shapes = []
    palette = ('#2563eb','#e87924','#16a34a','#9333ea','#dc2626','#0891b2')
    def visit(name, chain):
        def project(point):
            for ref in reversed(chain):
                x,y = transform(point, ref.get('rotation_deg',0), ref.get('x_reflection',False))
                point = (x+ref['origin_um'][0], y+ref['origin_um'][1])
            return point[0], y0+y1-point[1]
        for poly in cells[name]['polygons']:
            points = ' '.join('%.9g,%.9g' % project(p) for p in poly['points_um'])
            color = palette[int(poly['layer']) % len(palette)]
            shapes.append('<polygon points="%s" fill="%s" fill-opacity="0.45"><title>%s</title></polygon>' %
                          (points,color,html.escape(name+' layer '+str(poly['layer']))))
        for label in cells[name]['labels']:
            x,y=project(label['origin_um'])
            shapes.append('<text x="%g" y="%g" font-size="%g">%s</text>' %
                          (x,y,max(x1-x0,y1-y0)/80,html.escape(label['text'])))
        for ref0 in cells[name]['references']:
            for ref in expanded_refs(ref0):
                visit(ref['child'], chain+[ref])
    visit(top, [])
    Path(path).write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%g %g %g %g">%s</svg>' %
                         (x0,y0,x1-x0,y1-y0,''.join(shapes)), encoding='utf-8')


def export_gds(cells, top, path, precision_m):
    import gdspy
    if not isinstance(precision_m, (int,float)) or not 0 < precision_m < 1e-6:
        raise ValueError('Declare a positive sub-micrometer export precision')
    library = gdspy.GdsLibrary(unit=1e-6, precision=precision_m)
    # Export is optional; project grid must be validated separately.
    mapping = {}
    for index, name in enumerate(topo_order(cells,top)):
        cell = library.new_cell('C%d' % index)
        mapping[name] = cell
        for poly in cells[name]['polygons']:
            cell.add(gdspy.Polygon(poly['points_um'],layer=poly['layer'],datatype=poly['datatype']))
        for label in cells[name]['labels']:
            cell.add(gdspy.Label(label['text'],label['origin_um'],layer=label['layer'],texttype=label['datatype']))
        for ref0 in cells[name]['references']:
            for ref in expanded_refs(ref0):
                cell.add(gdspy.CellReference(mapping[ref['child']],ref['origin_um'],
                    rotation=ref['rotation_deg'],x_reflection=ref['x_reflection']))
    library.write_gds(str(path))
    return {name: cell.name for name,cell in mapping.items()}


def generate(spec, output):
    output = Path(output)
    cells = compose(spec)
    data = {'cells': cells, 'top': 'candidate_top', 'qualification': 'geometry_only',
            'connectivity': 'inter-block routing not generated', 'bbox_um': bbox(cells,'candidate_top')}
    (output/'layout.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    draw_svg(cells,'candidate_top',output/'layout.svg')
    return {'bbox_um':data['bbox_um'], 'qualification':'geometry_only'}
