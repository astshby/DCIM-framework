"""Conservative same-net stripe alignment; native DRC/LVS remain mandatory."""
from shapely.geometry import box,Point
from shapely.ops import unary_union
from shapely import affinity


def align_parallel(router, clearance=.120, m3_clearance=.080):
    for layer in (34,35,36,37):
        for net in router.ids:
            key = layer,net
            merged = unary_union(router.net_shapes[key])
            parts = [] if merged.is_empty else [merged] if merged.geom_type=="Polygon" else list(merged.geoms)
            axis = 0 if layer%2==0 else 1
            for _ in range(20):
                changed = False
                for i,p in enumerate(parts):
                    b = p.bounds
                    if abs(b[axis+2]-b[axis]-.080)>1e-7 or abs(p.area-box(*b).area)>1e-8:
                        continue
                    c = (b[axis]+b[axis+2])/2
                    for j,q in enumerate(parts):
                        if i==j or p.distance(q)>=.080-1e-7:
                            continue
                        d = q.bounds
                        if abs(d[axis+2]-d[axis]-.080)>1e-7 or abs(q.area-box(*d).area)>1e-8:
                            continue
                        target = (d[axis]+d[axis+2])/2
                        if not 1e-7<abs(target-c)<.160-1e-7:
                            continue
                        delta = target-c
                        move = lambda s: affinity.translate(s,xoff=delta if axis==0 else 0,
                                                            yoff=delta if axis==1 else 0)
                        proposed = move(p)
                        if not proposed.intersects(q):
                            continue
                        others = [s for (l,n),ss in router.net_shapes.items() if l==layer and n!=net for s in ss]
                        if any(proposed.distance(s)<clearance-1e-7 for s in others):
                            continue
                        terminal = router.fixed_port_pins.get(net)
                        if terminal and terminal[0]==layer and p.covers(Point(terminal[1:])):
                            continue
                        updates,extensions,valid = [],[],True
                        for vl,other in ((layer+19,layer-1),(layer+20,layer+1)):
                            metal = unary_union(router.net_shapes[other,net])
                            for k,cut in enumerate(router.net_shapes[vl,net]):
                                if p.buffer(1e-8).covers(cut):
                                    shifted = move(cut)
                                    if not metal.buffer(1e-8).covers(shifted.buffer(.016,join_style=2)):
                                        if other not in router.half:
                                            valid = False
                                        else:
                                            hx,hy = router.half[other]
                                            oldx,oldy = cut.centroid.x,cut.centroid.y
                                            newx,newy = shifted.centroid.x,shifted.centroid.y
                                            extension = box(min(oldx,newx)-hx,min(oldy,newy)-hy,
                                                            max(oldx,newx)+hx,max(oldy,newy)+hy)
                                            neighbor_clearance = m3_clearance if other==33 else clearance
                                            obstacles = [s for (l,n),ss in router.net_shapes.items()
                                                         if l==other and n!=net for s in ss]
                                            if any(extension.distance(s)<neighbor_clearance-1e-7 for s in obstacles):
                                                valid = False
                                            else:
                                                extensions.append((other,extension))
                                    updates.append((vl,k,shifted))
                        if not valid:
                            continue
                        for vl,k,cut in updates:
                            router.net_shapes[vl,net][k] = cut
                        for other,extension in extensions:
                            router.net_shapes[other,net].append(extension)
                        combined = unary_union([proposed,q])
                        parts = [s for k,s in enumerate(parts) if k not in (i,j)]+[combined]
                        print("ALIGN_STRIPE",layer,net,round(c,6),round(target,6),flush=True)
                        changed = True
                        break
                    if changed:
                        break
                if not changed:
                    break
            router.net_shapes[key] = parts
