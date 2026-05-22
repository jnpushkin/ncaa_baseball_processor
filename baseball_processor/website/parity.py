"""Non-blocking parity checks between processed data and website JSON."""

from __future__ import annotations

from typing import Any, Mapping

from .serializers import MILESTONE_JSON_KEYS, tabular_count


def _json_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, Mapping):
        return len(value)
    if isinstance(value, (list, tuple)):
        return len(value)
    return 0


def collect_website_data_parity_issues(processed_data: Mapping[str, Any], json_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return count mismatches that could indicate missing website serialization."""
    issues: list[dict[str, Any]] = []

    core_sources = [
        ("Game Log", "game_log", "unifiedGameLog"),
        ("Team Records", "team_records", "teamRecords"),
        ("Crossover Players", "crossover_players", "crossoverPlayers"),
    ]
    for dataset, processed_key, json_key in core_sources:
        source_count = tabular_count(processed_data.get(processed_key))
        website_count = _json_count(json_data.get(json_key))
        if source_count and website_count < source_count:
            issues.append(
                {
                    "kind": "count_mismatch",
                    "dataset": dataset,
                    "jsonKey": json_key,
                    "sourceCount": source_count,
                    "websiteCount": website_count,
                    "message": f"{dataset} has {source_count} processed row(s), but website key {json_key!r} has {website_count}.",
                }
            )

    milestone_payload = json_data.get("milestones", {})
    for source_key, json_key in MILESTONE_JSON_KEYS.items():
        source_count = tabular_count((processed_data.get("milestones") or {}).get(source_key))
        website_count = _json_count(milestone_payload.get(json_key))
        if source_count != website_count:
            issues.append(
                {
                    "kind": "milestone_count_mismatch",
                    "dataset": source_key,
                    "jsonKey": json_key,
                    "sourceCount": source_count,
                    "websiteCount": website_count,
                    "message": f"Milestone {source_key!r} has {source_count} processed row(s), but website key {json_key!r} has {website_count}.",
                }
            )

    return issues
