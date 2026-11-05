"""Preserve polygon holes using an explicitly supplied technology grid."""
import math

from shapely.geometry import box
from shapely.ops import unary_union


def fracture(shape, grid_um):
    if not math.isfinite(grid_um) or grid_um <= 0:
        raise ValueError("Supply a positive finite grid in micrometers")
    if not shape.interiors:
        return [shape]
    hole=shape.interiors[0]
    hx0,hy0,hx1,hy1=hole.bounds
    cut=round((hx0+hx1)/(2*grid_um))*grid_um
    if not hx0 < cut < hx1:
        raise ValueError("Hole has no interior cut on the supplied grid")
    x0,y0,x1,y1=shape.bounds
    margin=max(x1-x0,y1-y0,grid_um)
    pieces=[]
    for region in (box(x0-margin,y0-margin,cut,y1+margin),
                   box(cut,y0-margin,x1+margin,y1+margin)):
        part=shape.intersection(region)
        parts=[part] if part.geom_type=="Polygon" else list(part.geoms)
        for polygon in parts:
            if polygon.geom_type=="Polygon" and polygon.area>0:
                pieces.extend(fracture(polygon,grid_um))
    assert pieces and all(not polygon.interiors for polygon in pieces)
    assert shape.symmetric_difference(unary_union(pieces)).area<1e-8
    return pieces
