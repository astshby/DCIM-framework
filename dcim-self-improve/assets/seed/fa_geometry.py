"""Native22T FA from independently checked chains and the qualified contacts."""
from collections import defaultdict
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from geometry import empty_cell,read_gds,capture_closure
from core_geometry import (OLD,atlas,shared_pair,merge_at,rect,via,label,ref,
                           append_polygon)
from logic_geometry import logic_atlas
from fa_recipe import recipe
from route12 import Router
from repair_logic_routes import align_parallel
import random
import math


def fa22t(boundary_trim=False, pitch=.720, row_pitch=1.200):
    """Fixed circuit, discrete target-native placement experiments.

    Smaller pitches are diagnostics, not composition-qualified replacements.
    No scaling of a device polygon or change of MOS sizing is performed.
    """
    assert pitch in (.540, .720)
    assert row_pitch in (.720, .960, 1.200)
    baseline = pitch == .720 and row_pitch == 1.200
    topology = recipe()
    natives,taps = logic_atlas(),atlas()
    cells = capture_closure(read_gds(OLD/"sram6t12_v1_layout_v2.gds"),
                            [taps["SUB"].name,taps["NW"].name])
    top = empty_cell()
    pins = defaultdict(list)
    for index,chain in enumerate(topology["chains"]):
        kind = "n" if chain["model"].startswith("n") else "p"
        fins = int(chain["params"]["nfin"])
        x,y = (index//2)*pitch,0. if kind == "n" else row_pitch
        sd,gates = chain["diffusion_nets"],chain["gate_nets"]
        if len(gates) == 2:
            device = shared_pair(natives[kind,fins],fins,kind)
        else:
            assert len(gates) == 1 and fins == 2
            device = empty_cell()
            for (layer,dt),polys in natives[kind,fins].get_polygons(by_spec=True).items():
                for points in polys:
                    append_polygon(device,layer,dt,Polygon(points))
        clean = []
        for p in device["polygons"]:
            px0,py0,px1,py1 = Polygon(p["points_um"]).bounds
            if p["layer"] == 31:
                continue
            if fins == 2 and p["layer"] == 17:
                if p["datatype"] == 11:
                    lo,hi = (-.234,-.166) if py0 < 0 else (.320,.388)
                    p["points_um"] = [[px0,lo],[px1,lo],[px1,hi],[px0,hi]]
                elif p["datatype"] in (0,7):
                    p["points_um"] = [[px0,-.206],[px1,-.206],[px1,.360],[px0,.360]]
            clean.append(p)
        device["polygons"] = clean
        merge_at(top,device,x,y)
        h = .058+(fins-2)*.048
        gy = .177 if fins == 2 else .283
        sites = [(-.037,-.216),(.053,h/2),(.143,h+.192)]
        for net,(dx,ey) in zip(sd,sites):
            ey_end = .034 if dx == .053 else .041
            rect(top,31,x+dx-.028,y+min(-.034,ey-ey_end),
                 x+dx+.028,y+max(h+.034,ey+ey_end))
            via(top,1,x+dx,y+ey)
            px,py = round((x+dx)/.020)*.020,round((y+ey)/.020)*.020
            if row_pitch == .720:
                # Move only the M2→M3 landing away from the facing row;
                # native VIA1 and transistor contacts remain unchanged.
                if kind == "n" and dx == .143:
                    py = .240
                elif kind == "p" and dx == -.037:
                    py = .600
            # Reserve access above local routing for every terminal. Center
            # diffusion contacts escape on narrow M2 to the outside rows.
            if dx == .053:
                py = -.600 if kind == "n" else round(row_pitch+.820,6)
                rect(top,32,x+dx-.019,min(y+ey,py)-.064,
                     x+dx+.019,max(y+ey,py)+.064,70)
                via(top,2,x+dx,py)
                pins[net].append((33,px,py))
                continue
            rect(top,32,min(x+dx,px)-.030,min(y+ey,py)-.064,
                 max(x+dx,px)+.030,max(y+ey,py)+.064,70)
            via(top,2,px,py)
            pins[net].append((33,px,py))
        # At540nm, the old +300/-160nm gate-via escape pair leaves only
        #80nm between neighboring gates. Move the via centers inside their
        #existing legal M1 landings; do not move the native gate/contact.
        gate_left,gate_right = (-.160,.300) if pitch == .720 else (-.080,.240)
        for net,(dx,cy,gx0,gx1) in zip(gates,[(gate_left,gy,-.201,.062),
                                              (gate_right,h-gy,.055,.341)]):
            rect(top,31,x+gx0,y+cy-.025,x+gx1,y+cy+.025)
            via(top,1,x+dx,y+cy)
            px,py = round((x+dx)/.020)*.020,round((y+cy)/.020)*.020
            rect(top,32,min(x+dx,px)-.030,min(y+cy,py)-.064,
                 max(x+dx,px)+.030,max(y+cy,py)+.064,70)
            via(top,2,px,py)
            pins[net].append((33,px,py))
    for kind,y,bulk in (("SUB",.053,"BN"),("NW",row_pitch+.053,"BP")):
        x = -.640
        top["references"].append(ref(taps[kind].name,x,y))
        rect(top,250,x-.260,y-.149,x+.260,y+.149)
        rect(top,31,x-.041,y-.043,x+.041,y+.043)
        via(top,1,x,y)
        py = round(y/.020)*.020
        rect(top,32,x-.030,min(y,py)-.064,x+.030,max(y,py)+.064,70)
        via(top,2,x,py)
        pins[bulk].append((33,x,py))
    end = 5*pitch
    well_boundary = row_pitch/2+.120
    rect(top,23,-.900,-.230,end+.411,well_boundary)
    rect(top,26,-.270,-.206,end+.376,well_boundary)
    rect(top,24,-.900,well_boundary,end+.411,row_pitch+.384)
    rect(top,25,-.270,well_boundary,end+.376,row_pitch+.360)
    rect(top,3,-.900,well_boundary,end+.411,row_pitch+.384)
    # Single-device chain has a different termination from a shared pair.
    # Complete the missing90nm dummy phase without creating active OD.
    if pitch == .720:
        for y in (0.,row_pitch):
            rect(top,17,3.240,y-.206,3.256,y+.360,7)
            for lo,hi in ((-.234,-.166),(.320,.388)):
                rect(top,17,3.060,y+lo,3.436,y+hi,11)
    access = {}
    for x,names in ((-1.200,("BN","A","B","CI","BP")),
                    (end+.860,("CO","S","VSS","VDD"))):
        for i,net in enumerate(names):
            access[net] = (37,x,round(-.200+.280*i,6))
    base_order = ["PROP_BAR","PROP","SUM_BAR","CARRY_MUX","CARRY_BAR","B_BAR",
                  "A","B","CI","S","CO","VDD","VSS"]
    orders = [base_order,sorted(base_order,key=lambda n:len(pins[n])),
              sorted(base_order,key=lambda n:-len(pins[n]))]
    rng = random.Random(20261028)
    for _ in range(9):
        order = list(base_order)
        rng.shuffle(order)
        orders.append(order)
    failures = []
    for attempt,order in enumerate(orders):
        router = Router((-1.36,-.86,end+1.020,row_pitch+1.060))
        router.spacing = .120
        router.minimum_route_layer = 34
        if baseline:
            router.forbidden_tracks["PROP_BAR",34] = (1.320,1.380)
            router.forbidden_rows["PROP",35] = [(-.060,.160),(1.100,1.260)]
            router.forbidden_rows["CO",35] = [(-.500,-.240)]
            router.forbidden_rows["CO",37] = [(-.460,-.220)]
        elif pitch == .720 and row_pitch == .960:
            # fa22 native DRC and geometry-matched ownership identify these
            # as same-net sub-spacing branches, not a device-row violation.
            router.forbidden_tracks["CARRY_BAR",34] = (2.960,3.120)
            router.forbidden_rows["PROP_BAR",35] = [(.900,1.080),(-.060,.020)]
            router.forbidden_rows["CO",35] = [(-.500,-.240)]
            router.forbidden_rows["CO",37] = [(-.460,-.220)]
        for net,ps in pins.items():
            for pin in ps:
                router.pin(net,pin)
        for net,pin in access.items():
            router.pin(net,pin)
        # All local terminals get M4 landing reservations before any long
        # net is routed. Short M3 escapes align with the legal40nm x phase.
        escaped = defaultdict(list)
        for net,ps in pins.items():
            for _,x,y in ps:
                ex = round(math.floor(x/.040+.5+1e-7)*.040,6)
                router.add(net,33,(min(x,ex)-.064,y-.032,max(x,ex)+.064,y+.032))
                router.pin(net,(34,ex,y))
                router.add(net,53,(ex-.016,y-.016,ex+.016,y+.016))
                router.pin(net,(35,ex,y))
                router.add(net,54,(ex-.020,y-.020,ex+.020,y+.020))
                escaped[net].append((35,ex,y))
        if not baseline:
            conflicts = []
            for net,ps in escaped.items():
                for pin in ps:
                    owner = router.owners[router.coordinate(pin)]
                    if owner != router.number(net):
                        conflicts.append(dict(net=net,pin=pin,owner=int(owner)))
            if conflicts:
                raise ValueError(("Initial terminal reservations conflict; reorder/rework access",
                                  conflicts))
        try:
            for net in order+["BN","BP"]:
                router.route(net,escaped[net])
            router.rebuild_owners(.120)
            for net,pin in sorted(access.items(),key=lambda item:item[0] not in ("BN","BP")):
                router.route(net,[escaped[net][0],pin])
        except (ValueError,AssertionError) as error:
            failures.append(dict(order=order,error=str(error)))
            print("FA_ROUTE_REJECT",attempt,str(error),flush=True)
            continue
        print("FA_ROUTE_CONNECTED",attempt,order,flush=True)
        break
    else:
        raise ValueError(("No routable declared order",failures))
    router.fixed_port_pins = access
    align_parallel(router)
    # Eliminate the diagnosed20nm via-to-step enclosure at the PROP M6
    # overlap.160nm is still below the162nm wide-metal redundancy trigger.
    if baseline:
        patch = box(1.720,-.520,1.800,-.420)
        owner = unary_union(router.net_shapes[36,"PROP"])
        assert owner.buffer(1e-8).covers(box(1.720,-.420,1.800,-.400))
        assert all(patch.distance(s)>=.080-1e-7
                   for (l,n),ss in router.net_shapes.items() if l==36 and n!="PROP" for s in ss)
        router.add("PROP",36,patch.bounds)
    global last_router
    last_router = router
    top["polygons"].extend(router.polygons())
    for net,(metal,x,y) in access.items():
        label(top,net,metal-30,x,y)
    rect(top,108,-.900,-.835,end+.600,row_pitch+(.941 if boundary_trim else 1.085))
    cells["fa22t_core"] = top
    source = (OLD/"fa22t12_v1_layout_v2_lvs/source.cdl").read_text()
    return cells,"fa22t_core",source,"fa22t12_v1"
