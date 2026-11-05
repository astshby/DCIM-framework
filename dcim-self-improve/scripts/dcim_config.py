"""Process-neutral input manifests and read-only source protection."""

import hashlib
import json
import os
from pathlib import Path

from project_config import normalize_project


PATH_KEYS = (
    "work_root", "pdk_root", "compiler_ref_root", "circuit_ref_root",
    "experience_root", "same_process_dcim_root", "digital_flow_root",
    "isscc_reference_root",
)
INPUT_SCOPES = {
    "compiler": "compiler_ref_root",
    "pdk": "pdk_root",
    "circuit": "circuit_ref_root",
    "experience": "experience_root",
    "same_process_dcim": "same_process_dcim_root",
    "digital_flow": "digital_flow_root",
    "isscc": "isscc_reference_root",
}


def is_within(path, root):
    return path == root or root in path.parents


class Settings:
    def __init__(self, source, data):
        if not isinstance(data, dict):
            raise ValueError("Configuration must be a JSON object")
        unknown = set(data) - set(PATH_KEYS) - {"input_files", "project"}
        if unknown:
            raise ValueError("Unknown configuration keys: " + ", ".join(sorted(unknown)))
        self.source = Path(source).resolve()
        self.data = data
        self.project = normalize_project(data.get("project", {}))
        for key in PATH_KEYS:
            value = data.get(key)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{key} must be a nonempty path string or null")
        self.input_files = data.get("input_files", {})
        if not isinstance(self.input_files, dict):
            raise ValueError("input_files must map root keys to relative path lists")
        for key, names in self.input_files.items():
            if key not in INPUT_SCOPES.values() or not isinstance(names, list):
                raise ValueError(f"Invalid input_files entry: {key}")
            for name in names:
                if not isinstance(name, str) or not name.strip():
                    raise ValueError(f"Invalid input path for {key}")
                relative = Path(name)
                if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
                    raise ValueError(f"Input paths must stay relative to {key}: {name}")

    def path(self, key, required=True):
        if key not in PATH_KEYS:
            raise ValueError(f"Unknown path key: {key}")
        value = self.data.get(key)
        if value is None:
            if required:
                raise ValueError(f"Set {key} in {self.source}")
            return None
        path = Path(os.path.expandvars(value)).expanduser()
        if "$" in str(path):
            raise ValueError(f"Unresolved environment variable in {key}: {value}")
        if not path.is_absolute():
            path = self.source.parent / path
        return path.resolve()

    def check(self, scope):
        if scope not in (*INPUT_SCOPES, "all"):
            raise ValueError(f"Unknown input scope: {scope}")
        if scope == "all":
            required = [key for key in INPUT_SCOPES.values()
                        if key in ("pdk_root", "compiler_ref_root")
                        or self.path(key, required=False) is not None
                        or self.input_files.get(key)]
        else:
            required = [INPUT_SCOPES[scope]]
        records = []
        for key in required:
            root = self.path(key, required=False)
            if root is None:
                records.append({"key": key, "path": None, "present": False,
                                "coverage": "unconfigured"})
                continue
            names = self.input_files.get(key, [])
            records.append({"key": key, "path": str(root), "present": root.is_dir(),
                            "coverage": "root_and_manifest" if names else "root_only"})
            for name in names:
                path = (root / name).resolve()
                if not is_within(path, root):
                    raise ValueError(f"Manifest path escapes {key}: {name}")
                records.append({"key": key, "path": str(path),
                                "present": path.is_file() or path.is_dir(),
                                "coverage": "manifest_entry"})
        return {"scope": scope, "passed": all(r["present"] for r in records),
                "checks": records, "qualification": "existence only; not EDA qualification"}

    def ensure_output(self, output, require_work_root=True):
        output = Path(output).resolve()
        if require_work_root and not is_within(output, self.path("work_root")):
            raise ValueError("Output must remain inside work_root")
        for key in PATH_KEYS:
            if key == "work_root":
                continue
            source = self.path(key, required=False)
            if source is not None and (
                    is_within(output, source) or is_within(source, output)):
                raise ValueError(f"Output overlaps read-only {key}: {source}")
        package = Path(__file__).resolve().parents[2]
        if (package / "AGENTS.md").is_file() and (
                is_within(output, package) or is_within(package, output)):
            raise ValueError("Output must be outside the installed skill")
        return output

    def rebased(self, base):
        result = {
            key: os.path.relpath(self.path(key), base)
            for key in PATH_KEYS if self.path(key, required=False) is not None
        }
        result["input_files"] = self.input_files
        result["project"] = self.project
        return result


def load_config(path=None):
    path = path or os.environ.get("DCIM_CONFIG")
    if not path:
        raise ValueError("Supply --config or set DCIM_CONFIG to a private JSON file")
    source = Path(path).expanduser().resolve()
    return Settings(source, json.loads(source.read_text(encoding="utf-8")))


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()
