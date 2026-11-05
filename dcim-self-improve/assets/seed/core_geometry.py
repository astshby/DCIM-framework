"""Core-device geometry recipe from permitted native PCells, never HCSR masks."""
import json
from copy import deepcopy

from shapely.geometry import Polygon, box
from shapely import affinity

from geometry import empty_cell, capture_closure, read_gds
from seed_config import get_path

OLD = get_path("native_ref_root")


def rect(cell, layer, x0, y0, x1, y1, datatype=0):
    assert x1 > x0 and y1 > y0
    cell["polygons"].append({"layer": layer, "datatype": datatype,
                            "points_um": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]})


def label(cell, name, metal, x, y):
    cell["labels"].append({"layer": 130 + metal, "datatype": 0, "text": name,
                          "origin_um": [x, y], "rotation_deg": 0,
                          "x_reflection": False, "anchor": 5, "magnification": .2})


def append_polygon(cell, layer, datatype, poly):
    if poly.is_empty:
        return
    if poly.geom_type != "Polygon":
        if hasattr(poly, "geoms"):
            for p in poly.geoms:
                append_polygon(cell, layer, datatype, p)
        return
    assert not poly.interiors, "Do not drop physical mask holes"
    cell["polygons"].append({"layer": int(layer), "datatype": int(datatype),
                            "points_um": [[round(x, 6), round(y, 6)]
                                          for x, y in list(poly.exterior.coords)[:-1]]})


def atlas():
    lib = read_gds(OLD / "sram6t12_v1_layout_v2.gds")
    meta = json.loads((OLD / "sram6t12_v1_layout_v2.json").read_text())
    top = lib.cells[meta["cell"]]
    result = {}
    for key in ("NQ", "AXQ", "PQ"):
        x, y, *_ = meta["placements"][key]
        result[key] = next(r.ref_cell for r in top.references
                           if abs(r.origin[0] - x) < 1e-8 and abs(r.origin[1] - y) < 1e-8)
    for kind in ("SUB", "NW"):
        result[kind] = next(r.ref_cell for r in top.references
                            if r.ref_cell.name.startswith("M1_" + kind + "_"))
    return result


def shared_pair(native, fins=4, kind="n"):
    """Two equal-fin core MOS share center diffusion at native 90nm pitch.

    Opposite-side gate contacts avoid shorting adjacent M0_PO/M1 landings.
    Native active contact shapes retained. Context is regenerated as a pair,
    with PODE only at true outer OD ends. This is a candidate until DRC/LVS.
    """
    cell = empty_cell()
    h = .058 + (fins - 2) * .048
    upper = .254 if fins == 2 else .360
    lower = h - upper
    native_masks = native.get_polygons(by_spec=True)
    # Keep active gate/contact material only, not independent-cell dummies.
    for x, flip in ((0, False), (.090, True)):
        for (layer, dt), polys in native_masks.items():
            if (layer, dt) not in ((17, 0), (84, 0), (84, 2), (159, 0), (31, 0)):
                continue
            for points in polys:
                p = Polygon(points)
                if layer == 17:
                    p = p.intersection(box(0, -1, .016, 1))
                else:
                    p = p.intersection(box(-.074, -1, .090, 1))
                if flip:
                    p = affinity.scale(p, xfact=1, yfact=-1, origin=(0, 0))
                    p = affinity.translate(p, yoff=h)
                p = affinity.translate(p, xoff=x)
                append_polygon(cell, int(layer), int(dt), p)
    # Continuous active diffusion across the two gates.
    rect(cell, 6, -.090, 0, .196, h)
    rect(cell, 75, -.090, 0, .196, h)
    # Every real gate must reach the common cut rows, including its non-contact
    # end. Native single-PCell gate lengths are asymmetric.
    for x in (0, .090):
        rect(cell, 17, x, lower, x + .016, upper)
    # Native gate contact landing alone is below ordinary M1 minimum area.
    gy = .283 if fins == 4 else .177
    rect(cell, 31, -.132, gy - .019, .072, gy + .019)
    rect(cell, 31, .050, h - gy - .019, .254, h - gy + .019)
    for x in (-.090, .180):
        rect(cell, 17, x, lower, x + .016, upper)
        rect(cell, 206, x, 0, x + .016, h, 28)
    for x in (-.270, -.180, .270, .360):
        rect(cell, 17, x, lower, x + .016, upper, 7)
    # Reconstruct dummy local contacts on the two exterior sides.
    for x in (-.217, -.127, .233, .323):
        ext = .036 if fins == 2 else .012
        rect(cell, 84, x - .020, -ext, x + .020, h + ext)
    if fins == 2:
        rect(cell, 84, -.262, -.063, .368, -.009, 20)
        rect(cell, 84, -.262, h+.009, .368, h+.063, 20)
    rect(cell, 17, -.307, lower - .028, .413, lower + .040, 11)
    rect(cell, 17, -.307, upper - .040, .413, upper + .028, 11)
    rect(cell, 23 if kind == "n" else 24,
         -.305, lower - .024, .411, upper + .024)
    rect(cell, 26 if kind == "n" else 25, -.270, lower, .376, upper)
    rect(cell, 250, -.242, -.096, .348, h + .096)
    if kind == "p":
        rect(cell, 3, -.170, -.067, .276, h + .067)
    return cell


def diagnostic_pair():
    native = atlas()
    cells = capture_closure(read_gds(OLD / "sram6t12_v1_layout_v2.gds"),
                            [native["SUB"].name])
    cells["pair_n4"] = shared_pair(native["NQ"], 4, "n")
    top = empty_cell([
        {"child": "pair_n4", "origin_um": [0, 0], "rotation_deg": 0,
         "x_reflection": False, "columns": 1, "rows": 1, "spacing_um": None},
        {"child": native["SUB"].name, "origin_um": [-.64, .053],
         "rotation_deg": 0, "x_reflection": False,
         "columns": 1, "rows": 1, "spacing_um": None},
    ])
    rect(top, 250, -.90, -.096, -.38, .202)
    rect(top, 23, -.90, -.230, .411, .384)
    rect(top, 31, -.681, .010, -.599, .096)
    for x, y in ((-.64, .053), (.053, .077)):
        rect(top, 51, x - .016, y - .016, x + .016, y + .016, 70)
    rect(top, 32, -.704, -.011, .117, .141, 70)
    label(top, "VSS", 2, -.4, .077)
    label(top, "D0", 1, -.037, .077)
    label(top, "D1", 1, .143, .077)
    label(top, "G0", 1, .008, .283)
    label(top, "G1", 1, .098, -.129)
    rect(top, 108, -.90, -.259, .414, .413)
    cells["core_pair"] = top
    source = (
        "* Independent core SVT pair. MOS order D G S B.\n"
        ".SUBCKT core_pair_source D0 D1 G0 G1 VSS\n"
        "M0 D0 G0 VSS VSS nch_svt_mac L=16n nfin=4\n"
        "M1 D1 G1 VSS VSS nch_svt_mac L=16n nfin=4\n"
        ".ENDS core_pair_source\n")
    return cells, "core_pair", source, "core_pair_source"


def merge_at(dst, src, dx=0, dy=0):
    for p in src["polygons"]:
        append_polygon(dst, p["layer"], p["datatype"],
                       affinity.translate(Polygon(p["points_um"]), dx, dy))


def ref(child, x, y):
    return {"child": child, "origin_um": [x, y], "rotation_deg": 0,
            "x_reflection": False, "columns": 1, "rows": 1, "spacing_um": None}


def via(cell, level, x, y):
    rect(cell, 50 + level, x - .016, y - .016, x + .016, y + .016,
         150 if level == 3 else 70)


def wire(cell, metal, x0, y0, x1, y1, width=.038, end=.064):
    assert x0 == x1 or y0 == y1
    dt = 0 if metal == 1 else 70 if metal in (2, 3) else 150
    if y0 == y1:
        rect(cell, 30 + metal, min(x0, x1)-end, y0-width/2,
             max(x0, x1)+end, y0+width/2, dt)
    else:
        rect(cell, 30 + metal, x0-width/2, min(y0, y1)-end,
             x0+width/2, max(y0, y1)+end, dt)


def sram6t(compact=False, compact_x=False):
    """Two-row core 6T; paired PD/PU, separate unequal-fin access diffusions.

    HCSR-inspired local feedback and shared rail/edge ownership; no HCSR masks,
    SRAM waiver markers or electrical resizing. Golden source is independent OA.
    """
    native = atlas()
    cells = capture_closure(read_gds(OLD / "sram6t12_v1_layout_v2.gds"),
                            [native["SUB"].name, native["NW"].name])
    body = empty_cell()
    pd = shared_pair(native["NQ"], 4, "n")
    # Keep the qualified pair's electrical core; own dummy context once per row.
    for p in pd["polygons"]:
        layer, dt = p["layer"], p["datatype"]
        if layer in (84, 159, 31) or (layer == 17 and dt == 0):
            poly = Polygon(p["points_um"])
            if layer == 84 and dt == 0 and not poly.intersects(box(-.074, -1, .180, 1)):
                continue
            append_polygon(body, layer, dt, poly)
    # Access MOS are on the same fin phase, centered on the PD row's middle fins.
    for x in (-.360, .450):
        for (layer, dt), polys in native["AXQ"].get_polygons(by_spec=True).items():
            if (layer, dt) not in ((84, 0), (84, 2), (84, 20), (159, 0), (31, 0)):
                continue
            for points in polys:
                clip = (-.082, .098) if (layer, dt) == (84, 20) else (-.074, .090)
                p = Polygon(points).intersection(box(clip[0], -1, clip[1], 1))
                append_polygon(body, layer, dt, affinity.translate(p, x, .048))
        rect(body, 17, x, -.206, x+.016, .360)
        rect(body, 31, x-.132, .206, x+.072, .244)
        for sx in (-.037, .053):
            rect(body, 31, x+sx-.019, -.072, x+sx+.019, .125)
    for x0, x1, y0, y1 in ((-.450, -.254, .048, .106),
                           (-.090, .196, 0, .154),
                           (.360, .556, .048, .106)):
        rect(body, 6, x0, y0, x1, y1)
        rect(body, 75, x0, y0, x1, y1)
        for x in (x0, x1-.016):
            rect(body, 17, x, -.206, x+.016, .360)
            rect(body, 206, x, y0, x+.016, y1, 28)
    for x in (-.630, -.540, -.180, .270, .630, .720):
        rect(body, 17, x, -.206, x+.016, .360, 7)
    # Only exterior dummy contacts; no conductive contact at isolated OD gaps.
    for x in (-.577, -.487, -.217, -.127, .233, .323, .593, .683):
        rect(body, 84, x-.020, -.012, x+.020, .166)
    rect(body, 17, -.667, -.234, .773, -.166, 11)
    rect(body, 17, -.667, .320, .773, .388, 11)
    rect(body, 23, -.665, -.230, .771, .384)
    rect(body, 26, -.630, -.206, .736, .360)
    rect(body, 250, -.602, -.096, .708, .250)
    py = .720
    merge_at(body, shared_pair(native["PQ"], 2, "p"), 0, py)
    # Local storage-node connections: horizontal M2 stubs, two M3 feedback
    # trunks. No global escape for internal Q/QB.
    # Join common drains in M1 before escaping. Putting VIA1 on every 90nm
    # S/D column violated VIA1.S.1/1.1; place one via on each outward net bar.
    wire(body, 1, -.307, .077, -.037, .077, end=.019)
    wire(body, 1, .143, .077, .413, .077, end=.019)
    wire(body, 1, -.245, py+.029, -.037, py+.029, end=.019)
    wire(body, 1, .143, py+.029, .350, py+.029, end=.019)
    rect(body, 31, .025, py-.039, .081, py+.093)
    q = [(-.180, .077), (.098, -.129),
         (-.180, py+.029), (.098, py-.119)]
    qb = [(.286, .077), (-.100, .333),
          (.286, py+.029), (.008, py+.177)]
    rect(body, 31, -.119, .264, -.081, .374)
    for xtrunk, pts in ((-.180, q), (.286, qb)):
        for x, y in pts:
            via(body, 1, x, y)
            wire(body, 2, x, y, xtrunk, y, width=.064, end=.064)
            via(body, 2, xtrunk, y)
        wire(body, 3, xtrunk, min(y for x, y in pts),
             xtrunk, max(y for x, y in pts), end=.064)
    for x in (-.352, .458):
        via(body, 1, x, .225)
    wire(body, 2, -.352, .225, .458, .225, end=.064)
    label(body, "WL", 2, -.30, .225)
    label(body, "BL", 1, -.397, .077)
    label(body, "BLB", 1, .503, .077)
    # Shared diagnostic taps at left; later context must amortize them legally.
    for kind, x, y, net in (("SUB", -.990, .053, "VSS"),
                            ("NW", -.990 if compact else -.640,
                             py+.053, "VDD")):
        body["references"].append(ref(native[kind].name, x, y))
        rect(body, 250, x-.260, y-.149, x+.260, y+.149)
        rect(body, 31, x-.041, y-.043, x+.041, y+.043)
        sy = .077 if kind == "SUB" else py+.029
        for vx, vy in ((x, y), (.053, sy)):
            via(body, 1, vx, vy)
            via(body, 2, vx, vy)
            via(body, 3, vx, vy)
            rect(body, 32, vx-.102, vy-.032, vx+.102, vy+.032, 70)
            rect(body, 33, vx-.032, vy-.064, vx+.032, vy+.064, 70)
        rect(body, 34, x-.064, min(y, sy)-.064, .117, max(y, sy)+.064, 150)
        label(body, net, 4, x/2, sy)
    # SVT N/P regions abut without overlap. Their union has no artificial
    # 116nm gap; individual enclosure and extraction remain checked.
    rect(body, 23, -1.250, -.230, .771, py-.220)
    rect(body, 24, -1.250 if compact else -.900, py-.220, .411, py+.278)
    rect(body, 3, -1.250 if compact else -.900, py-.220, .411, py+.278)
    rect(body, 108, -1.250, -.259, .774, py+.317)
    cells["sram6t_core"] = body
    if compact:
        # Discrete shared-cut experiment: move P row by three fin pitches
        # (144nm), align its lower cut exactly with the N-row upper cut.
        # Gate escape shifts 4nm; OD/channel/fin dimensions are unchanged.
        # A monotone y map preserves all local routes and the 48nm OD phase.
        for p in body["polygons"]:
            layer, dt = p["layer"], p["datatype"]
            pts = p["points_um"]
            for pt in pts:
                y = pt[1]
                if y >= .490:
                    pt[1] = round(y-.144, 6)
            if layer in (17, 84, 159, 31, 32, 51, 52):
                lo = min(v[1] for v in pts)
                hi = max(v[1] for v in pts)
                # P-row downward gate contact and lower CPO only.
                if layer == 17 and dt == 11 and .340 < lo < .360:
                    for pt in pts:
                        pt[1] = round(pt[1]-.032, 6)
                elif layer != 17 and .420 < lo and hi < .510:
                    for pt in pts:
                        pt[1] = round(pt[1]+.004, 6)
            if (layer == 31 and abs(min(v[0] for v in pts)-.124) < 1e-6
                    and abs(max(v[0] for v in pts)-.162) < 1e-6
                    and .55 < min(v[1] for v in pts) < .56):
                ymin = min(v[1] for v in pts)
                for pt in pts:
                    if pt[1] == ymin:
                        pt[1] = round(pt[1]+.004, 6)
                    pt[0] = .115 if pt[0] < .143 else .171
            if layer == 17 and dt in (0, 7):
                for pt in pts:
                    if abs(pt[1]-.380) < 1e-6:
                        pt[1] = .348
        for r in body["references"]:
            if r["origin_um"][1] > .5:
                r["origin_um"][1] = round(r["origin_um"][1]-.144, 6)
        for l in body["labels"]:
            if l["origin_um"][1] > .5:
                l["origin_um"][1] = round(l["origin_um"][1]-.144, 6)
        # Set implant ownership at a legal N/P abutment, never overlap VT_N/P.
        for p in body["polygons"]:
            if p["layer"] == 23:
                for pt in p["points_um"]:
                    if pt[1] > .25:
                        pt[1] = .360
            elif p["layer"] == 24:
                for pt in p["points_um"]:
                    if pt[1] < .5:
                        pt[1] = .360
            elif p["layer"] == 25 and min(v[1] for v in p["points_um"]) > .3:
                for pt in p["points_um"]:
                    if pt[1] < .400:
                        pt[1] = .360
    if compact_x:
        assert compact
        # Move access columns one 90nm gate pitch inward; preserve channel
        # sizes. Remove now-redundant gap dummies before merging new boundaries.
        filtered = []
        for p in body["polygons"]:
            xs = [v[0] for v in p["points_um"]]
            ys = [v[1] for v in p["points_um"]]
            xmin, xmax, ymax = min(xs), max(xs), max(ys)
            if (p["layer"], p["datatype"]) == (17, 7) and ymax < .4 and (
                    abs(xmin+.180) < 1e-6 or abs(xmin-.270) < 1e-6):
                continue
            if (p["layer"], p["datatype"]) == (84, 0) and ymax < .2 and any(
                    abs((xmin+xmax)/2-x) < 1e-6 for x in (-.217, -.127, .233, .323)):
                continue
            filtered.append(p)
        body["polygons"] = filtered
        def mx(x):
            if x <= -.700:
                return round(x+.098, 6)
            if x <= -.254:
                return round(x+.090, 6)
            if x >= .360:
                return round(x-.090, 6)
            return x
        for p in body["polygons"]:
            nrow = max(v[1] for v in p["points_um"]) < .400
            top_gate = (p["layer"] in (31, 32, 51, 52, 159) or
                        (p["layer"], p["datatype"]) == (84, 2)) and (
                            min(v[1] for v in p["points_um"]) > .700 and
                            max(v[1] for v in p["points_um"]) < .800)
            left_p_sd = (p["layer"] == 31 and
                         abs(min(v[0] for v in p["points_um"])+.056) < 1e-6 and
                         abs(max(v[0] for v in p["points_um"])+.018) < 1e-6 and
                         .53 < min(v[1] for v in p["points_um"]) < .55)
            for pt in p["points_um"]:
                if top_gate:
                    pt[1] = round(pt[1]-.020, 6)
                if left_p_sd:
                    pt[0] = -.062 if pt[0] < -.037 else -.012
                    if pt[1] > .646:
                        pt[1] = .646
                if p["layer"] == 31 and abs(min(v[0] for v in p["points_um"])-.025) < 1e-6:
                    pt[0] = .028 if pt[0] < .053 else .078
                if nrow:
                    pt[0] = mx(pt[0])
                elif pt[0] < -.700:
                    pt[0] = round(pt[0]+.098, 6)
                elif p["layer"] == 108 and pt[0] > .700:
                    pt[0] = round(pt[0]-.090, 6)
                if pt[0] < -1.117:
                    pt[0] = -1.117
                if p["layer"] in (3, 24) and pt[1] > .830:
                    pt[1] = .838
                if p["layer"] == 17 and p["datatype"] == 11 and pt[1] > .850:
                    pt[1] = .838
                elif p["layer"] == 17 and p["datatype"] == 11 and abs(pt[1]-.790) < 1e-6:
                    pt[1] = .770
                if p["layer"] == 17 and p["datatype"] in (0, 7) and abs(pt[1]-.830) < 1e-6:
                    pt[1] = .810
                if p["layer"] == 108 and pt[1] > .850:
                    pt[1] = .845
        for item in body["references"] + body["labels"]:
            if item["origin_um"][1] < .4 or item["origin_um"][0] < -.7:
                item["origin_um"][0] = mx(item["origin_um"][0])
        # Gate pad straddled the piecewise placement boundary; move the entire
        # pad, preserving its legal 204nm length.
        rect(body, 31, .228, .206, .432, .244)
        for x in (-.127, .233):
            rect(body, 84, x-.020, -.012, x+.020, .166)
    source = (OLD / "sram6t12_v1_layout_v2_lvs/source.cdl").read_text()
    return cells, "sram6t_core", source, "sram6t12_v1"


def seam_context(columns=2, pitch=.900):
    """Horizontal diagnostic seam with independent BL/BLB/WL for each bit.

    Only one physical pair of body taps. Dummies and local contacts are owned
    by the actual outside edge. This is not a production SRAM array.
    """
    assert 2 <= columns <= 8
    cells, leaf, source, source_top = sram6t(True, True)
    base = cells.pop(leaf)
    top = empty_cell(deepcopy(base["references"]))
    assert pitch in (.810, .900), "Declared diagnostic pitch neighborhood only"
    for p in base["polygons"]:
        xmax = max(v[0] for v in p["points_um"])
        if xmax < -.700:
            top["polygons"].append(deepcopy(p))
    for i in range(columns):
        bit = empty_cell()
        for p in base["polygons"]:
            layer, dt = p["layer"], p["datatype"]
            xmin = min(v[0] for v in p["points_um"])
            xmax = max(v[0] for v in p["points_um"])
            ymax = max(v[1] for v in p["points_um"])
            if xmax < -.700 or layer == 108:
                continue
            if layer == 17 and dt == 7 and ymax < .4:
                if (i > 0 and xmin < -.36) or (i < columns-1 and xmin > .45):
                    continue
            if layer == 84 and dt == 0 and ymax < .2:
                xc = (xmin+xmax)/2
                if (i > 0 and xc < -.36) or (i < columns-1 and xc > .55):
                    continue
            append_polygon(bit, layer, dt,
                           affinity.translate(Polygon(p["points_um"]), i*pitch, 0))
        for l in base["labels"]:
            if l["text"] not in ("BL", "BLB", "WL"):
                continue
            ll = deepcopy(l)
            ll["text"] += str(i)
            ll["origin_um"][0] += i*pitch
            bit["labels"].append(ll)
        top["polygons"].extend(bit["polygons"])
        top["labels"].extend(bit["labels"])
    for net, y in (("VSS", .077), ("VDD", .605)):
        label(top, net, 4, -.5, y)
    rect(top, 108, -1.117, -.259, .684+(columns-1)*pitch, .845)
    cells["sram_seam"] = top
    ports = [f"{p}{i}" for i in range(columns) for p in ("BL", "BLB", "WL")]
    source += "\n.SUBCKT sram_seam_source " + " ".join(ports + ["VDD", "VSS"]) + "\n"
    for i in range(columns):
        source += f"X{i} BL{i} BLB{i} WL{i} VDD VSS {source_top}\n"
    source += ".ENDS sram_seam_source\n"
    return cells, "sram_seam", source, "sram_seam_source"
