"""Normalize source-specific game dictionaries into one processor contract."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .utils.constants import BASE_DIR, ROSTERS_DIR, TEAM_ALIASES, get_conference, resolve_level_and_league
from .utils.helpers import (
    is_placeholder_player_name,
    is_single_initial_player_name,
    normalize_name,
    resolve_player_display_name,
    resolve_venue_name,
    safe_int,
)
from .player_display import (
    display_suffix as _display_suffix,
    has_display_suffix as _has_display_suffix,
    has_richer_source_suffix as _has_richer_source_suffix,
    row_source_display_name as _row_source_display_name,
)
from utils.names import clean_player_name, normalize_player_name


PlayerNameAliases = Dict[tuple[str, str], Dict[str, str]]
_ROSTER_NAME_MATCHER_LOADED = False
_ROSTER_NAME_MATCHER: Any = None


def first_present(row: Mapping[str, Any], *keys: str, default: Any = "") -> Any:
    """Return the first present, non-empty value from a source row."""
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def first_int(row: Mapping[str, Any], *keys: str, default: int = 0) -> int:
    """Return the first present source value as an int."""
    return safe_int(first_present(row, *keys, default=default), default)


def _get_roster_name_matcher() -> Any:
    """Return a local roster matcher for source rows that lack player IDs."""
    global _ROSTER_NAME_MATCHER_LOADED, _ROSTER_NAME_MATCHER
    if _ROSTER_NAME_MATCHER_LOADED:
        return _ROSTER_NAME_MATCHER

    _ROSTER_NAME_MATCHER_LOADED = True
    try:
        from name_matcher import NameMatcher

        matcher = NameMatcher()
        if ROSTERS_DIR.exists():
            matcher.load_rosters_from_dir(str(ROSTERS_DIR))
        partner_rosters = BASE_DIR / "partner" / "rosters"
        if partner_rosters.exists():
            matcher.load_rosters_from_dir(str(partner_rosters))
        _ROSTER_NAME_MATCHER = matcher
    except Exception:
        _ROSTER_NAME_MATCHER = None
    return _ROSTER_NAME_MATCHER


def _team_alias_key(team: str) -> str:
    team = re.sub(r"\s*\(CA\)\s*$", "", str(team or "").strip(), flags=re.IGNORECASE)
    key = re.sub(r"[^a-z0-9]", "", team.lower())
    if key == "loyolamarymount":
        return "lmu"
    return key


def _last_name_token(normalized_name: str) -> str:
    parts = normalized_name.split()
    if not parts:
        return ""
    return re.sub(r"[^a-z]", "", parts[-1])


def _is_initial_token(token: str) -> bool:
    return bool(re.fullmatch(r"[a-z]\.?", token))


def _name_alias_key(display_name: str, team: str) -> tuple[tuple[str, str, str] | None, bool, str]:
    normalized = normalize_name(display_name)
    parts = normalized.split()
    if len(parts) < 2:
        return None, False, normalized

    first_letters = re.sub(r"[^a-z]", "", parts[0])
    last = _last_name_token(normalized)
    if not first_letters or not last:
        return None, False, normalized

    has_spaced_initials = len(parts) >= 3 and _is_initial_token(parts[0]) and _is_initial_token(parts[1])
    is_initial_only = len(first_letters) == 1 and not has_spaced_initials
    return (_team_alias_key(team), first_letters[0], last), is_initial_only, normalized


def _game_year(meta: Mapping[str, Any]) -> Optional[int]:
    date = str(meta.get("date") or meta.get("date_yyyymmdd") or "")
    if not date:
        return None
    try:
        if "/" in date:
            year = date.split("/")[-1]
            return int(year) if len(year) == 4 else 2000 + int(year)
        if "-" in date:
            return int(date.split("-")[0])
        if len(date) >= 4 and date[:4].isdigit():
            return int(date[:4])
    except (ValueError, IndexError):
        return None
    return None


def _player_alias_record(display_name: str, bref_id: Any = "", source: str = "") -> Dict[str, str]:
    return {"display_name": display_name, "bref_id": str(bref_id or ""), "source": source}


def _merge_alias_record(records: Dict[str, Dict[str, str]], normalized_name: str, display_name: str, bref_id: Any) -> None:
    record = records.setdefault(normalized_name, _player_alias_record(display_name, bref_id, "game"))
    if bref_id and not record.get("bref_id"):
        record["bref_id"] = str(bref_id)
    if len(display_name) > len(record.get("display_name", "")):
        record["display_name"] = display_name


def _unique_values(values: Iterable[str]) -> List[str]:
    seen = set()
    unique = []
    for value in values:
        text = str(value or "").strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        unique.append(text)
    return unique


def _roster_team_queries(team: str) -> List[str]:
    """Return B-Ref roster team query variants for a source team label."""
    raw = str(team or "").strip()
    stripped = re.sub(r"\s*\(CA\)\s*$", "", raw, flags=re.IGNORECASE).strip()
    candidates = [raw, stripped]

    if stripped in TEAM_ALIASES:
        candidates.append(TEAM_ALIASES[stripped])
    for alias, canonical in TEAM_ALIASES.items():
        if canonical == stripped:
            candidates.append(alias)

    alias_groups = {
        "lmu": ["Loyola Marymount", "LMU"],
        "saintmarys": ["Saint Mary's", "Saint Mary's (CA)"],
        "california": ["California", "Cal"],
    }
    candidates.extend(alias_groups.get(_team_alias_key(stripped), []))
    return _unique_values(candidates)


def _roster_name_queries(name: str) -> List[str]:
    """Return conservative source-name variants for B-Ref roster matching."""
    display_name = normalize_player_name(str(name or "").strip())
    cleaned = normalize_player_name(clean_player_name(display_name))
    candidates = [display_name, cleaned]
    normalized_cleaned = normalize_name(cleaned)

    source_aliases = {
        "daniel gueva castro": ["Daniel Guevara"],
        "dani castro": ["Daniel Guevara"],
        "jimmy pelletier": ["Charles-Etienne Pelletier"],
    }
    candidates.extend(source_aliases.get(normalized_cleaned, []))

    if re.search(r"\bfuny\b", cleaned, flags=re.IGNORECASE):
        candidates.append(re.sub(r"\bfuny\b", "Fung", cleaned, flags=re.IGNORECASE))

    tokens = cleaned.split()
    lower_tokens = [re.sub(r"[^a-z]", "", token.lower()) for token in tokens]
    compound_prefixes = {
        ("de",),
        ("del",),
        ("da",),
        ("van",),
        ("von",),
        ("la",),
        ("le",),
        ("de", "la"),
    }
    if len(tokens) >= 3:
        for prefix in compound_prefixes:
            if tuple(lower_tokens[: len(prefix)]) == prefix:
                candidates.append(tokens[-1])
                break

    if len(tokens) >= 2:
        last_token = tokens[-1]
        if len(last_token) > 3 and last_token[-1].lower() == last_token[-2].lower():
            candidates.append(" ".join(tokens[:-1] + [last_token[:-1]]))

    return _unique_values(candidates)


def _roster_alias_record(name: str, team: str, year: Optional[int], number: Any) -> Optional[Dict[str, str]]:
    matcher = _get_roster_name_matcher()
    if matcher is None:
        return None

    number_text = str(number or "").strip() or None
    result = None
    for team_query in _roster_team_queries(team):
        for name_query in _roster_name_queries(name):
            try:
                candidate = matcher.match(name_query, team_query, number=number_text, year=year)
            except Exception:
                continue
            if getattr(candidate, "matched", False) and getattr(candidate, "confidence", 0.0) >= 0.75:
                result = candidate
                break
        if result is not None:
            break
    if result is None:
        return None

    player = getattr(result, "player", None) or {}
    player_name = player.get("name") or " ".join(
        part for part in [player.get("first_name"), player.get("last_name")] if part
    )
    if not player_name:
        return None
    return _player_alias_record(player_name, player.get("bref_id", ""), "roster")


def build_player_name_aliases(games: Iterable[Mapping[str, Any]]) -> PlayerNameAliases:
    """Build conservative team-scoped player display-name aliases from games and local rosters."""
    games = list(games)
    aliases: PlayerNameAliases = {}
    initial_candidates: Dict[tuple[str, str, str], Dict[str, Dict[str, str]]] = {}
    last_name_candidates: Dict[tuple[str, str], Dict[str, Dict[str, str]]] = {}
    last_name_candidates_by_team: Dict[str, List[tuple[str, str, Dict[str, str]]]] = {}
    abbreviated: List[tuple[str, str, tuple[str, str, str]]] = []
    surname_only: List[tuple[str, str, str, str]] = []

    for game in games:
        meta = game.get("metadata", {}) or {}
        year = _game_year(meta)
        for side in ("away", "home"):
            team = str(meta.get(f"{side}_team", "") or "")
            team_key = _team_alias_key(team)
            sections = (
                _raw_batting_rows(game, side),
                _raw_pitching_rows(game, side),
            )
            for rows in sections:
                for row in rows:
                    bref_id = first_present(row, "bref_id", "register_id")
                    display_name = resolve_player_display_name(_row_source_display_name(row), bref_id)
                    if is_placeholder_player_name(display_name):
                        continue

                    roster_record = None
                    if not bref_id:
                        roster_record = _roster_alias_record(
                            display_name,
                            team,
                            year,
                            first_present(row, "number", "jersey", "jersey_number"),
                        )
                    if roster_record:
                        aliases[(team_key, normalize_name(display_name))] = roster_record
                        display_name = roster_record["display_name"]
                        bref_id = bref_id or roster_record.get("bref_id", "")
                    elif bref_id:
                        aliases.setdefault(
                            (team_key, normalize_name(display_name)),
                            _player_alias_record(display_name, bref_id, "game"),
                        )

                    alias_key, is_initial_only, normalized = _name_alias_key(display_name, team)
                    if not alias_key:
                        last = _last_name_token(normalized)
                        if last and len(last) >= 4:
                            surname_only.append((team, normalized, team_key, last))
                        continue

                    last = _last_name_token(normalized)
                    if is_initial_only:
                        abbreviated.append((team, normalized, alias_key))
                    else:
                        _merge_alias_record(
                            initial_candidates.setdefault(alias_key, {}),
                            normalized,
                            display_name,
                            bref_id,
                        )
                        if last:
                            record = _player_alias_record(display_name, bref_id)
                            _merge_alias_record(last_name_candidates.setdefault((team_key, last), {}), normalized, display_name, bref_id)
                            last_name_candidates_by_team.setdefault(team_key, []).append((last, normalized, record))

    for team, abbreviated_name, alias_key in abbreviated:
        candidates = initial_candidates.get(alias_key, {})
        if len(candidates) == 1:
            aliases[(_team_alias_key(team), abbreviated_name)] = next(iter(candidates.values()))

    for _team, surname_name, team_key, last in surname_only:
        candidates = dict(last_name_candidates.get((team_key, last), {}))
        if not candidates:
            for candidate_last, candidate_name, record in last_name_candidates_by_team.get(team_key, []):
                if len(last) >= 5 and (candidate_last.startswith(last) or last.startswith(candidate_last)):
                    candidates[candidate_name] = record
        if len(candidates) == 1:
            aliases[(team_key, surname_name)] = next(iter(candidates.values()))

    return aliases


def resolve_player_name_alias(
    name: Any,
    team: str,
    aliases: Optional[PlayerNameAliases],
) -> Optional[Dict[str, str]]:
    """Return a team-scoped player-name alias record when one is known."""
    if not aliases:
        return None
    return aliases.get((_team_alias_key(team), normalize_name(str(name or ""))))


def alias_display_name(name: str, alias: Mapping[str, str]) -> str:
    """Return alias display text without letting same-name cache casing regressions leak."""
    display_name = alias.get("display_name") or ""
    if not display_name:
        return name
    if normalize_name(display_name) == normalize_name(name) and (
        alias.get("source") == "game" or _has_richer_source_suffix(name, display_name)
    ):
        return name
    if normalize_name(display_name) == normalize_name(name):
        suffix = _display_suffix(name)
        if suffix and not _has_display_suffix(display_name):
            return f"{display_name} {suffix}"
    return display_name


def _date_yyyymmdd(meta: Mapping[str, Any]) -> str:
    if meta.get("date_yyyymmdd"):
        return str(meta.get("date_yyyymmdd"))

    date = str(meta.get("date", "") or "")
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(date, fmt).strftime("%Y%m%d")
        except ValueError:
            pass
    return ""


def _slug(value: Any) -> str:
    return "".join(c for c in str(value or "").lower() if c.isalnum())


def _score_slug(meta: Mapping[str, Any]) -> str:
    away_score = meta.get("away_team_score", meta.get("away_score"))
    home_score = meta.get("home_team_score", meta.get("home_score"))
    if away_score in (None, "") or home_score in (None, ""):
        return ""
    return f"{safe_int(away_score)}_{safe_int(home_score)}"


def infer_source(game: Mapping[str, Any]) -> str:
    """Infer the canonical source label for a raw game."""
    meta = game.get("metadata", {}) or {}
    source = str(meta.get("source") or game.get("source") or "").lower()
    if source:
        if source == "sidearm_html":
            return "ncaa"
        return source
    if game.get("format") == "milb_api":
        return "milb"
    return "ncaa"


def stable_game_id(game: Mapping[str, Any]) -> str:
    """Build a stable source-aware game id."""
    meta = game.get("metadata", {}) or {}
    source = infer_source(game)
    ymd = _date_yyyymmdd(meta)

    if source == "milb" or game.get("format") == "milb_api":
        game_pk = meta.get("game_pk") or meta.get("game_id")
        if game_pk:
            return f"milb_{game_pk}"

    if source == "partner":
        game_id = meta.get("game_id") or meta.get("game_code") or meta.get("game_pk")
        league = meta.get("league", "")
        if isinstance(league, dict):
            league = league.get("home") or league.get("away") or ""
        league_slug = "".join(c for c in str(league).lower().replace(" ", "_") if c.isalnum() or c == "_")
        if game_id:
            return f"partner_{league_slug}_{game_id}"

    if source == "ncaa_api":
        game_id = meta.get("game_id") or meta.get("game_pk")
        if game_id:
            return f"ncaa_api_{game_id}"
        prefix = "ncaa_api"
    elif meta.get("source") == "sidearm_html" or game.get("format") == "sidearm_html":
        prefix = "ncaa_html"
    else:
        prefix = "ncaa_pdf"
    fallback_id = f"{prefix}_{ymd}_{_slug(meta.get('away_team'))}_at_{_slug(meta.get('home_team'))}"
    score_slug = _score_slug(meta)
    if score_slug:
        fallback_id = f"{fallback_id}_{score_slug}"
    start_slug = _slug(meta.get("start_time"))
    if start_slug:
        fallback_id = f"{fallback_id}_{start_slug}"
    return fallback_id


def _level_and_league(game: Mapping[str, Any], meta: Mapping[str, Any]) -> tuple[str, str]:
    source = infer_source(game)
    home_team = str(meta.get("home_team") or "")
    if source in {"milb", "partner"} or game.get("format") == "milb_api":
        return resolve_level_and_league(dict(meta), home_team)
    return "NCAA", get_conference(home_team)


def _raw_batting_rows(game: Mapping[str, Any], side: str) -> Iterable[Mapping[str, Any]]:
    box = game.get("box_score")
    if isinstance(box, Mapping):
        return box.get(f"{side}_batting", []) or []
    batting = game.get("batting")
    if isinstance(batting, Mapping):
        return batting.get(side, []) or []
    return []


def _raw_pitching_rows(game: Mapping[str, Any], side: str) -> Iterable[Mapping[str, Any]]:
    box = game.get("box_score")
    if isinstance(box, Mapping):
        return box.get(f"{side}_pitching", []) or []
    pitching = game.get("pitching")
    if isinstance(pitching, Mapping):
        return pitching.get(side, []) or []
    return []


def _row_identity(row: Mapping[str, Any]) -> str:
    bref_id = first_present(row, "bref_id", "register_id")
    name = resolve_player_display_name(_row_source_display_name(row), bref_id)
    return normalize_name(normalize_player_name(clean_player_name(str(name or "").strip())))


def _loose_player_name_key(row: Mapping[str, Any]) -> str:
    """Return a first-initial/last-name key for nickname-aware artifact checks."""
    bref_id = first_present(row, "bref_id", "register_id")
    name = resolve_player_display_name(_row_source_display_name(row), bref_id)
    normalized = normalize_name(normalize_player_name(clean_player_name(str(name or "").strip())))
    parts = normalized.split()
    if len(parts) < 2:
        return ""
    first = re.sub(r"[^a-z]", "", parts[0])
    last = _last_name_token(normalized)
    if not first or not last:
        return ""
    return f"{first[0]}:{last}"


def _is_pitcher_only_batting_artifact(
    row: Mapping[str, Any],
    pitcher_identities: set[str],
    pitcher_identity_keys: set[str],
    pitcher_loose_name_keys: set[str],
    team: str,
    year: Optional[int],
    player_name_aliases: Optional[PlayerNameAliases],
) -> bool:
    """Return True for parser bleed-through where pitcher rows land in batting tables."""
    position = str(first_present(row, "position", "pos")).strip().lower()
    if position != "p":
        return False

    stat_groups = (
        ("AB", "ab", "at_bats"),
        ("R", "r", "runs"),
        ("H", "h", "hits"),
        ("RBI", "rbi"),
        ("BB", "bb", "walks"),
        ("SO", "so", "k", "strikeouts"),
        ("PO", "po", "put_outs"),
        ("A", "a", "assists"),
        ("LOB", "lob", "left_on_base"),
    )
    if not all(first_int(row, *keys) == 0 for keys in stat_groups):
        return False

    identity = _row_identity(row)
    canonical_identity = _row_player_identity_key(row, team, year, player_name_aliases)
    loose_name_key = _loose_player_name_key(row)
    if (
        (not identity or identity not in pitcher_identities)
        and (not canonical_identity or canonical_identity not in pitcher_identity_keys)
        and (not loose_name_key or loose_name_key not in pitcher_loose_name_keys)
    ):
        return False

    return True


def _row_has_roster_match(
    row: Mapping[str, Any],
    team: str,
    year: Optional[int],
    player_name_aliases: Optional[PlayerNameAliases],
) -> bool:
    bref_id = first_present(row, "bref_id", "register_id")
    name = resolve_player_display_name(_row_source_display_name(row), bref_id)
    alias = resolve_player_name_alias(name, team, player_name_aliases)
    if alias and alias.get("bref_id"):
        return True
    return _roster_alias_record(name, team, year, first_present(row, "number", "jersey", "jersey_number")) is not None


def _row_player_identity_key(
    row: Mapping[str, Any],
    team: str,
    year: Optional[int],
    player_name_aliases: Optional[PlayerNameAliases],
) -> str:
    bref_id = first_present(row, "bref_id", "register_id")
    name = resolve_player_display_name(_row_source_display_name(row), bref_id)
    alias = resolve_player_name_alias(name, team, player_name_aliases)
    if alias:
        name = alias_display_name(name, alias)
        bref_id = bref_id or alias.get("bref_id", "")
    if not bref_id:
        roster_record = _roster_alias_record(name, team, year, first_present(row, "number", "jersey", "jersey_number"))
        if roster_record:
            name = alias_display_name(name, roster_record)
            bref_id = roster_record.get("bref_id", "")
    if bref_id:
        return f"id:{bref_id}"
    identity = normalize_name(normalize_player_name(clean_player_name(str(name or "").strip())))
    return f"name:{identity}" if identity else ""


def _pitching_row_quality(row: Mapping[str, Any]) -> int:
    score = 0
    for keys in (
        ("SO", "so", "k", "strikeouts"),
        ("BB", "bb", "walks"),
        ("pitches", "np", "numberOfPitches"),
        ("batters_faced", "bf"),
        ("H", "h", "hits"),
        ("R", "r", "runs"),
        ("ER", "er", "earned_runs"),
    ):
        score += safe_int(first_present(row, *keys))
    return score


def _batting_row_quality(row: Mapping[str, Any]) -> int:
    score = 0
    for keys in (
        ("AB", "ab", "at_bats"),
        ("R", "r", "runs"),
        ("H", "h", "hits"),
        ("RBI", "rbi"),
        ("BB", "bb", "walks"),
        ("SO", "so", "k", "strikeouts"),
        ("2B", "2b", "doubles"),
        ("3B", "3b", "triples"),
        ("HR", "hr", "home_runs"),
        ("SB", "sb", "stolen_bases"),
        ("PO", "po", "put_outs"),
        ("A", "a", "assists"),
        ("LOB", "lob", "left_on_base"),
    ):
        score += safe_int(first_present(row, *keys))
    if first_present(row, "bref_id", "register_id"):
        score += 1
    if first_present(row, "full_name"):
        score += 1
    return score


def _dedupe_batting_rows(
    rows: List[Mapping[str, Any]],
    team: str,
    year: Optional[int],
    player_name_aliases: Optional[PlayerNameAliases],
) -> List[Mapping[str, Any]]:
    order: List[str] = []
    by_key: Dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(rows):
        identity = _row_player_identity_key(row, team, year, player_name_aliases) or f"row:{index}"
        if identity not in by_key:
            order.append(identity)
            by_key[identity] = row
            continue
        if _batting_row_quality(row) > _batting_row_quality(by_key[identity]):
            by_key[identity] = row
    return [by_key[identity] for identity in order]


def _dedupe_pitching_rows(
    rows: List[Mapping[str, Any]],
    team: str,
    year: Optional[int],
    player_name_aliases: Optional[PlayerNameAliases],
) -> List[Mapping[str, Any]]:
    order: List[str] = []
    by_key: Dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(rows):
        identity = _row_player_identity_key(row, team, year, player_name_aliases) or f"row:{index}"
        if identity not in by_key:
            order.append(identity)
            by_key[identity] = row
            continue
        if _pitching_row_quality(row) > _pitching_row_quality(by_key[identity]):
            by_key[identity] = row
    return [by_key[identity] for identity in order]


def _with_roster_identity(
    row: Mapping[str, Any],
    team: str,
    year: Optional[int],
    player_name_aliases: Optional[PlayerNameAliases],
) -> Mapping[str, Any]:
    bref_id = first_present(row, "bref_id", "register_id")
    name = resolve_player_display_name(_row_source_display_name(row), bref_id)
    record = resolve_player_name_alias(name, team, player_name_aliases)
    if not record or record.get("source") == "game":
        roster_record = _roster_alias_record(name, team, year, first_present(row, "number", "jersey", "jersey_number"))
        if roster_record and (not bref_id or roster_record.get("bref_id") == str(bref_id)):
            record = roster_record
    if not record:
        return row

    display_name = alias_display_name(name, record)
    updated = dict(row)
    updated["full_name"] = display_name or updated.get("full_name") or updated.get("name")
    updated["name"] = display_name or updated.get("name") or updated.get("full_name")
    if record.get("bref_id") and not updated.get("bref_id"):
        updated["bref_id"] = record["bref_id"]
    return updated


def normalized_raw_sections(
    game: Mapping[str, Any],
    player_name_aliases: Optional[PlayerNameAliases] = None,
) -> tuple[Dict[str, List[Mapping[str, Any]]], Dict[str, List[Mapping[str, Any]]]]:
    """Return raw batting/pitching sections with obvious parser artifacts corrected."""
    meta = game.get("metadata", {}) or {}
    year = _game_year(meta)
    batting = {side: list(_raw_batting_rows(game, side)) for side in ("away", "home")}
    pitching: Dict[str, List[Mapping[str, Any]]] = {"away": [], "home": []}

    for side in ("away", "home"):
        other_side = "home" if side == "away" else "away"
        current_team = str(meta.get(f"{side}_team", "") or "")
        other_team = str(meta.get(f"{other_side}_team", "") or "")
        for row in _raw_pitching_rows(game, side):
            current_match = _row_has_roster_match(row, current_team, year, player_name_aliases)
            other_match = _row_has_roster_match(row, other_team, year, player_name_aliases)
            target_side = other_side if other_match and not current_match else side
            target_team = str(meta.get(f"{target_side}_team", "") or "")
            pitching[target_side].append(_with_roster_identity(row, target_team, year, player_name_aliases))

    for side in ("away", "home"):
        team = str(meta.get(f"{side}_team", "") or "")
        batting[side] = [
            _with_roster_identity(row, team, year, player_name_aliases)
            for row in batting[side]
        ]
        batting[side] = _dedupe_batting_rows(batting[side], team, year, player_name_aliases)
        pitching[side] = _dedupe_pitching_rows(pitching[side], team, year, player_name_aliases)

    pitcher_identities = {
        identity
        for rows in pitching.values()
        for row in rows
        for identity in [_row_identity(row)]
        if identity
    }
    pitcher_identity_keys = {
        identity
        for side, rows in pitching.items()
        for row in rows
        for identity in [
            _row_player_identity_key(
                row,
                str(meta.get(f"{side}_team", "") or ""),
                year,
                player_name_aliases,
            )
        ]
        if identity
    }
    pitcher_loose_name_keys = {
        key
        for rows in pitching.values()
        for row in rows
        for key in [_loose_player_name_key(row)]
        if key
    }
    batting = {
        side: [
            row
            for row in rows
            if not _is_pitcher_only_batting_artifact(
                row,
                pitcher_identities,
                pitcher_identity_keys,
                pitcher_loose_name_keys,
                str(meta.get(f"{side}_team", "") or ""),
                year,
                player_name_aliases,
            )
        ]
        for side, rows in batting.items()
    }
    return batting, pitching


def normalize_batter(
    row: Mapping[str, Any],
    team: str,
    side: str,
    player_name_aliases: Optional[PlayerNameAliases] = None,
) -> Dict[str, Any]:
    """Normalize one batting row while preserving the source row."""
    bref_id = first_present(row, "bref_id", "register_id")
    name = resolve_player_display_name(_row_source_display_name(row), bref_id)
    alias = resolve_player_name_alias(name, team, player_name_aliases)
    if alias:
        name = alias_display_name(name, alias)
        bref_id = bref_id or alias.get("bref_id", "")
    normalized = dict(row)
    normalized.update(
        {
            "name": name,
            "full_name": name,
            "team": team,
            "side": side,
            "player_id": first_present(row, "player_id", "mlb_api_id"),
            "bref_id": bref_id,
            "AB": first_int(row, "AB", "ab", "at_bats"),
            "R": first_int(row, "R", "r", "runs"),
            "H": first_int(row, "H", "h", "hits"),
            "RBI": first_int(row, "RBI", "rbi"),
            "BB": first_int(row, "BB", "bb", "walks"),
            "SO": first_int(row, "SO", "so", "k", "strikeouts"),
            "2B": first_int(row, "2B", "2b", "doubles"),
            "3B": first_int(row, "3B", "3b", "triples"),
            "HR": first_int(row, "HR", "hr", "home_runs"),
            "SB": first_int(row, "SB", "sb", "stolen_bases"),
            "CS": first_int(row, "CS", "cs", "caught_stealing"),
            "HBP": first_int(row, "HBP", "hbp", "hit_by_pitch"),
            "SF": first_int(row, "SF", "sf", "sac_flies"),
            "SH": first_int(row, "SH", "sh", "sac_bunts"),
        }
    )
    return normalized


def normalize_pitcher(
    row: Mapping[str, Any],
    team: str,
    side: str,
    order: int,
    player_name_aliases: Optional[PlayerNameAliases] = None,
) -> Dict[str, Any]:
    """Normalize one pitching row while preserving the source row."""
    bref_id = first_present(row, "bref_id", "register_id")
    name = resolve_player_display_name(_row_source_display_name(row), bref_id)
    alias = resolve_player_name_alias(name, team, player_name_aliases)
    if alias:
        name = alias_display_name(name, alias)
        bref_id = bref_id or alias.get("bref_id", "")
    decision = str(first_present(row, "decision", default="") or "").upper()
    if not decision:
        if row.get("win"):
            decision = "W"
        elif row.get("loss"):
            decision = "L"
        elif row.get("save"):
            decision = "S"

    normalized = dict(row)
    normalized.update(
        {
            "name": name,
            "full_name": name,
            "team": team,
            "side": side,
            "pitcher_order": order,
            "player_id": first_present(row, "player_id", "mlb_api_id"),
            "bref_id": bref_id,
            "IP": first_present(row, "IP", "ip", "innings_pitched", default="0"),
            "H": first_int(row, "H", "h", "hits"),
            "R": first_int(row, "R", "r", "runs"),
            "ER": first_int(row, "ER", "er", "earned_runs"),
            "BB": first_int(row, "BB", "bb", "walks"),
            "SO": first_int(row, "SO", "so", "k", "strikeouts"),
            "HR": first_int(row, "HR", "hr", "home_runs"),
            "pitches": first_int(row, "pitches", "np", "numberOfPitches"),
            "strikes": first_int(row, "strikes"),
            "batters_faced": first_int(row, "batters_faced", "bf"),
            "HBP": first_int(row, "HBP", "hbp", "hit_by_pitch"),
            "decision": decision,
        }
    )
    return normalized


def normalize_game(
    game: Mapping[str, Any],
    player_name_aliases: Optional[PlayerNameAliases] = None,
) -> Dict[str, Any]:
    """Normalize one raw game into the canonical processor shape."""
    meta = dict(game.get("metadata", {}) or {})
    source = infer_source(game)
    level, league = _level_and_league(game, meta)

    basic_info = {
        "date": meta.get("date", ""),
        "date_yyyymmdd": _date_yyyymmdd(meta),
        "away_team": meta.get("away_team", ""),
        "home_team": meta.get("home_team", ""),
        "away_score_value": safe_int(meta.get("away_team_score", meta.get("away_score", 0))),
        "home_score_value": safe_int(meta.get("home_team_score", meta.get("home_score", 0))),
        "venue": resolve_venue_name(meta),
        "attendance": meta.get("attendance"),
        "source": source,
        "level": level,
        "league": league,
        "game_pk": meta.get("game_pk"),
    }

    batting_rows, pitching_rows = normalized_raw_sections(game, player_name_aliases)
    batting: Dict[str, List[Dict[str, Any]]] = {"away": [], "home": []}
    pitching: Dict[str, List[Dict[str, Any]]] = {"away": [], "home": []}
    for side in ("away", "home"):
        team = str(meta.get(f"{side}_team", "") or "")
        batting[side] = [
            normalize_batter(row, team, side, player_name_aliases)
            for row in batting_rows.get(side, [])
        ]
        pitching[side] = [
            normalize_pitcher(row, team, side, index, player_name_aliases)
            for index, row in enumerate(pitching_rows.get(side, []))
        ]

    return {
        "game_id": stable_game_id(game),
        "source": source,
        "basic_info": basic_info,
        "metadata": meta,
        "batting": batting,
        "pitching": pitching,
        "game_notes": game.get("game_notes", {}) or {},
        "play_by_play": game.get("play_by_play", {}) or {},
        "raw": game,
    }


def normalize_games(games: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize a list of raw game dictionaries."""
    games = list(games)
    player_name_aliases = build_player_name_aliases(games)
    return [normalize_game(game, player_name_aliases=player_name_aliases) for game in games]
