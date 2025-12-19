"""
Data models for NCAA baseball parsing.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlayerBattingStats:
    number: str
    name: str
    position: str
    at_bats: int
    runs: int
    hits: int
    rbi: int
    walks: int
    strikeouts: int
    put_outs: int
    assists: int
    left_on_base: int


@dataclass
class PitcherStats:
    number: str
    name: str
    innings_pitched: float
    hits: int
    runs: int
    earned_runs: int
    walks: int
    strikeouts: int
    batters_faced: int
    at_bats: int
    pitches: int


@dataclass
class PlayEvent:
    description: str
    pitch_count: Optional[str] = None  # e.g., "2-2 KBBK"
    rbi: int = 0
    runs_scored: list = None
