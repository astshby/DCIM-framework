"""Check a configured stage or a run's pinned identity, without EDA."""
import argparse
import json
import sys
from run_config import Config, verify_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--stage", default="planning")
    parser.add_argument("--run", help="Verify pinned run files and external input identities")
    args = parser.parse_args()
    try:
        result = verify_run(args.run) if args.run else Config(args.config).check(args.stage)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, "error: " + str(error) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
