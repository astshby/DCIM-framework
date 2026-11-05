"""Process-neutral geometry utilities; explicit layer maps and verified bridge required."""
from collections import Counter
from decimal import Decimal
from functools import lru_cache
import math
import re


ORIENTATIONS = {
    (0, False): "R0", (90, False): "R90", (180, False): "R180", (270, False): "R270",
    (0, True): "MX", (90, True): "MXR90", (180, True): "MY", (270, True): "MYR90",
}


def transform(point, rotation=0, reflected=False):
    x, y = map(float, point)
    if reflected:
        y = -y
    angle = round(float(rotation or 0)) % 360
    if abs(float(rotation or 0) % 90) > 1e-8 or angle not in (0, 90, 180, 270):
        raise ValueError(f"Non-orthogonal reference not supported: {rotation}")
    return ((x, y), (-y, x), (-x, -y), (y, -x))[angle // 90]


def expanded_refs(entry):
    """GDS array vectors rotate/reflect with the array; do not use world-axis pitch."""
    ox, oy = entry["origin_um"]
    sx, sy = entry.get("spacing_um") or (0, 0)
    for col in range(entry.get("columns", 1)):
        for row in range(entry.get("rows", 1)):
            dx, dy = transform((col * sx, row * sy), entry.get("rotation_deg", 0),
                               entry.get("x_reflection", False))
            yield {
                "child": entry["child"], "origin_um": [round(ox + dx, 9), round(oy + dy, 9)],
                "rotation_deg": entry.get("rotation_deg", 0) or 0,
                "x_reflection": entry.get("x_reflection", False),
                "columns": 1, "rows": 1, "spacing_um": None,
            }


def empty_cell(refs=None):
    return {"polygons": [], "labels": [], "references": list(refs or [])}


def read_gds(path):
    import gdspy
    return gdspy.GdsLibrary(infile=str(path))


def capture_closure(library, roots):
    """Capture parent-owned wires/shapes too. No GDS writing or geometry mutation."""
    result = {}

    def visit(name):
        if name in result:
            return
        cell = library.cells[name]
        record = empty_cell()
        result[name] = record
        for shape in cell.polygons:
            for points, layer, datatype in zip(shape.polygons, shape.layers, shape.datatypes):
                record["polygons"].append({"layer": int(layer), "datatype": int(datatype),
                                           "points_um": points.tolist()})
        for path in cell.paths:
            for (layer, datatype), polygons in path.get_polygons(by_spec=True).items():
                for points in polygons:
                    record["polygons"].append({"layer": int(layer), "datatype": int(datatype),
                                               "points_um": points.tolist()})
        for label in cell.labels:
            record["labels"].append({
                "layer": int(label.layer), "datatype": int(label.texttype),
                "text": label.text, "origin_um": label.position.tolist(),
                "rotation_deg": label.rotation or 0, "x_reflection": label.x_reflection,
                "anchor": int(label.anchor), "magnification": label.magnification or 1,
            })
        for ref in cell.references:
            if ref.magnification not in (None, 1):
                raise ValueError(f"Scaled reference unsupported: {name}/{ref.ref_cell.name}")
            visit(ref.ref_cell.name)
            record["references"].append({
                "child": ref.ref_cell.name, "origin_um": list(map(float, ref.origin)),
                "rotation_deg": ref.rotation or 0, "x_reflection": bool(ref.x_reflection),
                "columns": int(getattr(ref, "columns", 1)), "rows": int(getattr(ref, "rows", 1)),
                "spacing_um": list(map(float, ref.spacing)) if hasattr(ref, "spacing") else None,
            })
    for name in roots:
        visit(name)
    return result


def topo_order(cells, top):
    order, visiting, visited = [], set(), set()

    def visit(name):
        if name in visiting:
            raise ValueError(f"Hierarchy cycle: {name}")
        if name in visited:
            return
        visiting.add(name)
        for ref in cells[name]["references"]:
            visit(ref["child"])
        visiting.remove(name)
        visited.add(name)
        order.append(name)
    visit(top)
    return order


def hierarchy_counts(cells, top):
    @lru_cache(None)
    def count(name):
        counts = Counter({name: 1})
        for ref in cells[name]["references"]:
            multiplicity = ref.get("columns", 1) * ref.get("rows", 1)
            counts.update({k: v * multiplicity for k, v in count(ref["child"]).items()})
        return counts
    topo_order(cells, top)
    return dict(count(top))


def bbox(cells, top):
    @lru_cache(None)
    def box(name):
        points = [pt for poly in cells[name]["polygons"] for pt in poly["points_um"]]
        for ref0 in cells[name]["references"]:
            child = box(ref0["child"])
            if child is None:
                continue
            x0, y0, x1, y1 = child
            for ref in expanded_refs(ref0):
                for point in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)):
                    x, y = transform(point, ref["rotation_deg"], ref["x_reflection"])
                    points.append([x + ref["origin_um"][0], y + ref["origin_um"][1]])
        if not points:
            return None
        return (min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points))
    return box(top)


def layer_map(path):
    mapping = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) == 4 and fields[2].isdigit() and fields[3].isdigit():
            key = (int(fields[2]), int(fields[3]))
            value = fields[:2]
            if key in mapping and mapping[key] != value:
                prior = mapping[key]
                if isinstance(prior, dict):
                    if value not in prior["ambiguous"]:
                        prior["ambiguous"].append(value)
                else:
                    mapping[key] = {"ambiguous": [prior, value]}
            else:
                mapping[key] = value
    return mapping


def emit_skill(cells, top, target_lib, prefix, mapping):
    """All final drawing uses documented bridge builders and native Virtuoso DB calls."""
    from virtuoso_bridge.virtuoso.layout import (
        layout_create_polygon, layout_create_label, layout_create_param_inst,
    )
    from virtuoso_bridge.virtuoso.ops import (
        open_cell_view, save_current_cellview, close_current_cellview,
    )
    # Bridge builders use :g; floats would default to six significant digits.
    # Decimal keeps sub-nm resolution at large hierarchical source coordinates.
    number = lambda value: Decimal(format(float(value), ".12g"))
    point = lambda xy: tuple(number(value) for value in xy)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,35}", target_lib):
        raise ValueError("Use an explicit simple scratch-library name")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,20}", prefix):
        raise ValueError("Invalid unique cell prefix")
    order = topo_order(cells, top)
    names = {name: f"{prefix}_{i:03d}" for i, name in enumerate(order)}
    names[top] = f"{prefix}_top"
    # Preflight everything before creating any cell.
    used = {(shape["layer"], shape["datatype"]) for name in order
            for key in ("polygons", "labels") for shape in cells[name][key]}
    missing = used - mapping.keys()
    if missing:
        raise ValueError(f"Unmapped GDS layers: {sorted(missing)}")
    ambiguous = {key: mapping[key] for key in used if isinstance(mapping[key], dict)}
    if ambiguous:
        raise ValueError(f"Used GDS layers need explicit alias selection: {ambiguous}")
    lines = ['; Generated candidate. Geometry only: DRC/LVS/function NOT implied.',
             'let((cv)',
             f'  unless(ddGetObj("{target_lib}") error("Target scratch library is absent\\n"))']
    for name in order:
        lines.append(f'  when(ddGetObj("{target_lib}" "{names[name]}") '
                     'error("Destination cell already exists; use a new prefix\\n"))')
    # All guards precede creation so a repeat load cannot partially overwrite the run.
    justifications = {
        0: "upperLeft", 1: "upperCenter", 2: "upperRight",
        4: "centerLeft", 5: "centerCenter", 6: "centerRight",
        8: "lowerLeft", 9: "lowerCenter", 10: "lowerRight",
    }
    for name in order:
        lines.append("  " + open_cell_view(target_lib, names[name], mode="w"))
        lines.append('  unless(cv error("Unable to create candidate cell\\n"))')
        for poly in cells[name]["polygons"]:
            layer, purpose = mapping[poly["layer"], poly["datatype"]]
            op = layout_create_polygon(layer, purpose, map(point, poly["points_um"]))
            lines.append('  unless(' + op + ' error("Polygon creation failed\\n"))')
        for label in cells[name]["labels"]:
            layer, purpose = mapping[label["layer"], label["datatype"]]
            rot = ORIENTATIONS[int(label["rotation_deg"]) % 360, label["x_reflection"]]
            op = layout_create_label(layer, purpose, *point(label["origin_um"]), label["text"],
                                     justifications[label["anchor"]], rot, "roman",
                                     0.1 * label["magnification"])
            lines.append('  unless(' + op + ' error("Label creation failed\\n"))')
        serial = 0
        for ref0 in cells[name]["references"]:
            for ref in expanded_refs(ref0):
                rot = ORIENTATIONS[int(ref["rotation_deg"]) % 360, ref["x_reflection"]]
                op = layout_create_param_inst(target_lib, names[ref["child"]], "layout",
                                               f"I{serial}", *point(ref["origin_um"]), rot)
                lines.append('  unless(' + op + ' error("Instance creation failed\\n"))')
                serial += 1
        lines.append('  unless(' + save_current_cellview() + ' error("Save failed\\n"))')
        lines.append("  " + close_current_cellview())
    lines += [f'  printf("DCIM_GENERATED {target_lib}/{names[top]}\\n")', "  t", ")"]
    # A single large form also exhausts Virtuoso's value stack even with progn
    # chunks. Emit independent bounded forms and retain one uniquely named DB
    # handle across them. errset + error preserves fail-fast load behavior.
    variable = prefix + "_cv"
    body = lines[2:-1]
    chunked = [lines[0], f"{variable} = nil"]
    for start in range(0, len(body), 200):
        chunked += [f"unless(errset(let((cv) cv = {variable}"] + body[start:start+200]
        chunked += [f"  {variable} = cv", "  t", ') t) error("Candidate generation chunk failed\\n"))']
    chunked += [f"{variable} = nil", "t"]
    return "\n".join(chunked) + "\n", names
