"""Portable private configuration shared by the bundled initial generators."""

import hashlib
import json
import os
from pathlib import Path


PATH_KEYS = (
    "work_root", "pdk_root", "native_ref_root", "compiler_ref_root",
    "reference_22nm_root", "hierarchy_22nm", "experience_root", "warm_start_root",
)
PDK_FILES = (
    "tsmcN12/tsmcN12.layermap",
    "Calibre/drc/calibre_block.drc.15a",
    "Calibre/lvs/calibre.lvs",
    "models/toplevel.scs",
)
NATIVE_FILES = (
    "sram6t12_v1_layout_v2.gds",
    "sram6t12_v1_layout_v2.json",
    "sram6t12_v1_layout_v2_lvs/source.cdl",
    "lrcc12_v1_layout_v2.gds",
    "lrcc12_v1_layout_v2.json",
    "lrcc12_v1_layout_v2_lvs/source.cdl",
    "fa22t12_v1_layout_v2_lvs/source.cdl",
)
REFERENCE_DIRS = (
    "01_schematic", "02_basic_leaves", "03_composition_rules",
    "04_source_gds", "05_restricted_resize_script",
)
INPUT_SCOPES = {
    "seed": {"native_ref_root": NATIVE_FILES},
    "pdk": {"pdk_root": PDK_FILES},
    "compiler": {"compiler_ref_root": (
        "GDSII/sram12_ref16x8m2_m4xdh.gds",
        "SPICE/sram12_ref16x8m2.spi",
    )},
    "reference": {"reference_22nm_root": REFERENCE_DIRS},
}
_active = None


class Settings:
    def __init__(self, source, data):
        if not isinstance(data, dict):
            raise ValueError("Configuration must be a JSON object")
        unknown = set(data) - set(PATH_KEYS)
        if unknown:
            raise ValueError("Unknown configuration keys: " + ", ".join(sorted(unknown)))
        self.source = Path(source).resolve()
        self.data = data
        for key, value in data.items():
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{key} must be a nonempty path string or null")

    def path(self, key, required=True):
        if key not in PATH_KEYS:
            raise ValueError(f"Unknown path key: {key}")
        value = self.data.get(key)
        if value is None:
            if required:
                raise ValueError(f"Set {key} in {self.source}")
            return None
        path = Path(os.path.expandvars(value)).expanduser()
        if not path.is_absolute():
            path = self.source.parent / path
        return path.resolve()

    def check(self, scope):
        if scope not in (*INPUT_SCOPES, "all"):
            raise ValueError(f"Unknown input scope: {scope}")
        required = {}
        for name, inputs in INPUT_SCOPES.items():
            if scope in (name, "all"):
                required.update(inputs)
        records = []
        for key, names in required.items():
            root = self.path(key, required=False)
            if root is None:
                records.append({"key": key, "path": None, "present": False})
                continue
            for name in names:
                path = root / name
                present = path.is_dir() if key == "reference_22nm_root" else path.is_file()
                records.append({"key": key, "path": str(path), "present": present})
        return {"scope": scope, "passed": all(r["present"] for r in records),
                "checks": records, "qualification": "existence only; not EDA qualification"}

    def ensure_output(self, output):
        output = Path(output).resolve()
        for key in PATH_KEYS:
            if key == "work_root":
                continue
            source = self.path(key, required=False)
            if source is not None and (
                    output.is_relative_to(source) or source.is_relative_to(output)):
                raise ValueError(f"Output overlaps read-only {key}: {source}")
        package = Path(__file__).resolve().parents[2]
        if (package / "SKILL.md").is_file() and (
                output.is_relative_to(package) or package.is_relative_to(output)):
            raise ValueError("Output must be outside the installed skill")
        return output

    def rebased(self, base):
        return {
            key: os.path.relpath(self.path(key), base)
            for key in PATH_KEYS if self.path(key, required=False) is not None
        }


def load_config(path=None):
    path = path or os.environ.get("DCIM_CONFIG")
    if not path:
        raise ValueError("Supply --config or set DCIM_CONFIG to a private JSON file")
    source = Path(path).expanduser().resolve()
    return Settings(source, json.loads(source.read_text(encoding="utf-8")))


def configure(path=None):
    global _active
    _active = load_config(path)
    return _active


def get_path(key):
    settings = _active if _active is not None else load_config()
    return settings.path(key)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()
