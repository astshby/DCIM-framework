"""Read-only evidence tools; measurements are not design admission decisions."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys


VERSION = "2"


class EvidenceError(ValueError):
    def __init__(self, message, status="incomplete"):
        super().__init__(message)
        self.status = status


def require(condition, message, status="incomplete"):
    if not condition:
        raise EvidenceError(message, status)


def absolute(value):
    path = Path(value)
    require(path.is_absolute(), "Evidence paths must be absolute: " + str(path))
    return path.resolve(strict=True)


def fingerprint(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "bytes": size}


def within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def relative_file(value):
    path = Path(value)
    require(not path.is_absolute() and path.parts and '..' not in path.parts
            and path.as_posix() == value, "Invalid relative dependency path")
    return path


def freeze(paths, output, base_root=None):
    """Fingerprint files in place; an explicit common root opts into portable v2."""
    require(output.is_absolute(), "Manifest output path must be absolute")
    base = absolute(base_root) if base_root is not None else None
    resolved = sorted({absolute(base / p if base is not None else p) for p in paths})
    require(resolved, "No dependencies supplied")
    require(output.resolve() not in resolved, "Manifest cannot include itself")
    manifest = {"schema_version": 1, "files": [
        {"path": str(p), **fingerprint(p)} for p in resolved]}
    if base is not None:
        require(base.is_dir() and within(output.resolve(), base),
                "Portable manifest must be inside its base root")
        require(all(within(p, base) for p in resolved), "Dependency escapes base root")
        manifest = {"schema_version": 2,
                    "base_root": os.path.relpath(str(base), str(output.parent.resolve())),
                    "origin_path": str(base),
                    "files": [{"path": p.relative_to(base).as_posix(), **fingerprint(p)}
                              for p in resolved]}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    return manifest


class Frozen:
    def __init__(self, manifest):
        self.path = absolute(manifest)
        self.identity = fingerprint(self.path)
        data = json.loads(self.path.read_text())
        require(isinstance(data, dict), "Manifest must be a JSON object")
        self.version = data.get("schema_version")
        require(self.version in (1, 2), "Unsupported manifest schema")
        self.entries = {}
        self.origins = {}
        self.aliases = {}
        self.base = None
        if self.version == 2:
            locator = Path(data["base_root"])
            require(not locator.is_absolute(), "Base root must be manifest-relative")
            self.base = (self.path.parent / locator).resolve(strict=True)
            require(self.base.is_dir() and within(self.path, self.base),
                    "Manifest escapes base root")
            origin = Path(data["origin_path"])
            require(origin.is_absolute() and '..' not in origin.parts,
                    "Origin must be an absolute provenance path")
        require(isinstance(data.get("files"), list) and data["files"],
                "Manifest needs explicit files")
        for entry in data["files"]:
            require(isinstance(entry, dict), "Invalid manifest file entry")
            if self.version == 1:
                path = absolute(entry["path"])
                require(str(path) == entry["path"], "Manifest paths must be resolved")
                recorded = str(path)
            else:
                relative = relative_file(entry["path"])
                path = self.base / relative
                require(within(path.resolve(strict=True), self.base), "Dependency escapes base root")
                recorded = str(origin / relative)
            require(path not in self.entries, "Duplicate manifest path")
            self.entries[path] = entry
            self.origins[path] = recorded
            for alias in (str(path), recorded):
                require(alias not in self.aliases or self.aliases[alias] == path,
                        "Ambiguous dependency alias")
                self.aliases[alias] = path
        self.verify()

    def verify(self):
        require(fingerprint(self.path) == self.identity, "Manifest changed during read")
        for path, entry in self.entries.items():
            if self.base is not None:
                require(within(path.resolve(strict=True), self.base), "Dependency escapes base root")
            require(fingerprint(path) == {k: entry[k] for k in ("sha256", "bytes")},
                    "Frozen dependency changed: " + str(path))

    def path_for(self, value):
        if self.version == 2:
            # Old absolute spellings are exact aliases, never filesystem fallbacks.
            path = self.aliases.get(str(value))
            if path is None and not Path(value).is_absolute():
                path = self.base / relative_file(str(value))
        else:
            path = absolute(value)
        require(path in self.entries, "Unbound evidence: " + str(path))
        if self.base is not None:
            require(within(path.resolve(strict=True), self.base), "Dependency escapes base root")
        return path

    def recorded_path(self, value):
        """Check historical deck/report bindings against the original execution spelling."""
        return self.origins[self.path_for(value)]

    def text(self, value):
        return self.path_for(value).read_text()

    def json(self, value):
        return json.loads(self.text(value))


def parse_drc(text, expected_rules=None):
    rows = re.findall(
        r"^RULECHECK (\S+).*?TOTAL Result Count = (\d+)\s+\((\d+)\)\s*$",
        text, re.M)
    totals = re.findall(r"^TOTAL DRC Results Generated:\s+(\d+)\s+\((\d+)\)\s*$",
                        text, re.M)
    executed = re.findall(r"^TOTAL DRC RuleChecks Executed:\s+(\d+)\s*$", text, re.M)
    require(rows and len(totals) == 1 and len(executed) == 1,
            "Missing or ambiguous DRC rows/footer", "unsupported")
    require(len(rows) == int(executed[0]), "Incomplete DRC rule coverage")
    require(len({r[0] for r in rows}) == len(rows), "Duplicate DRC rule rows")
    if expected_rules is not None:
        require(type(expected_rules) is int and expected_rules > 0,
                "expected_rules must be a positive deck-specific count")
        require(len(rows) == expected_rules, "Unexpected deck-specific rule coverage")
    counts = [sum(int(r[i]) for r in rows) for i in (1, 2)]
    require(counts == [int(v) for v in totals[0]], "Inconsistent DRC totals")
    return {"status": "passed" if counts == [0, 0] else "failed",
            "rule_count": len(rows), "actual_expanded": counts,
            "nonzero": {name: [int(a), int(b)] for name, a, b in rows
                        if int(a) or int(b)}}


def parse_lvs(text, layout_top, source_top):
    require("OVERALL COMPARISON RESULTS" in text and "CELL  SUMMARY" in text,
            "Unsupported LVS report", "unsupported")
    rows = re.findall(r"^\s*(CORRECT|INCORRECT|NOT COMPARED)\s+(\S+)\s+(\S+)\s*$",
                      text, re.M)
    matches = [r for r in rows if r[1:] == (layout_top, source_top)]
    require(len(matches) == 1, "Missing/ambiguous LVS top-pair result")
    require("NUMBERS OF OBJECTS AFTER TRANSFORMATION" in text,
            "Incomplete LVS report: missing object summary")
    require(re.search(r"^Total CPU Time:\s+\S.*$", text, re.M)
            and re.search(r"^Total Elapsed Time:\s+\S.*$", text, re.M),
            "Incomplete LVS report: missing terminal timing summary")
    banner = text.split("OVERALL COMPARISON RESULTS", 1)[1].split("CELL  SUMMARY", 1)[0]
    banner_results = set(re.findall(r"\b(?:INCORRECT|CORRECT|NOT COMPARED)\b", banner))
    if banner_results:
        require(banner_results == {matches[0][0]}, "Inconsistent LVS overall/top results")
    bad = [r for r in rows if r[0] != "CORRECT"]
    return {"status": "passed" if matches[0][0] == "CORRECT" and not bad else "failed",
            "top_result": matches[0][0], "noncorrect_cells": bad,
            "errors": re.findall(r"^\s*Error:.*$", text, re.M)[:12]}


def pv(spec, frozen):
    kind = spec["kind"]
    require(kind in ("drc", "lvs"), "Unknown PV kind", "unsupported")
    gds = frozen.path_for(spec["gds"])
    source = frozen.path_for(spec["source"])
    original = frozen.path_for(spec["original_deck"])
    run = frozen.path_for(spec["run_deck"])
    record = frozen.json(spec["execution_inputs"])
    for key, path in (("gds_sha256", gds), ("source_sha256", source),
                      ("original_deck_sha256", original), ("run_deck_sha256", run)):
        require(record.get(key) == fingerprint(path)["sha256"],
                "Execution-time input binding mismatch: " + key)
    expected = original.read_text()
    for old, new in spec["replacements"]:
        require(old and old in expected, "Deck replacement does not match")
        expected = expected.replace(old, new)
    text = run.read_text()
    require(expected == text, "Unlisted deck modification", "failed")
    for field, value in (("LAYOUT PATH", frozen.recorded_path(spec["gds"])), ("LAYOUT PRIMARY", spec["top"])):
        require(re.search(r"^" + field + r'\s+"' + re.escape(value) + r'"\s*$',
                          text, re.M), "Run deck binding mismatch: " + field)
    report = frozen.text(spec["report"])
    if kind == "drc":
        require(re.search(r"^Layout Primary Cell:\s+" + re.escape(spec["top"])
                          + r"\s*$", report, re.M), "DRC report top mismatch")
        require(re.search(r"^Layout Path\(s\):\s+" + re.escape(frozen.recorded_path(spec["gds"]))
                          + r"\s*$", report, re.M), "DRC report GDS mismatch")
        result = parse_drc(report, spec.get("expected_rules"))
    else:
        for field, value in (("SOURCE PATH", frozen.recorded_path(spec["source"])),
                             ("SOURCE PRIMARY", spec["source_top"])):
            require(re.search(r"^" + field + r'\s+"' + re.escape(value) + r'"\s*$',
                              text, re.M), "Run deck binding mismatch: " + field)
        require(re.search(r"^SOURCE NAME:\s+" + re.escape(frozen.recorded_path(spec["source"]))
                          + r"\s+\('" + re.escape(spec["source_top"]) + r"'\)\s*$",
                          report, re.M), "LVS report source mismatch")
        result = parse_lvs(report, spec["top"], spec["source_top"])
    return {**result, "scope": kind + " report and declared deck/input bindings",
            "report": str(frozen.path_for(spec["report"])),
            "limitation": "Frozen files do not independently prove job provenance; "
                          "review terminal job record and warnings."}


def geometry(spec, frozen):
    import gdspy
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    def read(path, top):
        lib = gdspy.GdsLibrary(infile=str(frozen.path_for(path)), units="import")
        require(top in lib.cells, "GDS top is absent")
        cell = lib.cells[top]
        require(not any(isinstance(ref.ref_cell, str)
                        for c in [cell, *cell.get_dependencies(True)]
                        for ref in c.references), "Unresolved GDS reference")
        bbox = cell.get_bounding_box()
        require(bbox is not None, "Empty GDS top")
        scale = lib.unit / 1e-6
        bounds = (bbox * scale).tolist()
        width, height = (bbox[1] - bbox[0]) * scale
        masks = cell.get_polygons(by_spec=True)
        selected = {}
        for layer, datatype in spec.get("layers", []):
            polys = [Polygon(p * scale) for p in masks.get((layer, datatype), [])]
            require(all(p.is_valid for p in polys), "Invalid polygon; no silent repair")
            selected[(layer, datatype)] = unary_union(polys)
        return {"bbox_um": bounds, "width_um": float(width), "height_um": float(height),
                "bbox_area_um2": float(width * height),
                "direct_references": len(cell.references),
                "dependency_cells": sorted(c.name for c in cell.get_dependencies(True)),
                "layer_union_um2": {f"{a}/{b}": p.area for (a, b), p in selected.items()}}, selected

    result, masks = read(spec["gds"], spec["top"])
    status = "passed"
    if "band_y_um" in spec:
        low, high = spec["band_y_um"]
        require(math.isfinite(low) and math.isfinite(high) and low <= high, "Invalid band")
        result["in_band"] = result["bbox_um"][0][1] >= low - 1e-9 and (
            result["bbox_um"][1][1] <= high + 1e-9)
        if not result["in_band"]:
            status = "failed"
    if "compare_gds" in spec:
        require(masks, "Explicit layers required for mask comparison")
        other, comparison = read(spec["compare_gds"], spec["compare_top"])
        result["comparison"] = other
        result["xor_um2"] = {f"{a}/{b}": mask.symmetric_difference(
            comparison[(a, b)]).area for (a, b), mask in masks.items()}
    return {"status": status, "scope": "geometry measurement; no connectivity/DRC proof",
            "readers": {"gdspy": gdspy.__version__}, **result}


def sample_vectors(data, vector, spec):
    def real(name):
        values = vector(data, name)
        require(all(complex(v).imag == 0 and math.isfinite(complex(v).real)
                    for v in values), "Nonfinite/complex transient vector")
        return [float(complex(v).real) for v in values]

    times = real(spec.get("time_signal", "time"))
    require(len(times) >= 2 and all(b > a for a, b in zip(times, times[1:])),
            "Time must be strictly increasing")
    samples = spec["sample_times_s"]
    signals = spec["signals"]
    require(samples and signals and len(set(signals)) == len(signals),
            "Require samples and distinct signal names")
    require(all(math.isfinite(t) and times[0] <= t <= times[-1] for t in samples),
            "Sample outside waveform coverage")
    from bisect import bisect_right
    result = {}
    for name in signals:
        values = real(name)
        require(len(values) == len(times), "Signal/time length mismatch: " + name)
        out = []
        for t in samples:
            i = min(bisect_right(times, t) - 1, len(times) - 2)
            alpha = (t - times[i]) / (times[i + 1] - times[i])
            out.append(values[i] + alpha * (values[i + 1] - values[i]))
        result[name] = out
    return {"status": "passed", "scope": "waveform read/sampling, not circuit correctness",
            "time_range_s": [times[0], times[-1]], "sample_times_s": samples,
            "signals": result}


def wave(spec, frozen):
    from virtuoso_bridge.spectre.psf import read_psf_ascii, vector

    require(spec.get("format") == "psf_ascii", "Only PSF ASCII is supported", "unsupported")
    path = frozen.path_for(spec["psf"])
    result = sample_vectors(read_psf_ascii(path), vector, spec)
    module_path = Path(sys.modules[read_psf_ascii.__module__].__file__)
    result["reader"] = {"path": str(module_path), **fingerprint(module_path)}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("freeze", help="Snapshot explicitly selected dependencies")
    command.add_argument("--out", required=True, type=Path)
    command.add_argument("--base-root", type=Path,
                         help="Absolute common root for portable v2; move this whole tree together")
    command.add_argument("files", nargs="+")
    command = sub.add_parser("check", help="Verify a frozen dependency manifest")
    command.add_argument("manifest")
    for name in ("pv", "gds", "wave"):
        command = sub.add_parser(name, help={
            "pv": "Check Calibre reports and declared execution/deck bindings",
            "gds": "Measure hierarchical geometry and selected-layer mask XOR",
            "wave": "Read and sample PSF ASCII (no circuit acceptance oracle)",
        }[name])
        command.add_argument("spec", help="Frozen JSON path; v2 also accepts base-relative or recorded origin paths")
        command.add_argument("--manifest", required=True)
    args = parser.parse_args(argv)
    base = {"tool_version": VERSION, "tool_sha256": fingerprint(Path(__file__))["sha256"],
            "command": args.command}
    try:
        if args.command == "freeze":
            result = {"status": "passed", "scope": "fingerprint snapshot only",
                      "manifest": freeze(args.files, args.out, args.base_root)}
        else:
            frozen = Frozen(args.manifest)
            if args.command == "check":
                result = {"status": "passed", "scope": "dependency identity only"}
            else:
                spec = frozen.json(args.spec)
                result = {"pv": pv, "gds": geometry, "wave": wave}[args.command](spec, frozen)
            frozen.verify()
            result["manifest"] = str(frozen.path)
            result["manifest_sha256"] = frozen.identity["sha256"]
        output = {**base, **result}
    except ImportError as error:
        output = {**base, "status": "unsupported", "diagnostic": str(error)}
    except EvidenceError as error:
        output = {**base, "status": error.status, "diagnostic": str(error)}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        output = {**base, "status": "incomplete", "diagnostic": str(error)}
    print(json.dumps(output, indent=2, allow_nan=False))
    return {"passed": 0, "failed": 1, "incomplete": 2, "unsupported": 3}[output["status"]]


if __name__ == "__main__":
    sys.exit(main())
