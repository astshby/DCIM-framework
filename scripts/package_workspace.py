"""Publish the current framework through a verified, atomic ZIP replacement.

Adapted from the reference framework's package_workspace.py: retain its clean
file selection and byte comparison, and replace one archive after validation.
"""

import argparse
import json
import os
from pathlib import Path
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ("README.md", "AGENTS.md", "HANDOFF.md", "LICENSE", ".gitignore")
TREES = ("dcim-self-improve", "scripts", "tests")
EXCLUDED = {".git", "__pycache__", ".venv", ".pytest_cache", ".mypy_cache",
            "runs", "dcim-runs", "learn", "external", "iterations",
            "candidates", "evidence", "prompt-history", "iteration-evidence"}


def ignored(name):
    return (name in EXCLUDED or name in {"local.json", ".env"}
            or name.startswith(".env.")
            or name.endswith((".pyc", ".pyo", ".so", ".sha256", ".zip", ".local.json")))


def file_contents(root):
    """Read the release surface, pruning local state before traversal."""
    result = {}

    def add(path):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Release requires an independent file: " + str(path))
        result[path.relative_to(root).as_posix()] = path.read_bytes()

    for name in DOCUMENTS:
        add(root / name)
    for name in TREES:
        base = root / name
        if base.is_symlink() or not base.is_dir():
            raise ValueError("Missing or linked release directory: " + str(base))
        for directory, dirs, files in os.walk(str(base), followlinks=False):
            dirs[:] = sorted(item for item in dirs if not ignored(item))
            for item in dirs:
                if (Path(directory) / item).is_symlink():
                    raise ValueError("Release cannot include linked directories")
            for item in sorted(files):
                if not ignored(item):
                    add(Path(directory) / item)
    return result


def package_workspace(root=ROOT, archive=None):
    root = Path(root).resolve(strict=True)
    requested = Path(archive) if archive is not None else root.parent / "dcim-framework.zip"
    requested = requested.expanduser()
    if requested.is_symlink():
        raise ValueError("Archive target cannot be a symlink")
    archive = requested.resolve()
    try:
        archive.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("Archive must be outside the framework repository")
    if archive.suffix != ".zip" or (archive.exists() and not archive.is_file()):
        raise ValueError("Archive target must be a ZIP file")
    expected = file_contents(root)
    archive.parent.mkdir(parents=True, exist_ok=True)
    replaced = archive.exists()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".dcim-framework-", suffix=".zip",
                                         dir=str(archive.parent), delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(str(temporary), "w", compression=zipfile.ZIP_DEFLATED) as stream:
            for name, data in sorted(expected.items()):
                stream.writestr("dcim-framework/" + name, data)
        with zipfile.ZipFile(str(temporary)) as stream:
            if stream.testzip() is not None:
                raise ValueError("ZIP integrity check failed")
            actual = {name[len("dcim-framework/"):]: stream.read(name)
                      for name in stream.namelist()}
        if actual != expected or file_contents(root) != expected:
            raise ValueError("Release source or ZIP changed during packaging")
        os.chmod(str(temporary), 0o644)
        os.replace(str(temporary), str(archive))
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink()
    return {"archive": str(archive), "files": len(expected),
            "replaced_existing": replaced, "zip_verified": True,
            "git_metadata_included": False, "local_configuration_included": False,
            "eda_launched": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", help="Override the sibling dcim-framework.zip path")
    args = parser.parse_args()
    try:
        result = package_workspace(archive=args.archive)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(2, "error: " + str(error) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
