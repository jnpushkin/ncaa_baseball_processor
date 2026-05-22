"""Milestone processor wrapper around the source-neutral milestone engine."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from ..engines.milestone_engine import (
    MILESTONE_KEYS,
    build_extra_base_lookup,
    detect_milestones,
    get_player_extra_stats,
    is_valid_player_name,
    is_valid_stat_player,
)
from ..utils.helpers import normalize_player_name


class MilestonesProcessor:
    """Process and compile baseball milestones across games."""

    MILESTONE_KEYS = MILESTONE_KEYS

    def __init__(self, games: List[Dict[str, Any]]):
        self.games = games

    def process_all_milestones(self) -> Dict[str, pd.DataFrame]:
        """Return milestone type -> DataFrame."""
        detected = detect_milestones(self.games)
        result = {}
        for key in self.MILESTONE_KEYS:
            entries = detected.get(key, [])
            if entries:
                df = pd.DataFrame(entries)
                if "Date" in df.columns:
                    df = df.sort_values("Date", ascending=False)
                result[key] = df
            else:
                result[key] = pd.DataFrame()
        return result


__all__ = [
    "MilestonesProcessor",
    "MILESTONE_KEYS",
    "build_extra_base_lookup",
    "get_player_extra_stats",
    "is_valid_player_name",
    "is_valid_stat_player",
    "normalize_player_name",
]
