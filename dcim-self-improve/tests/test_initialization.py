"""Synthetic public entry points, no PDK or EDA."""
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from init_run import initialize
from run_config import Config, verify_run

class InitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = self.root / "private.json"
        self.data = {"schema_version": 1, "node": "fictional-alpha", "work_root": "runs",
                     "resources": {}, "stages": {"planning": [], "physical": ["rules"]}}
        self.save()

    def save(self):
        self.config.write_text(json.dumps(self.data), encoding="utf-8")

    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] /
            "scripts" / script)] + list(args), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True)

    def source(self):
        path = self.root / "external/rules"
        path.parent.mkdir(exist_ok=True)
        path.write_text("synthetic rule bytes")
        self.data["resources"] = {"rules": {"path": "external", "kind": "directory",
            "files": ["rules"], "role": "synthetic process constraint"}}
        self.save()
        return path

    def test_empty_init_and_public_cli(self):
        result = self.cli("init_run.py", "--config", str(self.config), "--name", "fresh")
        self.assertEqual(result.returncode, 0, result.stderr)
        run = Path(json.loads(result.stdout)["run_root"])
        self.assertEqual(list((run / "design").iterdir()), [])
        self.assertEqual(self.cli("check_inputs.py", "--run", str(run)).returncode, 0)
        self.assertEqual(self.cli("init_run.py", "--config", str(self.config), "--name", "fresh").returncode, 2)
        self.assertTrue(verify_run(run)["passed"])

    def test_two_unrelated_node_configs_and_explicit_file_sets(self):
        for node, names in [("fictional-alpha", ["a.mask", "b.model"]),
                            ("imaginary-beta", ["diff.rules", "ports.spec", "layers.table"])]:
            folder = self.root / node
            folder.mkdir()
            for name in names:
                (folder / name).write_text(node + name)
            self.data["node"] = node
            self.data["resources"] = {"rules": {"path": node, "kind": "directory",
                "files": names, "role": "user-declared process inputs"}}
            self.save()
            checked = Config(self.config).check("physical")
            self.assertEqual({Path(e["path"]).name for e in checked["inputs"]}, set(names))
            self.assertTrue(checked["passed"])
            self.assertTrue(verify_run(initialize(self.config, node, "physical"))["passed"])

    def test_targeted_missing_and_stale_sources(self):
        result = self.cli("check_inputs.py", "--config", str(self.config), "--stage", "physical")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["missing"][0]["id"], "rules")
        self.source()
        self.data["resources"]["rules"]["files"].append("missing-deck")
        self.save()
        with self.assertRaisesRegex(ValueError, "missing-deck"):
            initialize(self.config, "missing", "physical")
        self.assertFalse((self.root / "runs/missing").exists())
        self.data["resources"]["rules"]["files"] = ["rules"]
        self.data["resources"]["rules"]["hashes"] = {"rules": "stale"}
        self.save()
        self.assertIn("identity changed", Config(self.config).check("physical")["missing"][0]["reason"])

    def test_copy_and_publish_failures_clean_retry(self):
        for target in ("init_run.shutil.copytree", "init_run.os.rename"):
            with patch(target, side_effect=OSError("synthetic failure")):
                with self.assertRaises(OSError):
                    initialize(self.config, "retry")
            self.assertEqual(list((self.root / "runs").iterdir()), [])
        self.assertTrue(verify_run(initialize(self.config, "retry"))["passed"])

    def test_invalid_names_and_exclusive_lock(self):
        for name in ("../escape", "", "/tmp/out", "x/y", "a b", "1bad", "x" * 65):
            with self.assertRaises(ValueError):
                initialize(self.config, name)
        parent = self.root / "runs"
        parent.mkdir()
        lock = parent / ".locked.init-lock"
        lock.write_text("other active initializer")
        with self.assertRaises(FileExistsError):
            initialize(self.config, "locked")
        self.assertEqual(lock.read_text(), "other active initializer")

    def recipe(self):
        folder = self.root / "recipe"
        folder.mkdir()
        (folder / "generate.py").write_text("from helper import value")
        (folder / "helper.py").write_text("value = 1")
        self.data["initial_recipe"] = {"root": "recipe", "entrypoint": "generate.py",
                                       "files": ["generate.py", "helper.py"]}
        self.save()
        return folder

    def test_declared_recipe_closure_and_mutable_design(self):
        self.recipe()
        run = initialize(self.config, "seed")
        self.assertEqual({p.name for p in (run / "design").iterdir()}, {"generate.py", "helper.py"})
        (run / "design/helper.py").write_text("value = 2")
        self.assertTrue(verify_run(run)["passed"])
        (run / "initial_design/helper.py").write_text("value = 2")
        with self.assertRaisesRegex(ValueError, "Pinned run file changed"):
            verify_run(run)

    def test_recipe_root_overlap_and_dependency_escape(self):
        recipe = self.recipe()
        self.data["work_root"] = "recipe/runs"
        self.save()
        with self.assertRaisesRegex(ValueError, "overlaps"):
            initialize(self.config, "bad")
        self.assertFalse((recipe / "runs").exists())
        self.data["work_root"] = "runs"
        self.data["initial_recipe"]["files"] = ["../private.json", "generate.py"]
        self.save()
        with self.assertRaises(ValueError):
            initialize(self.config, "bad")
        self.assertEqual(list((self.root / "runs").iterdir()), [])

    def test_external_and_pinned_instruction_drift(self):
        source = self.source()
        run = initialize(self.config, "drift", "physical")
        source.write_text("changed")
        with self.assertRaisesRegex(ValueError, "External input changed"):
            verify_run(run)
        source.write_text("synthetic rule bytes")
        (run / "framework/references/builder.md").write_text("changed role")
        self.assertEqual(self.cli("check_inputs.py", "--run", str(run)).returncode, 2)

    def test_manifest_inventory_coverage(self):
        run = initialize(self.config, "inventory")
        manifest = run / "initial-manifest.json"
        original = manifest.read_text()
        data = json.loads(original)
        data["files"] = []
        manifest.write_text(json.dumps(data))
        self.assertEqual(self.cli("check_inputs.py", "--run", str(run)).returncode, 2)
        manifest.write_text(original)
        (run / "framework/references/new.md").write_text("unpinned instruction")
        with self.assertRaisesRegex(ValueError, "inventory"):
            verify_run(run)

    def test_whole_run_relocation_with_external_addresses_unchanged(self):
        self.source()
        original = initialize(self.config, "move", "physical")
        moved = self.root / "moved"
        shutil.move(str(original), str(moved))
        result = subprocess.run([sys.executable, str(moved / "framework/scripts/check_inputs.py"),
            "--run", str(moved)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["passed"])

    def test_first_task_prepare_and_open_from_pinned_run(self):
        run = initialize(self.config, "handoff")
        intent = run / "tasks/first.md"
        intent.write_text("Author one connected synthetic circuit. Stop after truth-table check.")
        task = {"task_id": "first", "stage": 1, "profile": "fictional-alpha", "host": "test",
            "execution_hostnames": [socket.gethostname()], "allowed_roots": [str(run), str(run / "knowledge")],
            "required_resource_ids": ["intent"], "max_bundle_bytes": 20000,
            "python": sys.executable, "model": "actual-test-model"}
        selection = {"task_id": "first", "stage": 1, "profile": "fictional-alpha", "host": "test",
            "catalog_revision": "initial", "decision": "Main chose circuit authoring",
            "route_id": "new-source", "entry_ids": [], "resources": [
            {"id": "intent", "path": str(intent), "mode": "inline", "purpose": "first task"}]}
        catalog = {"host": "test", "root": str(run / "knowledge"), "revision": "initial", "entries": []}
        for name, data in (("task", task), ("selection", selection), ("catalog", catalog)):
            (run / (name + ".json")).write_text(json.dumps(data))
        command = [sys.executable, str(run / "framework/scripts/context_dispatch.py"), "prepare"]
        for name in ("task", "selection", "catalog"):
            command.extend(["--" + name, str(run / (name + ".json"))])
        command.extend(["--out", str(run / "tasks/package")])
        prepared = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        card = json.loads(prepared.stdout)
        opened = subprocess.run([sys.executable, str(run / "framework/scripts/context_dispatch.py"), "open",
            "--package", card["package"], "--expected-sha256", card["manifest_sha256"]],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(opened.returncode, 0, opened.stdout + opened.stderr)
        self.assertIn("connected synthetic circuit", opened.stdout)
        self.assertTrue(verify_run(run)["passed"])

if __name__ == "__main__":
    unittest.main()
