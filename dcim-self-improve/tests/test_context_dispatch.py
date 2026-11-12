import contextlib
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import context_dispatch as dispatch
from evidence import EvidenceError


class DispatchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "rules.txt"
        self.source.write_text("PRIVATE_RULE_BODY", encoding="utf-8")
        self.task = {
            "task_id": "repair", "stage": 2, "profile": "synthetic-profile",
            "host": "test", "execution_hostnames": [socket.gethostname()],
            "allowed_roots": [str(self.root), str(Path(dispatch.__file__).parent)],
            "required_resource_ids": ["rules"], "max_bundle_bytes": 20000,
            "python": sys.executable, "model": "explicit-model",
        }
        self.catalog = {
            "host": "test", "root": str(self.root), "revision": "v1",
            "entries": [{"id": key, "stage": 2, "revision": "v1",
                         "summary_path": str(self.source),
                         "evidence_paths": [str(self.source)], "conclusion": key}
                        for key in ("route.a", "route.b")]
        }
        self.selection = {
            "task_id": "repair", "stage": 2, "profile": "synthetic-profile", "host": "test",
            "catalog_revision": "v1", "route_id": "a",
            "decision": "Analyst explicitly chose a", "entry_ids": ["route.a"],
            "resources": [{"id": "rules", "path": str(self.source),
                           "mode": "inline", "purpose": "Actual rule excerpt"}],
        }

    def save(self):
        for name in ("task", "selection", "catalog"):
            (self.root / (name + ".json")).write_text(
                json.dumps(getattr(self, name)), encoding="utf-8")

    def prepare(self):
        self.save()
        return dispatch.prepare(*(self.root / (name + ".json") for name in
                                  ("task", "selection", "catalog")), self.root / "bundle")

    def test_round_trip_private_stdout_and_all_routes_overview(self):
        self.save()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = dispatch.main(["prepare", "--task", str(self.root / "task.json"),
                                  "--selection", str(self.root / "selection.json"),
                                  "--catalog", str(self.root / "catalog.json"),
                                  "--out", str(self.root / "bundle")])
        self.assertEqual(code, 0)
        self.assertNotIn("PRIVATE_RULE_BODY", output.getvalue())
        card = json.loads(output.getvalue())
        body = dispatch.open_package(Path(card["package"]), card["manifest_sha256"])
        self.assertIn("PRIVATE_RULE_BODY", body)
        self.assertNotIn('"id": "route.b"', body)
        self.assertEqual(len(dispatch.overview(self.root / "catalog.json", 2)["entries"]), 2)

    def test_rejections(self):
        mutations = [
            lambda: self.selection.update(entry_ids=["missing"]),
            lambda: self.selection.update(entry_ids=["route.a", "route.a"]),
            lambda: self.selection.update(host="other"),
            lambda: self.selection.update(profile="sram-special"),
            lambda: self.selection.update(catalog_revision="old"),
            lambda: self.selection.update(catalog_sha256="old"),
            lambda: self.selection.update(resources=[]),
            lambda: self.task.update(max_bundle_bytes=3),
            lambda: self.task.update(execution_hostnames=["not-this-host"]),
            lambda: self.selection["resources"][0].update(sha256="bad"),
            lambda: self.selection["resources"][0].update(path=str(self.root / "missing")),
            lambda: self.selection["resources"].append(self.selection["resources"][0].copy()),
            lambda: self.selection["resources"][0].update(mode="unknown"),
            lambda: self.task.update(allowed_roots=[str(Path(dispatch.__file__).parent)]),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                before = json.dumps([self.task, self.selection])
                mutate()
                with self.assertRaises((EvidenceError, OSError)):
                    self.prepare()
                self.assertFalse((self.root / "bundle").exists())
                self.task, self.selection = json.loads(before)

    def test_dependency_cycle(self):
        self.catalog["entries"][0]["requires"] = ["route.b"]
        self.catalog["entries"][1]["requires"] = ["route.a"]
        with self.assertRaises(EvidenceError):
            self.prepare()

    def test_dependency_deduplication(self):
        self.catalog["entries"][0]["requires"] = ["route.b"]
        self.selection["entry_ids"].append("route.b")
        card = self.prepare()
        self.assertEqual(card["entry_count"], 2)
        self.assertEqual(card["source_count"], 7)

    def test_drift_and_immutable_output(self):
        card = self.prepare()
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.source.write_text("CHANGED", encoding="utf-8")
        with self.assertRaises(EvidenceError):
            dispatch.open_package(Path(card["package"]), card["manifest_sha256"])

    def test_bundle_tamper_and_dispatch_record(self):
        card = self.prepare()
        package = Path(card["package"])
        dispatch.record_dispatch(package, "actual-native-agent")
        with self.assertRaises(FileExistsError):
            dispatch.record_dispatch(package, "duplicate")
        (package / "context_bundle.md").write_text("tampered", encoding="utf-8")
        with self.assertRaises(EvidenceError):
            dispatch.open_package(package, card["manifest_sha256"])


if __name__ == "__main__":
    unittest.main()
