"""Native shared-pair LRCC diagnostic. Independent source remains the OA CDL.

All generated masks are emitted through the existing Virtuoso writer.
This is an editable experimental recipe, not a PDK-qualified cell library.
"""
from collections import defaultdict
from copy import deepcopy
import json
from shapely.geometry import Polygon
from core_geometry import (OLD, atlas, shared_pair, merge_at, rect, wire, via,
                           label, ref)
from geometry import empty_cell, capture_closure, read_gds
from route12 import Router


def logic_atlas():
    lib = read_gds(OLD / "lrcc12_v1_layout_v2.gds")
    meta = json.loads((OLD / "lrcc12_v1_layout_v2.json").read_text())
    top = lib.cells[meta["cell"]]
    natives = {}
    for name, (x, y, kind, fins) in meta["placements"].items():
        natives[kind, fins] = next(
            r.ref_cell for r in top.references
            if abs(r.origin[0]-x) < 1e-7 and abs(r.origin[1]-y) < 1e-7)
    return natives


def lrcc(compact=False, access=False, pitch=.720, port_metal=5):
    assert pitch in (.450,.540,.720)
    assert port_metal in (5,7)
    natives, taps = logic_atlas(), atlas()
    cells = capture_closure(read_gds(OLD / "sram6t12_v1_layout_v2.gds"),
                            [taps["SUB"].name, taps["NW"].name])
    top = empty_cell()
    pins = defaultdict(list)
    # This declaration is independently checked in logic_recipe.py.
    chains = [
        ("n", 2, 0., 0., ["LBL", "Q", "Q_FB"], ["CRD", "CRDB"]),
        ("p", 2, 0., .720, ["LBL", "Q", "Q_FB"], ["CRDB", "CRD"]),
        ("n", 2, pitch, 0., ["QB", "VSS", "Q_FB"], ["Q", "QB"]),
        ("p", 2, pitch, .720, ["QB", "VDD_MEM", "Q_FB"], ["Q", "QB"]),
        ("n", 4, 2*pitch, 0., ["VSS", "PP", "VSS"], ["QB", "IFN"]),
        ("p", 4, 2*pitch, .720, ["VDD_LOGIC", "NOR_PSTACK", "PP"], ["QB", "IFN"]),
    ]
    # Route on upper local metals; preserve all source drain/gate contact
    # identity. Directional pin escapes avoid adjacent 90nm VIA1 conflicts.
    for kind, fins, x, y, sd, gates in chains:
        pair = shared_pair(natives[kind, fins], fins, kind)
        clean = []
        for p in pair["polygons"]:
            px0, py0, px1, py1 = Polygon(p["points_um"]).bounds
            if p["layer"] == 31:
                continue  # replace contact M1 by straight legal-area strips
            if fins == 2 and p["layer"] == 17:
                if p["datatype"] == 11:
                    p["points_um"] = [[px0, -.234 if py0 < 0 else .320],
                                       [px1, -.234 if py0 < 0 else .320],
                                       [px1, -.166 if py0 < 0 else .388],
                                       [px0, -.166 if py0 < 0 else .388]]
                elif p["datatype"] in (0, 7):
                    p["points_um"] = [[px0, -.206], [px1, -.206],
                                       [px1, .360], [px0, .360]]
            clean.append(p)
        pair["polygons"] = clean
        merge_at(top, pair, x, y)
        h = .058+(fins-2)*.048
        gy = .177 if fins == 2 else .283
        sites = [
            (sd[0], -.037, (-.276 if pitch < .720 else -.236) if x == pitch else -.216, h/2),
            (sd[1], .053, h/2, h/2),
            (sd[2], .143, h+.192, h/2),
        ]
        for net, dx, ey, sy in sites:
            ey_end = .034 if dx == .053 else .041
            rect(top, 31, x+dx-.028, y+min(-.034, ey-ey_end),
                 x+dx+.028, y+max(h+.034, ey+ey_end))
            via(top, 1, x+dx, y+ey)
            px, py = round((x+dx)/.020)*.020, round((y+ey)/.020)*.020
            if access and net in ("VDD_MEM","VDD_LOGIC"):
                # Narrow long M2 can pass the adjacent S/D landing; terminate
                # above the active rows so feedback cannot seal this contact.
                py = 1.220 if net == "VDD_LOGIC" else 1.200
                rect(top,32,x+dx-.019,y+ey-.064,x+dx+.019,py+.064,70)
                via(top,2,x+dx,py)
            else:
                rect(top, 32, min(x+dx,px)-.030, min(y+ey,py)-.064,
                     max(x+dx,px)+.030, max(y+ey,py)+.064, 70)
                via(top, 2, px, py)
            pins[net].append((33, px, py))
        for net, dx, cy, ox in ((gates[0], -.160, gy, .008),
                                (gates[1], .300, h-gy, .098)):
            gx0,gx1 = (-.201,.062) if dx < 0 else (.055,.341)
            rect(top, 31, x+gx0,y+cy-.025,x+gx1,y+cy+.025)
            via(top, 1, x+dx, y+cy)
            px, py = round((x+dx)/.020)*.020, round((y+cy)/.020)*.020
            rect(top, 32, min(x+dx,px)-.030, min(y+cy,py)-.064,
                 max(x+dx,px)+.030, max(y+cy,py)+.064, 70)
            via(top, 2, px, py)
            pins[net].append((33, px, py))
    # Shared body context spans the three columns, taps amortized once.
    for kind, y, bulk in (("SUB", .053, "BN"), ("NW", .773, "BP")):
        x = -.640
        top["references"].append(ref(taps[kind].name, x, y))
        rect(top, 250, x-.260, y-.149, x+.260, y+.149)
        rect(top, 31, x-.041, y-.043, x+.041, y+.043)
        via(top, 1, x, y)
        py = round(y/.020)*.020
        rect(top, 32, x-.030, min(y,py)-.064, x+.030, max(y,py)+.064, 70)
        via(top, 2, x, py)
        pins[bulk].append((33, x, py))
    rect(top, 23, -.900, -.230, 2*pitch+.411, .480)
    rect(top, 26, -.270, -.206, 2*pitch+.376, .480)
    rect(top, 24, -.900, .480, 2*pitch+.411, 1.104)
    rect(top, 25, -.270, .480, 2*pitch+.376, 1.080)
    rect(top, 3, -.900, .480, 2*pitch+.411, 1.104)
    router = Router((-.96, -.46, 2*pitch+.660, 1.42))
    # Keep the two QB branches at least160nm center-to-center. Filling their
    # earlier40nm slot made a200nm plate and invoked redundant-via/wide-space.
    router.forbidden_tracks["QB",34] = (pitch+.320,pitch+.440)
    port_access = {}
    if access:
        # Export real accessible M5 terminals before qualifying the interface.
        # Parent wiring can land above these without crossing local M3/M4.
        for x,names in ((-.800,("BN","LBL","CRD","CRDB","BP")),
                        (2*pitch+.500,("PP","VSS","VDD_MEM","VDD_LOGIC","IFN"))):
            for i,net in enumerate(names):
                pin = (30+port_metal,x,round(-.200+.280*i,6))
                port_access[net] = pin
    for net, ps in pins.items():
        for pin in ps:
            router.pin(net, pin)
    for net,pin in port_access.items():
        router.pin(net,pin)
    router.fixed_port_pins = port_access
    # Internal storage nets first, followed by controls and supplies.
    order = ["CRDB", "CRD", "IFN", "Q_FB", "Q", "QB", "NOR_PSTACK", "LBL", "PP",
             "VSS", "VDD_MEM", "VDD_LOGIC", "BN", "BP"]
    for net in order:
        router.route(net, pins[net])
    if access:
        router.rebuild_owners(.100)
    for net,pin in sorted(port_access.items(),key=lambda item:(item[0] not in ("BN","BP"),
                                                               item[0] != "IFN")):
        router.route(net,[pins[net][0],pin])
    global last_router
    last_router = router
    top["polygons"].extend(router.polygons())
    ports = "LBL VSS PP CRDB CRD VDD_MEM VDD_LOGIC IFN BN BP".split()
    for net in ports:
        metal, x, y = port_access.get(net,pins[net][0])
        label(top, net, metal-30, x, y)
    # Boundary phase moves by integer48nm fin pitches. This is still checked
    # as a fresh candidate: boundary origin participates in fin recognition.
    rect(top, 108, *(-.900,-.355,2*pitch+(.600 if access else .540),1.325 if access else 1.181) if compact
         else (-.960,-.499,2*pitch+.660,1.469))
    cells["lrcc_core"] = top
    source = (OLD / "lrcc12_v1_layout_v2_lvs/source.cdl").read_text()
    return cells, "lrcc_core", source, "lrcc12_v1"
