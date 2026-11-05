"""Write a private configuration and optionally initialize a planning run."""

import argparse
import json
import os
from pathlib import Path

from dcim_config import PATH_KEYS, Settings, load_config
from init_run import initialize, run_destination
from project_config import normalize_project, open_items


def configure(output, source=None, paths=None, macro=None, project_file=None, run_name=None):
    output = Path(output).expanduser().resolve()
    data = (load_config(source).rebased(output.parent) if source else
            {"work_root": "dcim-runs", "input_files": {}})
    for key, value in (paths or {}).items():
        if key not in PATH_KEYS:
            raise ValueError(f"Unknown path key: {key}")
        expanded = os.path.expandvars(value)
        if "$" in expanded:
            raise ValueError(f"Unresolved environment variable in {key}")
        data[key] = str(Path(expanded).expanduser().resolve())
    project = (json.loads(Path(project_file).expanduser().read_text(encoding="utf-8"))
               if project_file else data.get("project", {}))
    project = normalize_project(project)
    project["macro"].update(macro or {})
    data["project"] = normalize_project(project)
    settings = Settings(output, data)
    settings.ensure_output(output, require_work_root=False)
    settings.ensure_output(settings.path("work_root"))
    if output.exists():
        raise FileExistsError(f"Configuration already exists: {output}")
    if run_name:
        run_destination(settings, run_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(data, indent=2) + "\n")
    result = {"config": str(output), "open_items": open_items(settings.project), "eda_launched": False}
    if run_name:
        result["run_root"] = str(initialize(output, run_name))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="New private JSON file; never overwritten")
    parser.add_argument("--from-config", help="Existing config/example whose paths are rebased")
    parser.add_argument("--project-file", help="JSON project object: macro, technology, modules, verification")
    parser.add_argument("--init", metavar="RUN", help="Also initialize a planning run")
    for key in PATH_KEYS:
        parser.add_argument("--" + key.replace("_", "-"))
    for key in ("input_channels", "output_channels", "storage_bits", "compute_lanes",
                "input_bits", "weight_bits", "output_bits", "accumulator_bits", "cycles_per_result"):
        parser.add_argument("--" + key.replace("_", "-"), type=int)
    parser.add_argument("--storage-compute-ratio", type=float)
    parser.add_argument("--ratio-definition")
    args = parser.parse_args()
    values = vars(args)
    paths = {key: values[key] for key in PATH_KEYS if values[key] is not None}
    macro = {key: value for key, value in values.items()
             if key not in PATH_KEYS and key not in ("output", "from_config", "project_file", "init")
             and value is not None}
    try:
        result = configure(args.output, args.from_config, paths, macro, args.project_file, args.init)
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
