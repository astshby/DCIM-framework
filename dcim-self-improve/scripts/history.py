"""Append design iterations and prompt revisions; verify and compare saved files."""

import argparse
from datetime import datetime, timezone
import difflib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile

from dcim_config import digest, is_within, load_config


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value):
        raise ValueError("Use a simple ID beginning with a letter")
    return value


def run_settings(run):
    root = Path(run).expanduser().resolve()
    settings = load_config(root / "config.json")
    if settings.path("work_root") != root:
        raise ValueError("Use an initialized run whose work_root is itself")
    return root, settings


def module_name(settings, module):
    module = "dcim" if module == "macro" else identifier(module)
    allowed = {entry["id"] for entry in settings.project["modules"] if entry["enabled"]}
    if module not in allowed | {"dcim"}:
        raise ValueError(f"Unknown enabled module: {module}")
    return module


def inventory(root):
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Snapshot must not contain symlinks: {path}")
        if path.is_file():
            files[str(path.relative_to(root))] = digest(path)
        elif not path.is_dir():
            raise ValueError(f"Snapshot requires regular files/directories: {path}")
    return files


def read_record(path, verify=True):
    if path.is_symlink():
        raise ValueError("Record directory must not be a symlink")
    record_file = path / "record.json"
    if record_file.is_symlink() or (path / "record.sha256").is_symlink():
        raise ValueError("Record metadata must not be symlinks")
    record = json.loads(record_file.read_text(encoding="utf-8"))
    if verify:
        if digest(record_file) != (path / "record.sha256").read_text().strip():
            raise ValueError(f"Record metadata changed: {path}")
        actual = inventory(path)
        actual.pop("record.json", None)
        actual.pop("record.sha256", None)
        if actual != record["files"]:
            raise ValueError(f"Saved files changed, missing or added: {path}")
    return record


def prepare(run, family, record_id, bundle, parent):
    root, settings = run_settings(run)
    record_id = identifier(record_id)
    destination = root / family / record_id
    settings.ensure_output(destination)
    if not is_within(destination.resolve(), root):
        raise ValueError("History must stay inside its run")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Record already exists: {destination}")
    source = Path(bundle).expanduser()
    if source.is_symlink():
        raise ValueError("Bundle must not be a symlink")
    source = source.resolve()
    if not source.is_dir() or not is_within(source, root):
        raise ValueError("Stage the bundle in a directory inside the run")
    settings.ensure_output(source)
    for reserved in (root / "iterations", root / "prompt-history", root / "iteration-evidence"):
        if is_within(source, reserved) or is_within(reserved, source):
            raise ValueError("Stage outside history directories and the run root")
    source_files = inventory(source)
    if not source_files:
        raise ValueError("Cannot save an empty bundle")
    previous = None
    if parent:
        parent_path = destination.parent / identifier(parent)
        previous = read_record(parent_path)
        if previous["id"] != parent or previous["kind"] != family.split("/")[0]:
            raise ValueError("Parent record identity does not match")
    elif destination.parent.exists() and any(destination.parent.glob("*/record.json")):
        raise ValueError("Specify --parent after the first record; branching is allowed")
    return root, destination, source, source_files, previous


def publish(destination, source, source_files, record, context, extra=None):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pending-", dir=str(destination.parent)) as temporary:
        staged = Path(temporary) / "record"
        shutil.copytree(source, staged / "snapshot", symlinks=True)
        if inventory(staged / "snapshot") != source_files or inventory(source) != source_files:
            raise ValueError("Source changed during snapshot; freeze writers and retry")
        for name, path in context.items():
            expected = digest(path)
            target = staged / "context" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            if digest(target) != expected or digest(path) != expected:
                raise ValueError("Context changed during snapshot")
        for name, content in (extra or {}).items():
            (staged / name).write_text(content, encoding="utf-8")
        record["created_utc"] = datetime.now(timezone.utc).isoformat()
        record["files"] = inventory(staged)
        record_file = staged / "record.json"
        record_file.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (staged / "record.sha256").write_text(digest(record_file) + "\n", encoding="utf-8")
        if destination.exists():
            raise FileExistsError(f"Record already exists: {destination}")
        staged.rename(destination)
    return destination


def record_prompt(run, record_id, bundle, reason, parent=None):
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("State the prompt revision reason")
    root, destination, source, files, previous = prepare(
        run, "prompt-history", record_id, bundle, parent)
    previous_root = destination.parent / parent / "snapshot" if parent else None
    old_files = inventory(previous_root) if previous_root else {}
    differences = []
    for name in sorted(set(files) | set(old_files)):
        before = (previous_root / name).read_text(encoding="utf-8") if name in old_files else ""
        after = (source / name).read_text(encoding="utf-8") if name in files else ""
        if before != after:
            differences.extend(difflib.unified_diff(
                before.splitlines(), after.splitlines(),
                fromfile=f"{parent or 'empty'}/{name}", tofile=f"{record_id}/{name}", lineterm=""))
    record = {"schema_version": 1, "kind": "prompt-history", "id": record_id,
              "parent": parent, "reason": reason}
    return publish(destination, source, files, record, {},
                   {"changes.diff": "\n".join(differences) + "\n"})


def record_iteration(run, module, record_id, bundle, parent=None):
    root, settings = run_settings(run)
    module = module_name(settings, module)
    root, destination, source, files, previous = prepare(
        run, f"iterations/{module}", record_id, bundle, parent)
    metadata = json.loads((source / "iteration.json").read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("iteration.json must be an object")
    for key in ("summary", "phase", "outcome", "prompt_revision"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"iteration.json needs {key}")
    prompt_id = identifier(metadata["prompt_revision"])
    prompt_path = root / "prompt-history" / prompt_id
    read_record(prompt_path)
    for key in ("circuit_files", "layout_files"):
        names = metadata.get(key)
        if not isinstance(names, list) or any(not isinstance(name, str) or name not in files for name in names):
            raise ValueError(f"{key} must list existing bundle files")
        if not names and not (isinstance(metadata.get(key + "_missing_reason"), str)
                              and metadata[key + "_missing_reason"].strip()):
            raise ValueError(f"Provide {key} or its explicit missing_reason")
    if not isinstance(metadata.get("metrics", {}), dict):
        raise ValueError("metrics must be an object with unit-qualified names")
    context = {"config.json": root / "config.json"}
    for name, path in (("module-contract.md", root / "modules" / module / "contract.md"),
                       ("framework.json", root / "framework.json")):
        if path.is_file():
            context[name] = path
    record = {"schema_version": 1, "kind": "iterations", "module": module,
              "id": record_id, "parent": parent, "iteration": metadata,
              "prompt_record_sha256": digest(prompt_path / "record.json")}
    return publish(destination, source, files, record, context)


def record_evidence(run, module, iteration, record_id, bundle):
    root, settings = run_settings(run)
    module = module_name(settings, module)
    iteration = identifier(iteration)
    design = root / "iterations" / module / iteration
    read_record(design)
    family = f"iteration-evidence/{module}/{iteration}"
    directory = root / family
    if directory.exists():
        previous = sorted(directory.glob("*/record.json"), key=lambda path: path.stat().st_mtime_ns)
    else:
        previous = []
    parent = previous[-1].parent.name if previous else None
    root, destination, source, files, previous = prepare(run, family, record_id, bundle, parent)
    if "verification.md" not in files:
        raise ValueError("Evidence bundle needs verification.md with commands, conditions and check results")
    record = {"schema_version": 1, "kind": "iteration-evidence", "id": record_id,
              "parent": parent, "module": module, "iteration": iteration,
              "design_record_sha256": digest(design / "record.json")}
    return publish(destination, source, files, record, {})


def list_records(run):
    root, settings = run_settings(run)
    result = {"iterations": {}, "prompts": [], "evidence": [], "verification": "not_run"}
    for path in sorted((root / "iterations").glob("*/*/record.json")):
        record = read_record(path.parent, verify=False)
        result["iterations"].setdefault(record["module"], []).append({
            "id": record["id"], "parent": record["parent"],
            "summary": record["iteration"]["summary"],
            "prompt_revision": record["iteration"]["prompt_revision"]})
    for path in sorted((root / "prompt-history").glob("*/record.json")):
        record = read_record(path.parent, verify=False)
        result["prompts"].append({key: record[key] for key in ("id", "parent", "reason")})
    for path in sorted((root / "iteration-evidence").glob("*/*/*/record.json")):
        record = read_record(path.parent, verify=False)
        result["evidence"].append({key: record[key] for key in ("module", "iteration", "id")})
    return result


def verify_history(run):
    root, settings = run_settings(run)
    paths = sorted((root / "iterations").glob("*/*/record.json"))
    paths += sorted((root / "prompt-history").glob("*/record.json"))
    paths += sorted((root / "iteration-evidence").glob("*/*/*/record.json"))
    for path in paths:
        record = read_record(path.parent)
        if record["parent"]:
            read_record(path.parent.parent / identifier(record["parent"]))
        if record["kind"] == "iterations":
            prompt = root / "prompt-history" / identifier(record["iteration"]["prompt_revision"])
            read_record(prompt)
            if digest(prompt / "record.json") != record["prompt_record_sha256"]:
                raise ValueError(f"Linked prompt changed: {prompt}")
        if record["kind"] == "iteration-evidence":
            design = root / "iterations" / identifier(record["module"]) / identifier(record["iteration"])
            read_record(design)
            if digest(design / "record.json") != record["design_record_sha256"]:
                raise ValueError(f"Evidence design changed: {design}")
    return {"records_verified": len(paths), "integrity_passed": True,
            "qualification": "saved bytes and links only; not circuit verification"}


def compare_iterations(run, module, left, right):
    root, settings = run_settings(run)
    directory = root / "iterations" / module_name(settings, module)
    before = read_record(directory / identifier(left))
    after = read_record(directory / identifier(right))
    before_metrics = before["iteration"].get("metrics", {})
    after_metrics = after["iteration"].get("metrics", {})
    deltas = {}
    for key in before_metrics.keys() & after_metrics.keys():
        values = (before_metrics[key], after_metrics[key])
        if all(isinstance(value, (int, float)) and not isinstance(value, bool)
               and math.isfinite(value) for value in values):
            deltas[key] = values[1] - values[0]
    scope = before["iteration"].get("comparison_scope")
    return {
        "module": module, "left": left, "right": right,
        "changed_files": sorted(name for name in before["files"].keys() | after["files"].keys()
                                if before["files"].get(name) != after["files"].get(name)),
        "before_metrics": before_metrics, "after_metrics": after_metrics, "numeric_deltas": deltas,
        "declared_scope_matches": bool(scope) and scope == after["iteration"].get("comparison_scope"),
        "prompt_matches": before["prompt_record_sha256"] == after["prompt_record_sha256"],
        "qualification": "descriptive differences; verify scope/conditions before superiority claims",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("iteration", "prompt", "evidence", "list", "verify", "compare"):
        child = commands.add_parser(command)
        child.add_argument("--run", required=True)
        if command in ("iteration", "prompt", "evidence"):
            child.add_argument("--id", required=True)
            child.add_argument("--bundle", required=True)
        if command in ("iteration", "prompt"):
            child.add_argument("--parent")
        if command in ("iteration", "evidence", "compare"):
            child.add_argument("--module", required=True)
        if command == "evidence":
            child.add_argument("--iteration", required=True)
        if command == "prompt":
            child.add_argument("--reason", required=True)
        if command == "compare":
            child.add_argument("--left", required=True)
            child.add_argument("--right", required=True)
    args = parser.parse_args()
    try:
        if args.command == "iteration":
            result = {"record": str(record_iteration(args.run, args.module, args.id, args.bundle, args.parent))}
        elif args.command == "prompt":
            result = {"record": str(record_prompt(args.run, args.id, args.bundle, args.reason, args.parent))}
        elif args.command == "evidence":
            result = {"record": str(record_evidence(args.run, args.module, args.iteration, args.id, args.bundle))}
        elif args.command == "list":
            result = list_records(args.run)
        elif args.command == "verify":
            result = verify_history(args.run)
        else:
            result = compare_iterations(args.run, args.module, args.left, args.right)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
