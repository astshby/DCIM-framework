"""Initialize a portable run from the bundled Python seed; never launch EDA."""

import argparse
import json
from pathlib import Path
import re
import shutil
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
SEED_ROOT = SKILL_ROOT / "assets" / "seed"
sys.path.insert(0, str(SEED_ROOT))

from seed_config import load_config


def initialize(config, name):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", name):
        raise ValueError("Use a simple run name beginning with a letter")
    settings = load_config(config)
    output = settings.ensure_output(settings.path("work_root") / name)
    if output.exists():
        raise FileExistsError(f"Run already exists: {output}")
    local = settings.rebased(output)
    local["work_root"] = "."
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(SEED_ROOT, output / "design",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.so"))
    shutil.copytree(SKILL_ROOT / "templates", output / "templates")
    (output / "config.json").write_text(json.dumps(local, indent=2) + "\n", encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Private JSON config (or DCIM_CONFIG)")
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    try:
        output = initialize(args.config, args.name)
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps({"run_root": str(output), "eda_launched": False}, indent=2))


if __name__ == "__main__":
    main()
