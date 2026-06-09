#!/usr/bin/env python3
"""Sync current affiliated MiLB team metadata from MLB Stats API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baseball_processor.utils.milb_metadata import (
    build_active_affiliated_registry,
    default_milb_season,
    fetch_active_affiliated_teams,
    generated_metadata_path,
    missing_location_teams,
    write_active_affiliated_registry,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write current-season MiLB metadata from MLB Stats API.")
    parser.add_argument("--season", type=int, default=default_milb_season(), help="Season to sync.")
    parser.add_argument("--output", type=Path, help="Output JSON path.")
    parser.add_argument("--timeout", type=int, default=10, help="Per-request timeout in seconds.")
    parser.add_argument(
        "--strict-location",
        action="store_true",
        help="Fail when any synced active team lacks local coordinates.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable sync output.")
    args = parser.parse_args()

    if os.environ.get("NCAA_BASEBALL_OFFLINE") == "1":
        message = "MiLB metadata sync requires network access; NCAA_BASEBALL_OFFLINE=1"
        if args.json:
            print(json.dumps({"error": message}, indent=2))
        else:
            print(message)
        return 1

    live_teams = fetch_active_affiliated_teams(args.season, timeout=args.timeout)
    registry = build_active_affiliated_registry(live_teams, args.season)
    output_path = write_active_affiliated_registry(
        registry,
        args.output or generated_metadata_path(args.season),
    )

    teams = {
        int(team["team_id"]): team
        for team in registry.get("teams", [])
        if team.get("team_id") is not None
    }
    missing_locations = missing_location_teams(teams)

    if args.json:
        print(json.dumps({
            "season": args.season,
            "output": str(output_path),
            "team_count": len(registry.get("teams", [])),
            "missing_locations": missing_locations,
        }, indent=2, sort_keys=True))
    else:
        print(f"Wrote {len(registry.get('teams', []))} active MiLB team(s) to {output_path}")
        for team in missing_locations:
            print(
                "WARNING: missing coordinates for "
                f"{team['team_id']} {team['team']} ({team['level']} / {team['league']} / {team['venue']})"
            )

    return 1 if args.strict_location and missing_locations else 0


if __name__ == "__main__":
    raise SystemExit(main())

