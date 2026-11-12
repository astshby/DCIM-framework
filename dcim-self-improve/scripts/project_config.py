"""Normalize the macro contract and the small default module-learning plan."""

import copy
import hashlib
import json
import math
import re


MODULE_PHASES = ("contract", "baseline", "legal_layout", "compact", "close", "learn")
MACRO_PHASES = ("redesign", "baseline", "legal_layout", "compact", "close", "compare")
MODULE_NAMES = (
    ("sram", "Storage, read/write and local memory access", "compiler"),
    ("multiplier", "Input/weight product with declared arithmetic", "digital_flow"),
    ("adder", "Addition/reduction with declared carry and width", "digital_flow"),
    ("selector_control", "Selection, decode and local control", "digital_flow"),
    ("accumulator", "State, accumulation, reset and output timing", "digital_flow"),
)
MODULE_DEFAULT = {
    "id": "", "purpose": "", "enabled": True, "omission_reason": None,
    "reference_scope": "circuit", "interface_contract": None,
    "geometry_contract": None, "closure_suite": None,
}
DEFAULT_PROJECT = {
    "macro": {
        "input_channels": 8, "output_channels": 8, "storage_compute_ratio": 8,
        "ratio_definition": None, "storage_bits": None, "compute_lanes": None,
        "input_bits": None, "weight_bits": None, "output_bits": None,
        "accumulator_bits": None, "input_signed": None, "weight_signed": None,
        "cycles_per_result": None, "overflow_policy": None,
        "objective": "minimize routed macro area subject to correctness and timing",
        "max_width_um": None, "max_height_um": None, "target_frequency_hz": None,
        "supply_v": None, "temperature_c": None, "output_load_ff": None,
    },
    "technology": {"process": None, "release": None, "stack": None},
    "modules": [dict(MODULE_DEFAULT, id=name, purpose=purpose, reference_scope=scope)
                for name, purpose, scope in MODULE_NAMES],
    "verification": {
        "profile": "staged", "full_simulation_policy": "selected_revision_per_round",
        "smoke_max_seconds": None, "full_max_seconds": None,
        "module_corners": [], "macro_corners": [], "macro_closure_suite": None,
    },
}


def merge_object(defaults, values, label):
    if not isinstance(values, dict):
        raise ValueError(f"{label} must be an object")
    unknown = set(values) - set(defaults)
    if unknown:
        raise ValueError(f"Unknown {label} keys: {', '.join(sorted(unknown))}")
    result = copy.deepcopy(defaults)
    for key, value in values.items():
        result[key] = (merge_object(defaults[key], value, f"{label}.{key}")
                       if isinstance(defaults[key], dict) else copy.deepcopy(value))
    return result


def optional_text(value, label):
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise ValueError(f"{label} must be nonempty text or null")


def positive_number(value, label, integer=False, required=False):
    if value is None and not required:
        return
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0
            or (integer and not isinstance(value, int))):
        raise ValueError(f"{label} must be a positive {'integer' if integer else 'number'}")


def normalize_project(values=None):
    project = merge_object(DEFAULT_PROJECT, {} if values is None else values, "project")
    macro = project["macro"]
    integers = ("input_channels", "output_channels", "storage_bits", "compute_lanes",
                "input_bits", "weight_bits", "output_bits", "accumulator_bits", "cycles_per_result")
    for key in integers:
        positive_number(macro[key], key, integer=True,
                        required=key in ("input_channels", "output_channels"))
    for key in ("storage_compute_ratio", "max_width_um", "max_height_um",
                "target_frequency_hz", "supply_v", "output_load_ff"):
        positive_number(macro[key], key, required=key == "storage_compute_ratio")
    temperature = macro["temperature_c"]
    if temperature is not None and (
            isinstance(temperature, bool) or not isinstance(temperature, (int, float))
            or not math.isfinite(temperature)):
        raise ValueError("temperature_c must be a finite number or null")
    for key in ("input_signed", "weight_signed"):
        if macro[key] is not None and not isinstance(macro[key], bool):
            raise ValueError(f"{key} must be boolean or null")
    for key in ("ratio_definition", "overflow_policy", "objective"):
        optional_text(macro[key], key)
    if macro["objective"] is None:
        raise ValueError("objective must be declared")
    for key, value in project["technology"].items():
        optional_text(value, f"technology.{key}")
    if not isinstance(project["modules"], list) or not project["modules"]:
        raise ValueError("modules must be a nonempty list")
    modules = []
    identifiers = set()
    for value in project["modules"]:
        module = merge_object(MODULE_DEFAULT, value, "module")
        identifier = module["id"]
        if (not isinstance(identifier, str)
                or not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", identifier)
                or identifier in identifiers or identifier == "macro"):
            raise ValueError("Module IDs must be unique simple names; macro is reserved")
        identifiers.add(identifier)
        for key in ("purpose", "omission_reason", "interface_contract", "geometry_contract", "closure_suite"):
            optional_text(module[key], f"{identifier}.{key}")
        if module["purpose"] is None or not isinstance(module["enabled"], bool):
            raise ValueError("Each module needs a purpose and boolean enabled")
        if not module["enabled"] and not module["omission_reason"]:
            raise ValueError("A disabled module needs an omission_reason")
        if module["reference_scope"] not in ("compiler", "digital_flow", "circuit", "native_device", "composition", "standard_cell"):
            raise ValueError("Unknown module reference_scope")
        modules.append(module)
    if not any(module["enabled"] for module in modules):
        raise ValueError("Enable at least one learning module")
    project["modules"] = modules
    verification = project["verification"]
    if (verification["profile"] != "staged"
            or verification["full_simulation_policy"] != "selected_revision_per_round"):
        raise ValueError("Use staged verification and selected_revision_per_round full simulation")
    for key in ("smoke_max_seconds", "full_max_seconds"):
        positive_number(verification[key], key)
    for key in ("module_corners", "macro_corners"):
        values = verification[key]
        if not isinstance(values, list) or any(
                not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(f"{key} must be a list of named test conditions")
    optional_text(verification["macro_closure_suite"], "macro_closure_suite")
    return project


def project_digest(project):
    return hashlib.sha256(json.dumps(project, sort_keys=True).encode("utf-8")).hexdigest()


def open_items(project):
    macro_fields = (
        "ratio_definition", "storage_bits", "compute_lanes", "input_bits", "weight_bits",
        "output_bits", "accumulator_bits", "input_signed", "weight_signed",
        "cycles_per_result", "overflow_policy", "target_frequency_hz", "supply_v",
        "temperature_c", "output_load_ff",
    )
    return {
        "macro_contract": [key for key in macro_fields if project["macro"][key] is None],
        "technology": [key for key, value in project["technology"].items() if value is None],
        "modules": {
            module["id"]: [key for key in ("interface_contract", "geometry_contract", "closure_suite")
                           if module[key] is None]
            for module in project["modules"] if module["enabled"]
        },
        "verification": [key for key in ("module_corners", "macro_corners", "macro_closure_suite")
                         if not project["verification"][key]],
    }


def initial_plan(project):
    def stage(phases):
        return {"phase": phases[0], "phases": {phase: "pending" for phase in phases},
                "selected_candidate": None, "closure_evidence": None, "closure_identity": None}

    return {
        "schema_version": 1, "project_sha256": project_digest(project),
        "state": "planning", "next_task": "tasks/000-initialize.md",
        "open_items": open_items(project),
        "modules": {module["id"]: stage(MODULE_PHASES)
                    for module in project["modules"] if module["enabled"]},
        "macro": stage(MACRO_PHASES), "live_jobs": [],
    }
