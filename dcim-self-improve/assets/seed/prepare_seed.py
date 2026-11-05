"""Generate one initial candidate locally; no EDA or bridge calls are executed."""

import argparse
import gzip
import json
from pathlib import Path
import re

from seed_config import configure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Private JSON config (or DCIM_CONFIG)")
    parser.add_argument("--id", required=True)
    parser.add_argument("--kind", choices=("pair", "sram", "seam", "lrcc", "fa"),
                        default="sram")
    parser.add_argument("--geometry-only", action="store_true")
    parser.add_argument("--library", help="Existing scratch OA library; emission only")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,15}", args.id):
            raise ValueError("Candidate ID must start with a letter; at most 16 simple characters")
        if not args.geometry_only and not args.library:
            raise ValueError("Supply --library or use --geometry-only")
        settings = configure(args.config)
        check = settings.check("seed")
        if not check["passed"]:
            missing = [r["path"] or r["key"] for r in check["checks"] if not r["present"]]
            raise ValueError("Missing native reference inputs: " + ", ".join(missing))
        output = settings.ensure_output(settings.path("work_root") / "candidates" / args.id)
        if output.exists():
            raise FileExistsError(f"Candidate already exists: {output}")
        from geometry import bbox, emit_skill, layer_map
        from core_geometry import diagnostic_pair, seam_context, sram6t

        if args.kind == "fa":
            from fa_geometry import fa22t
            cells, top, source, source_top = fa22t()
        elif args.kind == "lrcc":
            from logic_geometry import lrcc
            cells, top, source, source_top = lrcc()
        else:
            cells, top, source, source_top = {
                "pair": diagnostic_pair, "sram": sram6t, "seam": seam_context,
            }[args.kind]()
        il = names = None
        if not args.geometry_only:
            mapping = settings.path("pdk_root") / "tsmcN12" / "tsmcN12.layermap"
            il, names = emit_skill(cells, top, args.library, "c" + args.id, layer_map(mapping))
        bounds = bbox(cells, top)
        result = {
            "kind": args.kind, "top": names[top] if names else top,
            "source_top": source_top, "library": args.library if il else None,
            "bbox_um": bounds,
            "full_mask_bbox_area_um2": (
                (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]) if bounds else None),
            "area_scope": "standalone full-mask bbox; not repeat pitch or qualified macro",
            "accepted": False, "eda_launched": False,
            "drc": "not_run", "lvs": "not_run",
            "schematic_function": "not_run", "pex": "not_run", "post_layout": "not_run",
        }
        output.mkdir(parents=True, exist_ok=False)
        (output / "source.cdl").write_text(source, encoding="utf-8")
        with gzip.open(output / "geometry.json.gz", "wt", encoding="utf-8") as stream:
            json.dump(cells, stream)
        if il is not None:
            (output / "layout.il").write_text(il, encoding="utf-8")
            (output / "cell_names.json").write_text(
                json.dumps(names, indent=2) + "\n", encoding="utf-8")
        (output / "candidate.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, ImportError, AssertionError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps({"output": str(output), **result}, indent=2))


if __name__ == "__main__":
    main()
