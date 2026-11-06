"""Release behavior with synthetic files only; no EDA or installed dependencies."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from package_workspace import package_workspace


class PackageWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "source"
        self.root.mkdir()
        for name in ("README.md", "AGENTS.md", "HANDOFF.md", "LICENSE", ".gitignore"):
            (self.root / name).write_text("synthetic " + name)
        for name in ("dcim-self-improve", "scripts", "tests"):
            (self.root / name).mkdir()
        self.design = self.root / "dcim-self-improve/SKILL.md"
        self.design.write_text("version one")
        self.archive = self.parent / "dcim-framework.zip"

    def test_repeated_package_replaces_archive_with_current_content(self):
        self.assertFalse(package_workspace(self.root)["replaced_existing"])
        self.design.write_text("version two")
        result = package_workspace(self.root)
        self.assertTrue(result["replaced_existing"])
        with zipfile.ZipFile(self.archive) as stream:
            self.assertIsNone(stream.testzip())
            self.assertEqual(stream.read("dcim-framework/dcim-self-improve/SKILL.md"),
                             b"version two")
            self.assertEqual(len(stream.namelist()), result["files"])

    def test_private_files_and_metadata_are_excluded(self):
        for name in (".git/config", "runs/layout.gds", "dcim.local.json",
                     "dcim-self-improve/.env.secret", "scripts/test.local.json",
                     "scripts/record.sha256", "scripts/__pycache__/cache.pyc",
                     "dcim-self-improve/external/pdk/deck"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("private")
        package_workspace(self.root)
        with zipfile.ZipFile(self.archive) as stream:
            self.assertEqual(len(stream.namelist()), 6)
            self.assertTrue(all("private" not in stream.read(n).decode()
                                for n in stream.namelist()))

    def test_linked_source_is_rejected_and_old_archive_survives(self):
        package_workspace(self.root)
        original = self.archive.read_bytes()
        (self.root / "scripts/linked.txt").symlink_to(self.design)
        with self.assertRaisesRegex(ValueError, "independent"):
            package_workspace(self.root)
        self.assertEqual(self.archive.read_bytes(), original)

    def test_publish_failure_preserves_old_archive_and_cleans_temporary(self):
        package_workspace(self.root)
        original = self.archive.read_bytes()
        with patch("package_workspace.os.replace", side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):
                package_workspace(self.root)
        self.assertEqual(self.archive.read_bytes(), original)
        self.assertFalse(list(self.parent.glob(".dcim-framework-*.zip")))

    def test_archive_inside_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            package_workspace(self.root, self.root / "release.zip")


if __name__ == "__main__":
    unittest.main()
