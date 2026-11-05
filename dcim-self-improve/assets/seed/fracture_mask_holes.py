"""Represent Manhattan metal holes with simple polygons without filling holes."""
from shapely.geometry import box
from shapely.ops import unary_union


def fracture(shape):
    if not shape.interiors:
        return [shape]
    hole=shape.interiors[0]
    hx0,hy0,hx1,hy1=hole.bounds
    cut=round((hx0+hx1)/2,3)
    assert hx0-1e-8<=cut<=hx1+1e-8,("No legal1nm fracture coordinate",hole.bounds)
    x0,y0,x1,y1=shape.bounds
    pieces=[]
    for region in (box(x0-1,y0-1,cut,y1+1),box(cut,y0-1,x1+1,y1+1)):
        part=shape.intersection(region)
        parts=[part] if part.geom_type=="Polygon" else list(part.geoms)
        for p in parts:
            if p.geom_type=="Polygon" and p.area>0:
                pieces.extend(fracture(p))
    assert pieces and all(not p.interiors for p in pieces)
    assert shape.symmetric_difference(unary_union(pieces)).area<1e-8
    return pieces
