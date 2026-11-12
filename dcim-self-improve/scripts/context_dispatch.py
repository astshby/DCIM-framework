"""Materialize Analyst selections; never rank routes or invoke an agent API."""

import argparse
import json
import os
from pathlib import Path
import shlex
import socket
import sys

from evidence import EvidenceError, Frozen, absolute, fingerprint, freeze, require
from run_config import within


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=True)
        stream.write("\n")


def unique(values, label):
    require(len(values) == len(set(values)), "Duplicate " + label)


def bounded_file(value, roots):
    path = absolute(value)
    require(path.is_file(), "Expected a file: " + str(path))
    require(any(within(path, root) for root in roots),
            "Source outside declared roots: " + str(path))
    return path


def overview(catalog, stage):
    """Emit all stage summaries, not keyword-selected competing routes."""
    data = read_json(catalog)
    entries = [e for e in data["entries"] if e["stage"] == stage]
    unique([e["id"] for e in entries], "catalog IDs")
    return {"stage": stage, "catalog_revision": data["revision"],
            "entries": entries}


def prepare(task_path, selection_path, catalog_path, out):
    task_path, selection_path, catalog_path = map(
        absolute, (task_path, selection_path, catalog_path))
    task, selection, catalog = map(
        read_json, (task_path, selection_path, catalog_path))
    require(socket.gethostname() in task["execution_hostnames"],
            "Execution hostname does not match task")
    require(task["host"] == catalog["host"] == selection["host"],
            "Host identity mismatch")
    require(task["profile"] == selection["profile"], "Profile mismatch")
    require(task["task_id"] == selection["task_id"], "Task identity mismatch")
    require(task["stage"] == selection["stage"], "Stage mismatch")
    require(selection["catalog_revision"] == catalog["revision"],
            "Stale catalog revision")
    if "catalog_sha256" in selection:
        require(selection["catalog_sha256"] == fingerprint(catalog_path)["sha256"],
                "Catalog changed since Analyst selection")
    require(selection.get("decision") and selection.get("route_id"),
            "Explicit Analyst route decision required")
    roots = [absolute(p) for p in task["allowed_roots"]]
    require(all(p.is_dir() for p in roots), "Allowed roots must be directories")
    require(absolute(catalog["root"]) in roots, "Catalog root not declared")
    entries = catalog["entries"]
    unique([e["id"] for e in entries], "catalog IDs")
    by_id = {e["id"]: e for e in entries}
    requested = selection["entry_ids"]
    unique(requested, "selected entry IDs")
    selected, visiting, visited = [], set(), set()

    def visit(key):
        require(key in by_id, "Missing experience ID: " + key)
        require(key not in visiting, "Cyclic experience dependency: " + key)
        if key in visited:
            return
        visiting.add(key)
        entry = by_id[key]
        for dependency in entry.get("requires", []):
            visit(dependency)
        visiting.remove(key)
        visited.add(key)
        selected.append(entry)

    for key in requested:
        visit(key)
    resources = selection["resources"]
    unique([r["id"] for r in resources], "resource IDs")
    require(set(task["required_resource_ids"]) <= {r["id"] for r in resources},
            "Missing mandatory task/rule/tool resource")
    sources = {}

    def bind(value):
        path = bounded_file(value, roots)
        if str(path) not in sources:
            sources[str(path)] = {"path": str(path), **fingerprint(path)}
        return path

    for path in (task_path, selection_path, catalog_path, Path(__file__).resolve(),
                 Path(__file__).with_name("evidence.py").resolve(),
                 Path(__file__).with_name("run_config.py").resolve()):
        bind(path)
    body = ["# Builder Context", "\n## Task\n",
            json.dumps(task, indent=2), "\n## Analyst Selection\n",
            json.dumps({k: v for k, v in selection.items()
                        if k != "resources"}, indent=2)]
    for entry in selected:
        bind(entry["summary_path"])
        for path in entry["evidence_paths"]:
            bind(path)
        body.extend(["\n## Experience: " + entry["id"] + "\n",
                     json.dumps(entry, indent=2)])
    emitted = set()
    for resource in resources:
        path = bind(resource["path"])
        mode = resource.get("mode", "reference")
        require(mode in ("inline", "reference"), "Unknown resource mode")
        if "sha256" in resource:
            require(resource["sha256"] == sources[str(path)]["sha256"],
                    "Stale selected resource: " + resource["id"])
        body.extend(["\n## Resource: " + resource["id"],
                     resource["purpose"], str(path)])
        if mode == "inline" and path not in emitted:
            # Bound before decoding; no full deck accidentally enters a bundle.
            require(path.stat().st_size <= task["max_bundle_bytes"],
                    "Inline resource exceeds bundle budget: " + resource["id"])
            body.append(path.read_text(encoding="utf-8"))
            emitted.add(path)
        elif mode == "inline":
            body.append("(Already included above.)")
    text = "\n".join(body) + "\n"
    size = len(text.encode("utf-8"))
    require(size <= task["max_bundle_bytes"],
            "Bundle budget exceeded; Analyst must split/reselect, never truncate")
    # All input validation precedes creating a new, exclusive package.
    out = out.absolute()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    out = out.resolve()
    write_json(out / "task.json", task)
    write_json(out / "selection.json", selection)
    write_json(out / "sources.json", {
        "host": task["host"], "hostname": socket.gethostname(),
        "files": list(sources.values()), "resolved_entry_ids": [e["id"] for e in selected]})
    (out / "context_bundle.md").write_text(text, encoding="utf-8")
    freeze([out / name for name in
            ("task.json", "selection.json", "sources.json", "context_bundle.md")],
           out / "manifest.json")
    digest = fingerprint(out / "manifest.json")["sha256"]
    command = shlex.join([task["python"], str(Path(__file__).resolve()),
                          "open", "--package", str(out),
                          "--expected-sha256", digest])
    card = {
        "status": "prepared", "task_id": task["task_id"],
        "package": str(out), "manifest_sha256": digest,
        "bundle_bytes": size, "entry_count": len(selected),
        "source_count": len(sources), "model": task["model"],
        "bootstrap": "Continue as Builder. On host " + task["host"]
        + ", use the task-declared execution runner:\n" + command
        + "\nRead the emitted task and selected context before editing. "
          "Follow its scope; do not spawn agents. Return concise result paths.",
        "native_dispatch": "Main invokes the native tool; this script does not spawn."
    }
    write_json(out / "dispatch.json", card)
    return card


def open_package(package, digest):
    package = absolute(package)
    manifest = package / "manifest.json"
    require(fingerprint(manifest)["sha256"] == digest, "Manifest digest mismatch")
    frozen = Frozen(manifest)
    task = frozen.json(package / "task.json")
    require(socket.gethostname() in task["execution_hostnames"],
            "Execution hostname does not match task")
    sources = frozen.json(package / "sources.json")
    for entry in sources["files"]:
        require(fingerprint(absolute(entry["path"])) ==
                {k: entry[k] for k in ("sha256", "bytes")},
                "Source changed since preparation: " + entry["path"])
    body = frozen.text(package / "context_bundle.md")
    frozen.verify()
    return body


def record_dispatch(package, agent_id):
    require(agent_id.strip() and len(agent_id) < 100, "Invalid actual agent ID")
    path = absolute(package) / "dispatch_receipt.json"
    write_json(path, {"agent_id": agent_id, "event": "native_dispatch_reported",
                      "pid": os.getpid(),
                      "limitation": "Caller records tool result; not proof of reading."})
    return {"status": "recorded", "receipt": str(path)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    view = sub.add_parser("overview")
    view.add_argument("--catalog", required=True, type=Path)
    view.add_argument("--stage", required=True, type=int)
    build = sub.add_parser("prepare")
    for name in ("task", "selection", "catalog", "out"):
        build.add_argument("--" + name, required=True, type=Path)
    read = sub.add_parser("open")
    read.add_argument("--package", required=True, type=Path)
    read.add_argument("--expected-sha256", required=True)
    record = sub.add_parser("record")
    record.add_argument("--package", required=True, type=Path)
    record.add_argument("--agent-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "open":
            print(open_package(args.package, args.expected_sha256))
            return 0
        if args.command == "overview":
            result = overview(args.catalog, args.stage)
        elif args.command == "prepare":
            result = prepare(args.task, args.selection, args.catalog, args.out)
        else:
            result = record_dispatch(args.package, args.agent_id)
        print(json.dumps(result, indent=2))
        return 0
    except (EvidenceError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "incomplete", "diagnostic": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
