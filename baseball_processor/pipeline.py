"""Pipeline helpers shared by the CLI and future automation entry points."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from player_crossover import PlayerCrossover


def build_crossover_data(
    ncaa_games: List[Dict[str, Any]],
    milb_games: List[Dict[str, Any]],
    partner_games: Optional[List[Dict[str, Any]]] = None,
) -> PlayerCrossover:
    """Build player crossover tracking data from NCAA, MiLB, and Partner games."""
    crossover = PlayerCrossover()

    if ncaa_games:
        print(f"Loading {len(ncaa_games)} NCAA games for crossover...")
        crossover.load_ncaa_data(ncaa_games)
    if milb_games:
        print(f"Loading {len(milb_games)} MiLB games for crossover...")
        crossover.load_milb_data(milb_games)
    if partner_games:
        print(f"Loading {len(partner_games)} Partner games for crossover...")
        crossover.load_partner_data(partner_games)

    return crossover
