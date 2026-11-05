"""Small local M3/M4/M5 router with explicit net ownership.

Native 12FFC mapping and landing dimensions. Calibre remains the checker.
Only straight preferred-direction segments and interlayer turns are allowed.
"""
from collections import defaultdict
import heapq
import math
import numpy as np
from shapely.geometry import box, Point
from shapely.ops import unary_union
from shapely import affinity
from core_geometry import append_polygon


class Router:
    grid = .020
    layers = (33, 34, 35, 36, 37)
    spacing = .080
    half = {33: (.064, .032), 34: (.040, .100), 35: (.100, .040),
            36: (.040, .100), 37: (.100, .040)}
    datatype = {33: 70, 34: 150, 35: 245, 36: 240, 37: 245,
                53: 150, 54: 240, 55: 240, 56: 240}

    def __init__(self, bounds):
        self.x0, self.y0, x1, y1 = bounds
        self.nx = round((x1-self.x0)/self.grid)+1
        self.ny = round((y1-self.y0)/self.grid)+1
        self.owners = np.zeros((len(self.layers), self.nx, self.ny), np.int32)
        self.ids = {}
        self.shapes = defaultdict(list)
        self.net_shapes = defaultdict(list)
        self.net_rects = defaultdict(list)
        self.routes = []
        self.via_sites = defaultdict(set)
        self.forbidden_tracks = {}
        self.merge_narrow_slots = False
        self.net_nodes = defaultdict(set)
        self.fixed_port_pins = {}
        self.allowed_tracks = {}
        self.forbidden_rows = {}
        self.minimum_route_layer = 33

    def number(self, net):
        if net not in self.ids:
            self.ids[net] = len(self.ids)+1
        return self.ids[net]

    def coordinate(self, pin):
        l, x, y = pin
        ix, iy = round((x-self.x0)/self.grid), round((y-self.y0)/self.grid)
        assert abs(self.x0+ix*self.grid-x) < 1e-7, pin
        assert abs(self.y0+iy*self.grid-y) < 1e-7, pin
        return self.layers.index(l), ix, iy

    def actual(self, node):
        li, ix, iy = node
        return self.layers[li], round(self.x0+ix*self.grid, 6), round(self.y0+iy*self.grid, 6)

    def add(self, net, layer, bounds, record=True):
        if getattr(self,"quantize_geometry",False):
            bounds=tuple(round(float(v),6) for v in bounds)
        if record:
            self.shapes[layer].append(box(*bounds))
            self.net_shapes[layer,net].append(box(*bounds))
            self.net_rects[layer,net].append(tuple(bounds))
        if layer not in self.layers:
            return
        hx, hy = self.half[layer]
        x0, y0, x1, y1 = bounds
        spacing = getattr(self, "m3_spacing", .080) if layer == 33 else self.spacing
        x0 -= hx+spacing-1e-7
        x1 += hx+spacing-1e-7
        y0 -= hy+spacing-1e-7
        y1 += hy+spacing-1e-7
        ix0 = max(0, math.ceil((x0-self.x0)/self.grid))
        ix1 = min(self.nx, math.floor((x1-self.x0)/self.grid)+1)
        iy0 = max(0, math.ceil((y0-self.y0)/self.grid))
        iy1 = min(self.ny, math.floor((y1-self.y0)/self.grid)+1)
        v = self.owners[self.layers.index(layer), ix0:ix1, iy0:iy1]
        own = self.number(net)
        v[(v != 0) & (v != own)] = -1
        v[v == 0] = own

    def pin(self, net, pin):
        l, x, y = pin
        hx, hy = self.half[l]
        self.add(net, l, (x-hx, y-hy, x+hx, y+hy))

    def rebuild_owners(self, spacing):
        self.spacing = spacing
        self.owners[:] = 0
        for (layer,net),shapes in self.net_shapes.items():
            for shape in shapes:
                self.add(net,layer,shape.bounds,record=False)

    def route(self, net, pins):
        goals = {self.coordinate(pins[0])} | self.net_nodes[net]
        owner = self.number(net)
        blocked = (self.owners != 0) & (self.owners != owner)
        for (named_net,layer),(low,high) in self.forbidden_tracks.items():
            if named_net == net:
                xs = self.x0+np.arange(self.nx)*self.grid
                blocked[self.layers.index(layer),(xs>=low-1e-8)&(xs<=high+1e-8),:] = True
        for (named_net,layer),tracks in self.allowed_tracks.items():
            if named_net == net:
                xs = self.x0+np.arange(self.nx)*self.grid
                allowed = np.any(np.abs(xs[:,None]-np.array(tracks)[None,:])<1e-8,axis=1)
                blocked[self.layers.index(layer),~allowed,:] = True
        for (named_net,layer),bands in self.forbidden_rows.items():
            if named_net == net:
                ys = self.y0+np.arange(self.ny)*self.grid
                for low,high in bands:
                    blocked[self.layers.index(layer),:,(ys>=low-1e-8)&(ys<=high+1e-8)] = True
        if hasattr(self,"expand_fixed_goals"):
            self.expand_fixed_goals(net,goals,blocked)
        goals = {g for g in goals if not blocked[g]}
        assert goals, (net,"no accessible existing metal")
        other_blocked=blocked
        for pin in pins[1:]:
            if getattr(self,"same_net_spacing",False):
                blocked=self.same_net_mask(net,other_blocked)
                goals={g for g in goals if not blocked[g]}
                assert goals,(net,"same-net spacing removed every attachment")
            start = self.coordinate(pin)
            if (hasattr(self,"fixed_pin_connected")
                    and self.fixed_pin_connected(net,start,goals)):
                continue
            assert not blocked[start], (net, "blocked start", pin)
            assert all(not blocked[g] for g in goals), (net, "blocked goal")
            distances = None
            if len(goals) > 30 and getattr(self,"fast_heuristic",False):
                distances = np.full(blocked.shape,self.nx+self.ny+len(self.layers),dtype=np.int32)
                for g in goals:
                    distances[g] = 0
                for axis,length in enumerate(distances.shape):
                    size = [1]*len(distances.shape)
                    size[axis] = length
                    coord = np.arange(length,dtype=np.int32).reshape(size)
                    distances = np.minimum.accumulate(distances-coord,axis=axis)+coord
                    rev = [slice(None)]*len(distances.shape)
                    rev[axis] = slice(None,None,-1)
                    rev = tuple(rev)
                    distances = np.minimum.accumulate((distances+coord)[rev],axis=axis)[rev]-coord
            def heuristic(n):
                if distances is not None:
                    return int(distances[n])
                return min(abs(n[1]-g[1])+abs(n[2]-g[2])+4*abs(n[0]-g[0]) for g in goals)
            queue = [(heuristic(start), 0, start)]
            best, parent = {start: 0}, {}
            finish = None
            while queue:
                _, cost, node = heapq.heappop(queue)
                if cost != best[node]:
                    continue
                if node in goals:
                    finish = node
                    break
                li, ix, iy = node
                steps = [(0, 0, -1), (0, 0, 1)] if self.layers[li] % 2 == 0 else [(0, -1, 0), (0, 1, 0)]
                if self.layers[li] == 33 and getattr(self,"local_m3_jogs",False):
                    steps += [(0,0,-1),(0,0,1)]
                steps += [(-1, 0, 0), (1, 0, 0)]
                for dl, dx, dy in steps:
                    nxt = li+dl, ix+dx, iy+dy
                    if not (0 <= nxt[0] < len(self.layers) and 0 <= nxt[1] < self.nx and 0 <= nxt[2] < self.ny):
                        continue
                    if self.layers[nxt[0]] < self.minimum_route_layer:
                        continue
                    if blocked[nxt]:
                        continue
                    # M4 vertical trunks use a 40nm x phase. Avoid 20nm
                    # same-net offsets that form forbidden 100nm-wide jogs.
                    if (dl and 34 in (self.layers[li],self.layers[nxt[0]])
                            and ix % 2 and getattr(self,"m4_phase_lock",True)):
                        continue
                    penalty = 0
                    if dl:
                        level = min(self.layers[li], self.layers[nxt[0]])+20
                        _,vx,vy = self.actual(node)
                        penalty = 200 if any(
                            (abs(vx-qx)>1e-8 or abs(vy-qy)>1e-8)
                            and abs(vx-qx)<.120-1e-8 and abs(vy-qy)<.120-1e-8
                            for qx,qy in self.via_sites[level]) else 0
                    nc = cost+(8 if dl else 1)+penalty
                    if nc < best.get(nxt, math.inf):
                        best[nxt], parent[nxt] = nc, node
                        heapq.heappush(queue, (nc+heuristic(nxt), nc, nxt))
            if finish is None:
                raise ValueError((net, "unrouted", pin, len(best)))
            path = [finish]
            while path[-1] != start:
                path.append(parent[path[-1]])
            self.commit_path(net,path,goals)
            if hasattr(self,"expand_fixed_goals"):
                self.expand_fixed_goals(net,goals,blocked)
        self.net_nodes[net].update(goals)

    def same_net_mask(self,net,blocked):
        """Keep thin aligned stems; same-net connectivity is not a DRC waiver.

        A new parallel stem is legal only at the same centerline or outside
        normal metal spacing. Connections between stems use the other layer.
        """
        assert self.layers==(38,39)
        blocked=blocked.copy()
        for layer in self.layers:
            tracks={}
            for x0,y0,x1,y1 in self.net_rects[layer,net]:
                if layer==38:
                    center=round((x0+x1)/2,6)
                    lo,hi=y0,y1
                else:
                    center=round((y0+y1)/2,6)
                    lo,hi=x0,x1
                if center in tracks:
                    a,b=tracks[center]
                    tracks[center]=(min(a,lo),max(b,hi))
                else:
                    tracks[center]=(lo,hi)
            for center,(lo,hi) in tracks.items():
                # Both centerlines'60nm halfwidth plus80nm spacing.
                if layer==38:
                    x0,x1=center-.200+1e-7,center+.200-1e-7
                    y0,y1=lo-.100,hi+.100
                else:
                    x0,x1=lo-.100,hi+.100
                    y0,y1=center-.200+1e-7,center+.200-1e-7
                ix0=max(0,math.ceil((x0-self.x0)/self.grid))
                ix1=min(self.nx,math.floor((x1-self.x0)/self.grid)+1)
                iy0=max(0,math.ceil((y0-self.y0)/self.grid))
                iy1=min(self.ny,math.floor((y1-self.y0)/self.grid)+1)
                plane=blocked[self.layers.index(layer)]
                if layer==38:
                    line=round((center-self.x0)/self.grid)
                    prior=plane[line,iy0:iy1].copy()
                    plane[ix0:ix1,iy0:iy1]=True
                    plane[line,iy0:iy1]=prior
                else:
                    line=round((center-self.y0)/self.grid)
                    prior=plane[ix0:ix1,line].copy()
                    plane[ix0:ix1,iy0:iy1]=True
                    plane[ix0:ix1,line]=prior
        return blocked

    def commit_path(self,net,path,goals):
            goals.update(path)
            segments=list(zip(path,path[1:]))
            if getattr(self,"compact_segments",False):
                compact=[]
                for a,b in segments:
                    if compact and a[0]==b[0]==compact[-1][0][0]==compact[-1][1][0]:
                        first,last=compact[-1]
                        axis=2 if self.layers[a[0]]%2==0 else 1
                        if last==a and (last[axis]-first[axis])*(b[axis]-a[axis])>0:
                            compact[-1]=(first,b)
                            continue
                    compact.append((a,b))
                segments=compact
            for a, b in segments:
                la, xa, ya = self.actual(a)
                lb, xb, yb = self.actual(b)
                if la == lb:
                    hx, hy = self.half[la]
                    self.add(net, la, (min(xa, xb)-hx, min(ya, yb)-hy,
                                       max(xa, xb)+hx, max(ya, yb)+hy))
                else:
                    for ll in (la, lb):
                        hx, hy = self.half[ll]
                        self.add(net, ll, (xa-hx, ya-hy, xa+hx, ya+hy))
                    h = getattr(self,"via_half",None) or (
                        .016 if min(la, lb) == 33 else .031 if min(la,lb) >= 38 else .020)
                    self.add(net, min(la, lb)+20, (xa-h, ya-h, xa+h, ya+h))
                    self.via_sites[min(la, lb)+20].add((xa,ya))
            self.routes.append((net, len(path)))

    def polygons(self):
        cell = {"polygons": []}
        # Straighten a slightly offset same-net M4 trunk when all incident
        # vias remain covered by their opposite metal. This moves wiring only.
        for (layer,net), shapes in list(self.net_shapes.items()):
            if layer != 34 or getattr(self,"preserve_m4_width",False):
                continue
            u = unary_union(shapes)
            pieces = [u] if u.geom_type == "Polygon" else list(u.geoms)
            replacement = []
            for p in pieces:
                x0,y0,x1,y1 = p.bounds
                if .080+1e-7 < x1-x0 <= .120+1e-7:
                    cx = x0+.040
                    changes = []
                    valid = True
                    for vl,other in ((53,33),(54,35)):
                        other_metal = unary_union(self.net_shapes[other,net])
                        for i,cut in enumerate(self.net_shapes[vl,net]):
                            if p.buffer(1e-8).covers(cut):
                                shifted = affinity.translate(cut,xoff=cx-cut.centroid.x)
                                if not other_metal.buffer(1e-8).covers(shifted):
                                    valid = False
                                changes.append((vl,i,shifted))
                    if valid:
                        p = box(x0,y0,x0+.080,y1)
                        for vl,i,shifted in changes:
                            self.net_shapes[vl,net][i] = shifted
                replacement.append(p)
            # Same-net close parallel trunks must merge legally, not retain
            # a 40nm slot. Fill only their overlap; preserve outside widths.
            bridges = []
            for i,a in enumerate(replacement if self.merge_narrow_slots else []):
                for b in replacement[i+1:]:
                    ax0,ay0,ax1,ay1 = a.bounds
                    bx0,by0,bx1,by1 = b.bounds
                    if bx0 < ax0:
                        ax0,ay0,ax1,ay1,bx0,by0,bx1,by1 = bx0,by0,bx1,by1,ax0,ay0,ax1,ay1
                    lo,hi = max(ay0,by0),min(ay1,by1)
                    if 0 < bx0-ax1 < .080-1e-7 and hi-lo >= .20:
                        bridge = box(ax1,lo,bx0,hi)
                        others = [q for (l,n),qs in self.net_shapes.items()
                                  if l == layer and n != net for q in qs]
                        if all(bridge.distance(q)>=.080-1e-7 for q in others):
                            bridges.append(bridge)
            self.net_shapes[layer,net] = replacement+bridges
        # Same operation for horizontal upper-metal pin escapes. Keep the
        # declared boundary terminal on the resulting stripe.
        for (layer,net),shapes in list(self.net_shapes.items()):
            if layer not in (35,37):
                continue
            u = unary_union(shapes)
            pieces = [u] if u.geom_type == "Polygon" else list(u.geoms)
            replacement = []
            for p in pieces:
                x0,y0,x1,y1 = p.bounds
                if .080+1e-7 < y1-y0 <= .160+1e-7:
                    pin = self.fixed_port_pins.get(net)
                    cy = pin[2] if pin and pin[0] == layer and p.covers(Point(pin[1:])) else y0+.040
                    candidate = box(x0,cy-.040,x1,cy+.040)
                    changes,valid = [],True
                    for vl,other in ((layer+19,layer-1),(layer+20,layer+1)):
                        other_metal = unary_union(self.net_shapes[other,net])
                        for i,cut in enumerate(self.net_shapes[vl,net]):
                            if p.buffer(1e-8).covers(cut):
                                shifted = affinity.translate(cut,yoff=cy-cut.centroid.y)
                                if not other_metal.buffer(1e-8).covers(shifted):
                                    valid = False
                                changes.append((vl,i,shifted))
                    others = [q for (l,n),qs in self.net_shapes.items()
                              if l == layer and n != net for q in qs]
                    valid &= all(candidate.distance(q)>=.080-1e-7 for q in others)
                    if valid:
                        p = candidate
                        for vl,i,shifted in changes:
                            self.net_shapes[vl,net][i] = shifted
                replacement.append(p)
            self.net_shapes[layer,net] = replacement
        components = {}
        for (layer,net), shapes in self.net_shapes.items():
            if layer not in self.layers:
                continue
            merged = unary_union(shapes)
            pieces = [merged] if merged.geom_type == "Polygon" else list(merged.geoms)
            # A* can join two same-net strips with a sub-rule-width step.
            # Square only small M4 components when the completed rectangle is
            # clear of all other nets. Recheck with the foundry deck.
            repaired = []
            for shape in pieces:
                if layer == 34 and len(shape.exterior.coords) > 5:
                    x0,y0,x1,y1 = shape.bounds
                    width = x1-x0
                    if width < .20-1e-7:
                        target = next(w for w in (.080,.120,.160,.200) if w >= width-1e-7)
                        x1 = x0+target
                    candidate = box(x0,y0,x1,y1)
                    others = [q for (l,n),qs in self.net_shapes.items()
                              if l == layer and n != net for q in qs]
                    if candidate.area-shape.area < .040 and all(
                            candidate.distance(q) >= .080-1e-7 for q in others):
                        shape = candidate
                repaired.append(shape)
                if shape.interiors and getattr(self,"fracture_mask_holes",False):
                    from fracture_mask_holes import fracture
                    for piece in fracture(shape):
                        append_polygon(cell,layer,self.datatype[layer],piece)
                else:
                    append_polygon(cell, layer, self.datatype[layer], shape)
            components[layer,net] = repaired
        for (layer,net), shapes in self.net_shapes.items():
            if layer in self.layers:
                continue
            lo,hi = layer-20,layer-19
            # One via per physical metal-component pair prevents nearby
            # duplicate cuts merging into an illegal rectangle. Preserve
            # every distinct intercomponent connection.
            pairs = {}
            for cut in shapes:
                low = [i for i,p in enumerate(components[lo,net]) if p.buffer(1e-9).covers(cut)]
                high = [i for i,p in enumerate(components[hi,net]) if p.buffer(1e-9).covers(cut)]
                assert len(low) == len(high) == 1, (layer,net,cut.bounds)
                pairs.setdefault((low[0],high[0]),cut)
            for cut in pairs.values():
                append_polygon(cell, layer, self.datatype[layer], cut)
        return cell["polygons"]


class UpperRouter(Router):
    """Ordinary M8/M9 over a checked M7 interface, not a rule-deck substitute."""
    grid = .010
    layers = (38,39)
    half = {38:(.060,.100),39:(.100,.060)}
    datatype = {38:20,39:20,58:20}
    fast_heuristic = True
