"""Explicit stage inputs and portable run identity. Standard library only."""
import hashlib
import json
import os
from pathlib import Path
import re


def fingerprint(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "bytes": size}


def within(path, root):
    try:
        Path(path).relative_to(root)
        return True
    except ValueError:
        return False


def resolve(base, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("An explicit nonempty path is required")
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def safe_relative(value):
    path = Path(value)
    if path.is_absolute() or not path.parts or any(p in ("..", ".") for p in path.parts):
        raise ValueError("Expected a contained relative file path: " + str(value))
    return path


class Config:
    def __init__(self, filename=None):
        filename = filename or os.environ.get("DCIM_CONFIG")
        if not filename:
            raise ValueError("Supply --config or DCIM_CONFIG")
        self.path = Path(filename).expanduser().resolve(strict=True)
        self.base = self.path.parent
        self.identity = fingerprint(self.path)
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        if fingerprint(self.path) != self.identity:
            raise ValueError("Configuration changed while reading")
        if self.data.get("schema_version") != 1:
            raise ValueError("Unsupported configuration schema_version")
        if not isinstance(self.data.get("node"), str) or not self.data["node"].strip():
            raise ValueError("Declare the target node/profile explicitly")
        self.output = resolve(self.base, self.data["work_root"])
        self.resources = self.data.get("resources", {})
        self.stages = self.data.get("stages", {})
        if not isinstance(self.resources, dict) or not isinstance(self.stages, dict):
            raise ValueError("resources and stages must be objects")

    def check(self, stage):
        if stage not in self.stages or not isinstance(self.stages[stage], list):
            raise ValueError("Declare required resource IDs for stage: " + stage)
        required = self.stages[stage]
        if len(required) != len(set(required)):
            raise ValueError("Duplicate stage resource IDs")
        rows, missing = [], []
        for key in required:
            spec = self.resources.get(key)
            if not isinstance(spec, dict):
                missing.append({"id": key, "reason": "resource not configured"})
                continue
            path = resolve(self.base, spec.get("path"))
            kind = spec.get("kind", "file")
            if kind not in ("file", "directory"):
                raise ValueError("Unknown resource kind: " + key)
            if not spec.get("role"):
                raise ValueError("Declare resource role: " + key)
            paths = [path]
            if kind == "directory":
                names = spec.get("files")
                if not isinstance(names, list) or not names or len(names) != len(set(names)):
                    raise ValueError("Directory resources require explicit unique files: " + key)
                paths = [(path / safe_relative(name)).resolve() for name in names]
                if not all(within(p, path) for p in paths):
                    raise ValueError("Resource file escapes configured root: " + key)
            for item in paths:
                row = {"id": key, "role": spec["role"], "path": str(item)}
                if not item.is_file():
                    missing.append(dict(row, reason="required file missing"))
                    continue
                row.update(fingerprint(item))
                expected = spec.get("sha256") if kind == "file" else spec.get("hashes", {}).get(str(item.relative_to(path)))
                if expected and expected != row["sha256"]:
                    missing.append(dict(row, reason="configured source identity changed"))
                rows.append(row)
        return {"passed": not missing, "stage": stage, "node": self.data["node"],
                "inputs": rows, "missing": missing,
                "scope": "file availability and byte identity only", "eda_launched": False}

    def local_data(self):
        data = json.loads(json.dumps(self.data))
        data["work_root"] = "."
        for spec in data["resources"].values():
            spec["path"] = str(resolve(self.base, spec["path"]))
        data.pop("initial_recipe", None)
        return data


def verify_run(run):
    run = Path(run).resolve(strict=True)
    data = json.loads((run / "initial-manifest.json").read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported run manifest")
    required = {"config.json", "original-config.json", "input-check.json"}
    for folder in ("framework", "initial_design"):
        if not (run / folder).is_dir():
            raise ValueError("Missing pinned directory: " + folder)
        for path in (run / folder).rglob("*"):
            if path.is_symlink():
                raise ValueError("Pinned files cannot be symlinks")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                required.add(str(path.relative_to(run)))
    listed = [entry["path"] for entry in data["files"]]
    if len(listed) != len(set(listed)) or set(listed) != required:
        raise ValueError("Pinned inventory does not match run files")
    if not (run / "framework/SKILL.md").is_file() or not (run / "framework/scripts/check_inputs.py").is_file():
        raise ValueError("Run lacks required pinned entrypoints")
    for entry in data["files"]:
        path = (run / safe_relative(entry["path"])).resolve()
        if not within(path, run) or fingerprint(path) != {k: entry[k] for k in ("sha256", "bytes")}:
            raise ValueError("Pinned run file changed: " + entry["path"])
    for entry in data["external_inputs"]:
        if fingerprint(Path(entry["path"])) != {k: entry[k] for k in ("sha256", "bytes")}:
            raise ValueError("External input changed: " + entry["path"])
    return {"passed": True, "files": len(data["files"]),
            "external_inputs": len(data["external_inputs"]),
            "manifest_sha256": fingerprint(run / "initial-manifest.json")["sha256"],
            "scope": "pinned bytes and declared reference identity", "eda_launched": False}
