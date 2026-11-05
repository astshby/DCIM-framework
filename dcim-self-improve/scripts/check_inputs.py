"""Check configured external input addresses without running EDA."""

import argparse
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets" / "seed"))

from seed_config import INPUT_SCOPES, load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Private JSON config (or DCIM_CONFIG)")
    parser.add_argument("--scope", choices=(*INPUT_SCOPES, "all"), default="all")
    args = parser.parse_args()
    try:
        result = load_config(args.config).check(args.scope)
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
