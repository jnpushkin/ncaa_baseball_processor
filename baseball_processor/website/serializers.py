"""Reusable serializers for website JSON payload pieces."""

from __future__ import annotations

import math
from typing import Any, Mapping

import pandas as pd


MILESTONE_JSON_KEYS = {
    "three_hr_games": "threeHrGames",
    "multi_hr_games": "multiHrGames",
    "hr_games": "hrGames",
    "five_hit_games": "fiveHitGames",
    "four_hit_games": "fourHitGames",
    "three_hit_games": "threeHitGames",
    "cycles": "cycles",
    "cycle_watch": "cycleWatch",
    "six_rbi_games": "sixRbiGames",
    "five_rbi_games": "fiveRbiGames",
    "four_rbi_games": "fourRbiGames",
    "three_rbi_games": "threeRbiGames",
    "multi_double_games": "multiDoubleGames",
    "multi_triple_games": "multiTripleGames",
    "multi_sb_games": "multiSbGames",
    "four_walk_games": "fourWalkGames",
    "perfect_batting_games": "perfectBattingGames",
    "four_run_games": "fourRunGames",
    "three_run_games": "threeRunGames",
    "hit_for_extra_bases": "hitForExtraBases",
    "three_total_bases_games": "threeTotalBasesGames",
    "perfect_games": "perfectGames",
    "no_hitters": "noHitters",
    "one_hitters": "oneHitters",
    "two_hitters": "twoHitters",
    "shutouts": "shutouts",
    "cgso_no_walks": "cgsoNoWalks",
    "complete_games": "completeGames",
    "low_hit_cg": "lowHitCg",
    "seven_inning_shutouts": "sevenInningShutouts",
    "maddux_games": "madduxGames",
    "fifteen_k_games": "fifteenKGames",
    "twelve_k_games": "twelveKGames",
    "ten_k_games": "tenKGames",
    "eight_k_games": "eightKGames",
    "quality_starts": "qualityStarts",
    "dominant_starts": "dominantStarts",
    "efficient_starts": "efficientStarts",
    "high_k_low_bb": "highKLowBb",
    "no_walk_starts": "noWalkStarts",
    "scoreless_relief": "scorelessRelief",
    "win_games": "winGames",
    "save_games": "saveGames",
}

NOTABLE_MILESTONE_KEYS = [
    "three_hr_games", "multi_hr_games",
    "five_hit_games", "four_hit_games",
    "cycles", "cycle_watch",
    "six_rbi_games", "five_rbi_games", "four_rbi_games",
    "multi_double_games", "multi_triple_games", "multi_sb_games",
    "four_walk_games", "perfect_batting_games",
    "four_run_games", "three_total_bases_games",
    "perfect_games", "no_hitters", "one_hitters", "two_hitters",
    "shutouts", "cgso_no_walks", "complete_games", "low_hit_cg",
    "seven_inning_shutouts", "maddux_games",
    "fifteen_k_games", "twelve_k_games", "ten_k_games",
    "dominant_starts",
]


def df_to_list(value: Any) -> list[dict[str, Any]] | list[Any]:
    """Convert DataFrames to records and normalize empty tabular values to []"""
    if value is None or (isinstance(value, pd.DataFrame) and value.empty):
        return []
    if isinstance(value, pd.DataFrame):
        return value.to_dict("records")
    return value


def scrub_json_value(value: Any) -> Any:
    """Replace NaN/Infinity values in nested payloads with JSON-safe nulls."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {key: scrub_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_json_value(item) for item in value]
    return value


def tabular_count(value: Any) -> int:
    """Count rows in a DataFrame/list-like value."""
    if value is None or (isinstance(value, pd.DataFrame) and value.empty):
        return 0
    try:
        return len(value)
    except TypeError:
        return 0


def count_notable_milestones(milestones: Mapping[str, Any]) -> int:
    """Count milestone rows that should contribute to the headline total."""
    return sum(tabular_count(milestones.get(key)) for key in NOTABLE_MILESTONE_KEYS)


def serialize_milestones(milestones: Mapping[str, Any]) -> dict[str, list[dict[str, Any]] | list[Any]]:
    """Serialize internal snake_case milestone frames to frontend camelCase keys."""
    return {
        json_key: df_to_list(milestones.get(source_key, []))
        for source_key, json_key in MILESTONE_JSON_KEYS.items()
    }
