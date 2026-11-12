"""Atomically initialize a new pinned run, without executing recipes or EDA."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import sys
from run_config import Config, fingerprint, resolve, safe_relative, within, verify_run

SKILL_ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def copy_recipe(settings, destination):
    recipe = settings.data.get("initial_recipe")
    if recipe is None:
        destination.mkdir()
        return
    root = resolve(settings.base, recipe["root"])
    names = recipe["files"]
    if not isinstance(names, list) or not names or len(names) != len(set(names)):
        raise ValueError("Recipe requires explicit unique dependency files")
    if recipe["entrypoint"] not in names:
        raise ValueError("Recipe entrypoint must be a declared dependency")
    for name in names:
        source = (root / safe_relative(name)).resolve(strict=True)
        if not within(source, root) or not source.is_file():
            raise ValueError("Recipe dependency escapes root or is not a file")
        target = destination / safe_relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(source), str(target))


def initialize(config, name, stage="planning", skill_root=SKILL_ROOT):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", name):
        raise ValueError("Use a run name beginning with a letter, then letters/digits/_/-")
    settings = Config(config)
    checked = settings.check(stage)
    if not checked["passed"]:
        raise ValueError("Missing/stale stage inputs: " + json.dumps(checked["missing"]))
    output = settings.output / name
    protected = [Path(skill_root).resolve(), settings.path]
    if settings.data.get("initial_recipe"):
        protected.append(resolve(settings.base, settings.data["initial_recipe"]["root"]))
    protected.extend(resolve(settings.base, spec["path"]) for spec in settings.resources.values())
    for source in protected:
        if within(output, source):
            raise ValueError("Output overlaps an input/package: " + str(source))
        if within(source, output):
            raise ValueError("Output would contain an input/package: " + str(source))
    settings.output.mkdir(parents=True, exist_ok=True)
    lock = settings.output / ("." + name + ".init-lock")
    descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    staging = None
    try:
        if output.exists():
            raise FileExistsError("Run already exists: " + str(output))
        staging = Path(tempfile.mkdtemp(prefix="." + name + "-", dir=str(settings.output)))
        framework = staging / "framework"
        framework.mkdir()
        for folder in ("scripts", "references", "templates", "agents"):
            shutil.copytree(str(Path(skill_root) / folder), str(framework / folder),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for filename in ("SKILL.md", "requirements.txt"):
            shutil.copyfile(str(Path(skill_root) / filename), str(framework / filename))
        shutil.copyfile(str(settings.path), str(staging / "original-config.json"))
        if fingerprint(staging / "original-config.json") != settings.identity:
            raise ValueError("Configuration changed during initialization")
        write_json(staging / "config.json", settings.local_data())
        write_json(staging / "input-check.json", checked)
        copy_recipe(settings, staging / "initial_design")
        shutil.copytree(str(staging / "initial_design"), str(staging / "design"))
        for name_dir in ("tasks", "knowledge", "evidence", "decisions"):
            (staging / name_dir).mkdir()
        entries = []
        for p in sorted(staging.rglob("*")):
            if p.is_file() and not within(p, staging / "design"):
                entries.append(dict(path=str(p.relative_to(staging)), **fingerprint(p)))
        write_json(staging / "initial-manifest.json", {
            "schema_version": 1, "files": entries, "external_inputs": checked["inputs"],
            "node": settings.data["node"], "stage": stage,
            "configuration_source": str(settings.path),
            "recipe": settings.data.get("initial_recipe"),
            "scope": "initial programs/instructions/config/declared input identities"})
        verify_run(staging)
        if output.exists():
            raise FileExistsError("Run appeared before publication: " + str(output))
        os.rename(str(staging), str(output))
        staging = None
    finally:
        if staging is not None:
            shutil.rmtree(str(staging))
        lock.unlink()
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Private JSON configuration or DCIM_CONFIG")
    parser.add_argument("--name", required=True)
    parser.add_argument("--stage", default="planning")
    args = parser.parse_args()
    try:
        output = initialize(args.config, args.name, args.stage)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, "error: " + str(error) + "\n")
    print(json.dumps({"run_root": str(output), "eda_launched": False,
                      "first_task": "Main writes an actual bounded task and AI resource selection"}, indent=2))


if __name__ == "__main__":
    main()
