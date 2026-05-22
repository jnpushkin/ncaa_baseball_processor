#!/usr/bin/env python3
"""Run local data-integrity checks for cached inputs and generated outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baseball_processor.audit import run_integrity_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit cache and generated website data for dropped games/rows.")
    parser.add_argument(
        "--strict-generated-from-cache",
        action="store_true",
        help="Require generated website game/detail counts to match all cached games.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable audit output.")
    args = parser.parse_args()

    summary, issues, warnings = run_integrity_audit(strict_generated_from_cache=args.strict_generated_from_cache)

    if args.json:
        print(json.dumps({"summary": summary, "warnings": warnings, "issues": issues}, indent=2, sort_keys=True))
    else:
        cache = summary["cache"]
        website = summary["website"]
        print("Data Integrity Audit")
        print("=" * 50)
        print(
            "Cache: "
            f"{cache['normalized_games']} normalized game(s), "
            f"{cache['batting_rows']} batting row(s), "
            f"{cache['pitching_rows']} pitching row(s)"
        )
        print(f"Source counts: {cache['source_counts']}")
        if website.get("generated"):
            print(
                "Website: "
                f"{website['linked_games']} linked game(s), "
                f"{website['detail_files']} detail file(s), "
                f"{website['missing_detail_files']} missing detail file(s), "
                f"{website.get('stat_accuracy_errors', 0)} stat accuracy error(s)"
            )
        for warning in warnings:
            print(f"WARNING: {warning}")
        for issue in issues:
            print(f"ERROR: {issue}")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
