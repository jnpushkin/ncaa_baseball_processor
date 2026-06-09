#!/usr/bin/env python3
"""Audit local MiLB metadata against the current-season MLB Stats API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baseball_processor.utils.milb_metadata_audit import (
    compare_milb_metadata,
    has_metadata_issues,
    metadata_audit_issue_lines,
    summarize_metadata_audit,
)
from baseball_processor.utils.milb_metadata import (
    active_affiliated_registry_teams,
    default_milb_season,
    fetch_active_affiliated_teams,
    load_active_affiliated_registry,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare static MiLB team metadata to MLB Stats API.")
    parser.add_argument("--season", type=int, default=default_milb_season(), help="Season to audit.")
    parser.add_argument("--strict", action="store_true", help="Fail when metadata drift is detected.")
    parser.add_argument("--require-generated", action="store_true", help="Fail when generated metadata is missing.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable audit output.")
    parser.add_argument("--timeout", type=int, default=10, help="Per-request timeout in seconds.")
    args = parser.parse_args()

    if os.environ.get("NCAA_BASEBALL_OFFLINE") == "1":
        message = "MiLB metadata audit skipped because NCAA_BASEBALL_OFFLINE=1"
        if args.json:
            print(json.dumps({"skipped": True, "reason": message}, indent=2))
        else:
            print(message)
        return 0

    if args.require_generated and not load_active_affiliated_registry(args.season):
        message = f"generated MiLB metadata not found for {args.season}; run scripts/sync_milb_metadata.py"
        if args.json:
            print(json.dumps({"error": message}, indent=2))
        else:
            print(message)
        return 1

    registry_teams, registry_source = active_affiliated_registry_teams(args.season)
    try:
        live_teams = fetch_active_affiliated_teams(args.season, timeout=args.timeout)
    except Exception as exc:
        message = f"MiLB metadata audit could not fetch Stats API data: {exc}"
        if args.json:
            print(json.dumps({"error": message}, indent=2))
        else:
            print(message)
        return 1 if args.strict else 0

    report = compare_milb_metadata(registry_teams, live_teams, registry_source=registry_source)
    lines = metadata_audit_issue_lines(report)

    if args.json:
        print(json.dumps({"season": args.season, "report": report, "issues": lines}, indent=2, sort_keys=True))
    else:
        print(f"MiLB Metadata Audit ({args.season})")
        print("=" * 50)
        print(summarize_metadata_audit(report))
        for line in lines:
            print(f"WARNING: {line}")

    return 1 if args.strict and has_metadata_issues(report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
