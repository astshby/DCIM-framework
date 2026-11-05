"""Public smoke tests: temporary inputs only, no PDK, bridge or EDA required."""

import ast
import contextlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SEED_ROOT = SKILL_ROOT / "assets" / "seed"
sys.path.insert(0, str(SEED_ROOT))
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import arithmetic_contract
from geometry import bbox, empty_cell, expanded_refs, topo_order
from init_run import initialize
from macro_topology import arithmetic, macro_netlist
from seed_config import NATIVE_FILES, Settings, load_config


class PortableSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "dcim.local.json"
        self.config.write_text(json.dumps({
            "work_root": "runs",
            "native_ref_root": "external/native12",
            "pdk_root": "external/pdk12",
        }))

    def command(self, script, *args, **kwargs):
        env = dict(os.environ)
        env.pop("DCIM_CONFIG", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", str(script), *map(str, args)],
            cwd=self.root, env=env, text=True, capture_output=True, **kwargs,
        )

    def test_relative_paths_are_config_relative(self):
        settings = load_config(self.config)
        with patch("os.getcwd", return_value=str(self.root / "another-working-directory")):
            self.assertEqual(settings.path("native_ref_root"), self.root / "external/native12")

    def test_explicit_config_overrides_environment(self):
        with patch.dict(os.environ, {"DCIM_CONFIG": str(self.root / "missing.json")}):
            self.assertEqual(load_config(self.config).path("work_root"), self.root / "runs")

    def test_environment_config(self):
        with patch.dict(os.environ, {"DCIM_CONFIG": str(self.config)}):
            self.assertEqual(load_config().source, self.config)

    def test_missing_config_is_actionable(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Supply --config"):
                load_config()

    def test_bad_config_is_rejected(self):
        for data in ([], {"work_root": 5}, {"work_rooot": "runs"}):
            with self.assertRaises(ValueError):
                Settings(self.config, data)

    def test_initialization_and_rebased_config(self):
        output = initialize(self.config, "trial01")
        self.assertEqual(output, self.root / "runs/trial01")
        settings = load_config(output / "config.json")
        self.assertEqual(settings.path("work_root"), output)
        self.assertEqual(settings.path("native_ref_root"), self.root / "external/native12")
        self.assertTrue((output / "design/prepare_seed.py").is_file())
        self.assertTrue((output / "templates/task_packet.md").is_file())
        self.assertFalse(any(output.rglob("*.so")))
        with self.assertRaises(FileExistsError):
            initialize(self.config, "trial01")

    def test_path_traversal_and_readonly_overlap_rejected(self):
        with self.assertRaises(ValueError):
            initialize(self.config, "../escape")
        settings = Settings(self.config, {"native_ref_root": "runs/private"})
        for path in (self.root / "runs/private/new", self.root / "runs"):
            with self.assertRaisesRegex(ValueError, "read-only"):
                settings.ensure_output(path)
        with self.assertRaisesRegex(ValueError, "installed skill"):
            load_config(self.config).ensure_output(SKILL_ROOT / "runs")

    def test_seed_input_scope_and_missing_files(self):
        result = self.command(SKILL_ROOT / "scripts/check_inputs.py",
                              "--config", self.config, "--scope", "seed")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(json.loads(result.stdout)["passed"])
        native = self.root / "external/native12"
        for name in NATIVE_FILES:
            path = native / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic existence fixture only\n")
        result = self.command(SKILL_ROOT / "scripts/check_inputs.py",
                              "--config", self.config, "--scope", "seed")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["passed"])
        self.assertFalse(load_config(self.config).check("pdk")["passed"])

    def test_candidate_missing_ref_does_not_create_output(self):
        result = self.command(SEED_ROOT / "prepare_seed.py", "--config", self.config,
                              "--id", "sample", "--geometry-only")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Missing native reference inputs", result.stderr)
        self.assertFalse((self.root / "runs/candidates").exists())

    def test_cli_help_works_without_external_packages(self):
        for script in ("prepare_seed.py",):
            result = self.command(SEED_ROOT / script, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)
        for script in ("init_run.py", "check_inputs.py"):
            result = self.command(SKILL_ROOT / "scripts" / script, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_arithmetic_contract(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            arithmetic_contract.main()
        result = json.loads(output.getvalue())
        self.assertTrue(result["passed"])
        self.assertEqual(result["samples"], 11264)
        self.assertFalse(result["electrical_qualified"])

    def test_macro_integer_model_matches_independent_sum(self):
        rng = random.Random(31)
        for _ in range(100):
            weights = [[rng.randrange(16) for _ in range(8)] for _ in range(8)]
            ifn, sign = rng.randrange(256), rng.randrange(256)
            expected = []
            for channel in range(8):
                terms = [row[channel] - (16 if sign & (1 << channel) and row[channel] >= 8 else 0)
                         for term, row in enumerate(weights) if not ifn & (1 << term)]
                expected.append(sum(terms) % 128)
            self.assertEqual(arithmetic(weights, ifn, sign), expected)

    def test_macro_sketch_unique_instances_and_ports(self):
        for channels in (1, 8):
            ports, instances = macro_netlist(channels)
            self.assertEqual(len(ports), len(set(ports)))
            self.assertEqual(len(instances), 12 + 14 * channels)
            self.assertEqual(len(instances), len({i["name"] for i in instances}))

    def test_hierarchy_array_rotation_and_bbox(self):
        entry = {"child": "leaf", "origin_um": [10, 20], "columns": 2,
                 "rows": 1, "spacing_um": [3, 0], "rotation_deg": 90}
        self.assertEqual([r["origin_um"] for r in expanded_refs(entry)],
                         [[10, 20], [10, 23]])
        leaf = empty_cell()
        leaf["polygons"] = [{"points_um": [[0, 0], [2, 0], [2, 1], [0, 1]]}]
        cells = {"leaf": leaf, "top": empty_cell([entry])}
        self.assertEqual(bbox(cells, "top"), (9, 20, 10, 25))
        cells["leaf"]["references"].append({"child": "top"})
        with self.assertRaisesRegex(ValueError, "cycle"):
            topo_order(cells, "top")

    def test_public_sources_compile_without_private_imports(self):
        forbidden = {"prepare_baseline", "fast_route", "dcim_layout_transfer"}
        for source in SKILL_ROOT.rglob("*.py"):
            text = source.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(source))
            compile(tree, str(source), "exec")
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or "").split(".")[0], forbidden)


if __name__ == "__main__":
    unittest.main()
