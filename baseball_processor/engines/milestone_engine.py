"""Source-neutral milestone detection engine."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping

from ..normalization import build_player_name_aliases, normalize_game
from ..utils.helpers import (
    is_placeholder_player_name,
    normalize_player_name,
    normalize_team_name,
    parse_innings_pitched,
    safe_int,
)


MILESTONE_KEYS = [
    "three_hr_games", "multi_hr_games", "hr_games",
    "five_hit_games", "four_hit_games", "three_hit_games",
    "cycles", "cycle_watch",
    "six_rbi_games", "five_rbi_games", "four_rbi_games", "three_rbi_games",
    "multi_double_games", "multi_triple_games", "multi_sb_games",
    "four_walk_games", "perfect_batting_games",
    "four_run_games", "three_run_games",
    "hit_for_extra_bases", "three_total_bases_games",
    "perfect_games", "no_hitters", "one_hitters", "two_hitters",
    "shutouts", "cgso_no_walks", "complete_games", "low_hit_cg",
    "seven_inning_shutouts", "maddux_games",
    "fifteen_k_games", "twelve_k_games", "ten_k_games", "eight_k_games",
    "quality_starts", "dominant_starts", "efficient_starts",
    "high_k_low_bb", "no_walk_starts", "scoreless_relief",
    "win_games", "save_games",
]


def is_valid_player_name(name: str) -> bool:
    """Return False for totals rows and parsed game-note fragments."""
    if is_placeholder_player_name(name):
        return False

    name_lower = name.lower()
    if "totals" in name_lower:
        return False

    note_prefixes = [
        "sb:", "2b:", "3b:", "hr:", "e:", "cs:", "hbp:", "sf:", "sh:",
        "dp:", "lob:", "wp:", "pb:", "bk:", "w:", "l:", "s:", "sv:", "lp:",
    ]
    if any(name_lower.startswith(prefix) for prefix in note_prefixes):
        return False
    if re.search(r"\(\d+\)\s*$", name):
        return False
    if re.search(r"\(\d+[-/]\d+\)\s*$", name):
        return False
    return True


def is_valid_stat_player(name: str) -> bool:
    """Return False when a game-note token is a stat prefix instead of a player."""
    if not name:
        return False

    invalid_prefixes = ["SH", "SF", "SFA", "HBP", "CS", "SB", "GDP", "LOB", "DP", "WP", "PB", "BK", "IBB", "E", "PO"]
    name_upper = name.upper().strip()
    for prefix in invalid_prefixes:
        if name_upper.startswith(prefix + " ") or name_upper.startswith(prefix + "-") or name_upper.startswith(prefix + ":"):
            return False
        if name_upper == prefix:
            return False
    return not re.match(r"^[A-Z]+\s*:\s*\d+$", name_upper)


def _clean_note_name(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r"\s*\([^)]*\)\s*", "", name)
    name = re.sub(r"\s*\d+\s*$", "", name)
    return name.strip()


def _normalize_note_name(name: str) -> str:
    cleaned = _clean_note_name(name)
    if not cleaned:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", normalize_player_name(cleaned).lower()).strip()


def _note_lookup_keys(name: str) -> List[str]:
    cleaned = _clean_note_name(name)
    if not cleaned:
        return []
    keys: list[str] = []
    if "," in cleaned:
        last, first = cleaned.split(",", 1)
        last_key = re.sub(r"[^a-z0-9]+", " ", last.lower()).strip()
        first_key = re.sub(r"[^a-z0-9]+", " ", first.lower()).strip()
        if first_key and last_key:
            full_key = re.sub(r"[^a-z0-9]+", " ", f"{first_key} {last_key}").strip()
            keys.append(full_key)
            keys.append(f"{last_key}|{first_key[0]}")
        elif last_key:
            keys.append(last_key)
    else:
        keys.append(_normalize_note_name(cleaned))

    return [key for key in dict.fromkeys(keys) if key]


def build_extra_base_lookup(game_notes: Mapping[str, Any]) -> Dict[str, Dict[str, int]]:
    """Build player-name lookup for NCAA note-derived XBH and SB counts."""
    lookup: Dict[str, Dict[str, int]] = {}

    def add_to_lookup(name: str, stat: str, count: int) -> None:
        for norm in _note_lookup_keys(name):
            lookup.setdefault(norm, {"hr": 0, "2b": 0, "3b": 0, "sb": 0})
            lookup[norm][stat] += count

    def add_items(items: Iterable[Any], stat: str) -> None:
        for item in items or []:
            if isinstance(item, Mapping):
                name = str(item.get("player", "") or "")
                count = safe_int(item.get("game_count", 1), 1)
            else:
                name = str(item)
                count_match = re.search(r"\((\d+)\)", name)
                count = int(count_match.group(1)) if count_match else 1
            if is_valid_stat_player(name):
                add_to_lookup(name, stat, count)

    add_items(game_notes.get("home_runs", []), "hr")
    add_items(game_notes.get("doubles", []), "2b")
    add_items(game_notes.get("triples", []), "3b")
    add_items(game_notes.get("stolen_bases", []), "sb")
    return lookup


def get_player_extra_stats(player_name: str, lookup: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    """Return note-derived XBH/SB counts for a player, matching last names when needed."""
    norm = _normalize_note_name(player_name)
    if norm in lookup:
        return lookup[norm]

    parts = norm.split()
    if parts:
        first_initial_key = f"{parts[-1]}|{parts[0][0]}"
        if first_initial_key in lookup:
            return lookup[first_initial_key]
        if parts[-1] in lookup:
            return lookup[parts[-1]]

    return {"hr": 0, "2b": 0, "3b": 0, "sb": 0}


class MilestoneEngine:
    """Detect milestone event rows from raw or normalized games."""

    keys = MILESTONE_KEYS

    def __init__(self, games: Iterable[Mapping[str, Any]]):
        self.games = list(games)
        self.player_name_aliases = build_player_name_aliases(self.games)

    def detect(self) -> Dict[str, List[Dict[str, Any]]]:
        milestones: Dict[str, List[Dict[str, Any]]] = {key: [] for key in self.keys}
        for raw_game in self.games:
            self._detect_game(normalize_game(raw_game, player_name_aliases=self.player_name_aliases), milestones)
        return milestones

    def _detect_game(self, game: Mapping[str, Any], milestones: Dict[str, List[Dict[str, Any]]]) -> None:
        basic = game.get("basic_info", {}) or {}
        game_notes = game.get("game_notes", {}) or {}
        date = basic.get("date", "")
        game_id = game.get("game_id") or f"{date}_{basic.get('away_team', '')}_{basic.get('home_team', '')}"
        game_level = basic.get("level", "")
        game_league = basic.get("league", "")
        extra_stats_lookup = build_extra_base_lookup(game_notes)

        for side in ("away", "home"):
            opponent_side = "home" if side == "away" else "away"
            team = normalize_team_name(basic.get(f"{side}_team", ""))
            opponent = normalize_team_name(basic.get(f"{opponent_side}_team", ""))
            team_score = safe_int(basic.get(f"{side}_score_value", 0))
            opp_score = safe_int(basic.get(f"{opponent_side}_score_value", 0))

            base_context = {
                "Date": date,
                "Team": team,
                "Opponent": opponent,
                "Score": f"{team_score}-{opp_score}",
                "GameID": game_id,
                "Level": game_level,
                "League": game_league,
            }
            self._detect_batting(game.get("batting", {}).get(side, []), extra_stats_lookup, base_context, milestones)
            self._detect_pitching(game.get("pitching", {}).get(side, []), base_context, milestones)

    def _detect_batting(
        self,
        batters: Iterable[Mapping[str, Any]],
        extra_stats_lookup: Dict[str, Dict[str, int]],
        base_context: Dict[str, Any],
        milestones: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        for player in batters:
            name = normalize_player_name(str(player.get("name", "") or ""))
            if not is_valid_player_name(name):
                continue

            extra_stats = get_player_extra_stats(name, extra_stats_lookup)
            h = safe_int(player.get("H", 0))
            rbi = safe_int(player.get("RBI", 0))
            hr = extra_stats["hr"] or safe_int(player.get("HR", 0))
            doubles = extra_stats["2b"] or safe_int(player.get("2B", 0))
            triples = extra_stats["3b"] or safe_int(player.get("3B", 0))
            sb = extra_stats["sb"] or safe_int(player.get("SB", 0))
            r = safe_int(player.get("R", 0))
            bb = safe_int(player.get("BB", 0))
            so = safe_int(player.get("SO", 0))
            ab = safe_int(player.get("AB", 0))
            singles = max(0, h - doubles - triples - hr)
            total_bases = singles + (2 * doubles) + (3 * triples) + (4 * hr)
            base_info = {**base_context, "Player": name}

            if hr >= 3:
                milestones["three_hr_games"].append({**base_info, "HR": hr, "H": h, "RBI": rbi})
            elif hr >= 2:
                milestones["multi_hr_games"].append({**base_info, "HR": hr, "H": h, "RBI": rbi})
            elif hr >= 1:
                milestones["hr_games"].append({**base_info, "HR": hr, "H": h, "RBI": rbi})

            if h >= 5:
                milestones["five_hit_games"].append({**base_info, "H": h, "R": r, "RBI": rbi})
            elif h >= 4:
                milestones["four_hit_games"].append({**base_info, "H": h, "R": r, "RBI": rbi})
            elif h >= 3:
                milestones["three_hit_games"].append({**base_info, "H": h, "R": r, "RBI": rbi})

            hit_types = sum(1 for value in (singles, doubles, triples, hr) if value > 0)
            if singles >= 1 and doubles >= 1 and triples >= 1 and hr >= 1:
                milestones["cycles"].append({**base_info, "H": h, "1B": singles, "2B": doubles, "3B": triples, "HR": hr})
            elif hit_types >= 3 and h >= 3:
                milestones["cycle_watch"].append({**base_info, "H": h, "1B": singles, "2B": doubles, "3B": triples, "HR": hr})

            if rbi >= 6:
                milestones["six_rbi_games"].append({**base_info, "RBI": rbi, "H": h, "HR": hr})
            elif rbi >= 5:
                milestones["five_rbi_games"].append({**base_info, "RBI": rbi, "H": h, "HR": hr})
            elif rbi >= 4:
                milestones["four_rbi_games"].append({**base_info, "RBI": rbi, "H": h, "HR": hr})
            elif rbi >= 3:
                milestones["three_rbi_games"].append({**base_info, "RBI": rbi, "H": h, "HR": hr})

            if doubles >= 2:
                milestones["multi_double_games"].append({**base_info, "2B": doubles, "H": h, "RBI": rbi})
            if triples >= 2:
                milestones["multi_triple_games"].append({**base_info, "3B": triples, "H": h, "RBI": rbi})
            if sb >= 2:
                milestones["multi_sb_games"].append({**base_info, "SB": sb, "H": h, "R": r})
            if bb >= 4:
                milestones["four_walk_games"].append({**base_info, "BB": bb, "H": h, "R": r})
            if ab >= 3 and h == ab and so == 0:
                milestones["perfect_batting_games"].append({**base_info, "AB": ab, "H": h, "K": so, "R": r, "RBI": rbi})

            if r >= 4:
                milestones["four_run_games"].append({**base_info, "R": r, "H": h, "BB": bb})
            elif r >= 3:
                milestones["three_run_games"].append({**base_info, "R": r, "H": h, "BB": bb})

            xbh = doubles + triples + hr
            if xbh >= 2:
                milestones["hit_for_extra_bases"].append({**base_info, "XBH": xbh, "2B": doubles, "3B": triples, "HR": hr, "TB": total_bases})
            if total_bases >= 8:
                milestones["three_total_bases_games"].append({**base_info, "H": h, "HR": hr, "RBI": rbi, "TB": total_bases})

    def _detect_pitching(
        self,
        pitchers: Iterable[Mapping[str, Any]],
        base_context: Dict[str, Any],
        milestones: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        for pitcher_idx, player in enumerate(pitchers):
            name = normalize_player_name(str(player.get("name", "") or ""))
            if not is_valid_player_name(name):
                continue

            ip = parse_innings_pitched(player.get("IP", 0))
            k = safe_int(player.get("SO", 0))
            er = safe_int(player.get("ER", 0))
            h = safe_int(player.get("H", 0))
            bb = safe_int(player.get("BB", 0))
            hbp = safe_int(player.get("HBP", 0))
            pitches = safe_int(player.get("pitches", 0))
            decision = str(player.get("decision", "") or "").upper()
            ip_str = f"{int(ip)}.{int((ip % 1) * 3)}"
            base_info = {**base_context, "Player": name}

            is_complete_game = ip >= 9
            is_seven_inning_cg = ip >= 7 and ip < 9
            batters_faced = safe_int(player.get("batters_faced", 0))
            is_perfect = is_complete_game and h == 0 and bb == 0 and hbp == 0 and (batters_faced == 0 or batters_faced == 27)

            if is_perfect:
                milestones["perfect_games"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb})
            elif is_complete_game and h == 0:
                milestones["no_hitters"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})
            elif is_complete_game and h == 1:
                milestones["one_hitters"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})
            elif is_complete_game and h == 2:
                milestones["two_hitters"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})

            if is_complete_game and er == 0:
                if bb == 0:
                    milestones["cgso_no_walks"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb})
                else:
                    milestones["shutouts"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb})
            elif is_seven_inning_cg and er == 0:
                milestones["seven_inning_shutouts"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb})

            if is_complete_game:
                if h <= 3:
                    milestones["low_hit_cg"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})
                else:
                    milestones["complete_games"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})
            if is_complete_game and 0 < pitches < 100:
                milestones["maddux_games"].append({**base_info, "IP": ip_str, "K": k, "Pitches": pitches, "H": h, "BB": bb})

            if k >= 15:
                milestones["fifteen_k_games"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})
            elif k >= 12:
                milestones["twelve_k_games"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})
            elif k >= 10:
                milestones["ten_k_games"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})
            elif k >= 8:
                milestones["eight_k_games"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})

            if ip >= 6 and er <= 3 and pitcher_idx == 0:
                milestones["quality_starts"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})
            if ip >= 7 and k >= 10 and pitcher_idx == 0:
                milestones["dominant_starts"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})
            if ip >= 6 and 0 < pitches <= 80 and pitcher_idx == 0:
                milestones["efficient_starts"].append({**base_info, "IP": ip_str, "K": k, "Pitches": pitches, "H": h, "BB": bb})
            if k >= 8 and bb <= 2:
                milestones["high_k_low_bb"].append({**base_info, "IP": ip_str, "K": k, "BB": bb, "H": h, "ER": er})
            if ip >= 5 and bb == 0:
                milestones["no_walk_starts"].append({**base_info, "IP": ip_str, "K": k, "BB": bb, "H": h, "ER": er})
            if 3 <= ip < 6 and er == 0:
                milestones["scoreless_relief"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb})
            if decision == "W":
                milestones["win_games"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})
            if decision in {"S", "SV"}:
                milestones["save_games"].append({**base_info, "IP": ip_str, "K": k, "H": h, "BB": bb, "ER": er})


def detect_milestones(games: Iterable[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Functional entry point for milestone detection."""
    return MilestoneEngine(games).detect()
